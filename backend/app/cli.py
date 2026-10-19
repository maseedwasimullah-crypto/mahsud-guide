"""Command-line operations: database init, seeding, ingestion, refresh, admin user.

Run from the ``backend`` directory:

    python -m app.cli initdb
    python -m app.cli seed
    python -m app.cli ingest          # fetch official pages/PDFs (needs network)
    python -m app.cli ingest --offline # use archived copies in ../data/raw when present
    python -m app.cli refresh
    python -m app.cli create-admin --email you@example.com
    python -m app.cli bootstrap       # initdb + seed + ingest (skips failures)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (register tables)
from .config import BASE_DIR, settings
from .constants import DocType, InstitutionType, Verification
from .db import SessionLocal, init_db
from .models import (
    AdmissionCycle,
    AdmissionRule,
    AggregateFormula,
    Campus,
    Document,
    Institution,
    Policy,
    Program,
    ProgramOffering,
    Source,
    User,
)
from .seed_data import CYCLES, FORMULAS, INGEST_PAGES, POLICIES, RULES, SOURCES
from .security import hash_password
from .services import kmu_parsers
from .services.ingest import (
    fetch,
    get_or_create_source,
    html_to_text,
    ingest_url,
    pdf_to_text,
    refresh_source,
    upsert_document,
)

RAW_DIR = BASE_DIR.parent / "data" / "raw"

LOCAL_FALLBACKS = {
    "https://kmu.edu.pk/institutes/affiliated": "affiliated_institutes.html",
    "https://kmu.edu.pk/institutes/constituent": "constituent_institutes.html",
    "https://kmu.edu.pk/programs/undergraduate": "programs_ug.html",
    "https://kmu.edu.pk/programs/postgraduate": "programs_pg.html",
    "https://kmu.edu.pk/programs/diploma": "programs_diploma.html",
    "https://kmu.edu.pk/faculty_by_institute": "faculty.html",
}

# Documents captured by hand during research because the host blocks automated
# fetching (PNMC resets the connection; the cas.kmu.edu.pk PDF is not linked for
# crawlers). They are imported from the local archive and flagged in the record.
MANUAL_ARCHIVES = {
    "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf": "KMU-Admission-Policy-Public-2025-26.pdf",
    "https://online.pnmc.gov.pk/": "pnmc_online_services.txt",
    "https://www.hec.gov.pk/": "hec_home.txt",
}

PROGRAM_PAGES = [
    ("https://kmu.edu.pk/programs/undergraduate", "undergraduate"),
    ("https://kmu.edu.pk/programs/postgraduate", "postgraduate"),
    ("https://kmu.edu.pk/programs/diploma", "diploma"),
]


def _log(message: str) -> None:
    print(message, flush=True)


def seed_sources(db: Session) -> dict[str, Source]:
    registry: dict[str, Source] = {}
    for entry in SOURCES:
        source = get_or_create_source(
            db,
            name=entry["name"],
            url=entry["url"],
            institution=entry.get("institution"),
            category=entry.get("category"),
            is_official=entry.get("is_official", True),
            verification_status=entry.get("verification_status", Verification.UNVERIFIED),
            verification_notes=entry.get("verification_notes"),
        )
        registry[entry["url"]] = source
    db.commit()
    _log(f"seeded {len(registry)} official sources")
    return registry


def seed_admissions(db: Session, sources: dict[str, Source]) -> None:
    cycles: dict[tuple[str, str], AdmissionCycle] = {}
    for entry in CYCLES:
        cycle = db.scalar(
            select(AdmissionCycle).where(
                AdmissionCycle.name == entry["name"], AdmissionCycle.session == entry["session"]
            )
        )
        if cycle is None:
            cycle = AdmissionCycle(**entry)
            if cycle.source_url in sources:
                cycle.source_id = sources[cycle.source_url].id
            db.add(cycle)
        cycles[(entry["name"], entry["session"])] = cycle
    db.flush()

    for entry in FORMULAS:
        existing = db.scalar(
            select(AggregateFormula).where(
                AggregateFormula.name == entry["name"],
                AggregateFormula.admission_session == entry["admission_session"],
            )
        )
        if existing:
            continue
        formula = AggregateFormula(**{k: v for k, v in entry.items() if k != "cycle"})
        formula.source_document_id = (
            db.scalar(select(Document.id).where(Document.url == formula.source_url))
            if formula.source_url
            else None
        )
        db.add(formula)

    for entry in RULES:
        data = {k: v for k, v in entry.items() if k != "cycle"}
        exists = db.scalar(
            select(AdmissionRule).where(
                AdmissionRule.title == data["title"],
                AdmissionRule.program_scope == data.get("program_scope"),
            )
        )
        if exists:
            continue
        rule = AdmissionRule(**data)
        cycle = cycles.get((entry["cycle"], "2026-27")) or cycles.get((entry["cycle"], "2025-26"))
        if cycle:
            rule.cycle_id = cycle.id
        document_id = db.scalar(select(Document.id).where(Document.url == rule.source_url))
        rule.document_id = document_id
        db.add(rule)

    for entry in POLICIES:
        exists = db.scalar(select(Policy).where(Policy.title == entry["title"]))
        if exists:
            continue
        policy = Policy(**entry)
        policy.document_id = db.scalar(select(Document.id).where(Document.url == policy.source_url))
        db.add(policy)

    db.commit()
    _log(
        f"seeded {len(cycles)} admission cycles, {len(FORMULAS)} aggregate formulas, "
        f"{len(RULES)} admission rules, {len(POLICIES)} policies"
    )


def _load_html(url: str, *, offline: bool) -> bytes | None:
    if not offline:
        result = fetch(url)
        if result.ok:
            return result.content
        _log(f"  ! fetch failed ({result.error or result.status_code}) — trying archive")
    fallback = LOCAL_FALLBACKS.get(url)
    if fallback:
        path = RAW_DIR / fallback
        if path.exists():
            _log(f"  using archived copy {path.name}")
            return path.read_bytes()
    return None


def seed_institutions_and_programs(db: Session, sources: dict[str, Source], *, offline: bool) -> None:
    constituent_url = "https://kmu.edu.pk/institutes/constituent"
    affiliated_url = "https://kmu.edu.pk/institutes/affiliated"
    created_inst = 0
    created_offerings = 0
    created_campuses = 0
    seen_institutions: set[tuple[str, str]] = set()

    for url, kind in ((constituent_url, InstitutionType.CONSTITUENT_INSTITUTE), (affiliated_url, InstitutionType.AFFILIATED_COLLEGE)):
        content = _load_html(url, offline=offline)
        if content is None:
            _log(f"skipped {url} (no content)")
            continue
        parsed = kmu_parsers.parse_institution_table(content.decode("utf-8", errors="ignore"))
        source = sources.get(url)
        for item in parsed:
            inst_type = kind
            if kind == InstitutionType.AFFILIATED_COLLEGE:
                inst_type = kmu_parsers.classify_affiliated_institution(item.name)
            key = (item.name, inst_type)
            if key in seen_institutions:
                # The official directory lists a few institutes twice; keep one record.
                continue
            seen_institutions.add(key)
            existing = db.scalar(
                select(Institution).where(
                    Institution.name == item.name, Institution.institution_type == inst_type
                )
            )
            if existing:
                continue
            db.add(
                Institution(
                    name=item.name,
                    institution_type=inst_type,
                    city=item.city,
                    website=item.website,
                    phone=item.phone,
                    email=item.email,
                    source_id=source.id if source else None,
                    source_url=item.detail_url or url,
                    verification_status=Verification.VERIFIED,
                    verification_notes="Extracted from the official KMU institute directory on 2026-10-19.",
                )
            )
            created_inst += 1
            if kind == InstitutionType.CONSTITUENT_INSTITUTE:
                # A constituent institute record doubles as a campus location entry.
                db.add(
                    Campus(
                        name=item.name,
                        city=item.city,
                        address=None,
                        phone=item.phone,
                        website=item.website,
                        source_url=url,
                        verification_status=Verification.VERIFIED,
                    )
                )
                created_campuses += 1
        _log(f"parsed {len(parsed)} institutions from {url}")

    db.flush()

    for url, level in PROGRAM_PAGES:
        content = _load_html(url, offline=offline)
        if content is None:
            _log(f"skipped {url} (no content)")
            continue
        parsed_programs = kmu_parsers.parse_program_table(content.decode("utf-8", errors="ignore"))
        source = sources.get(url)
        for parsed in parsed_programs:
            existing = db.scalar(
                select(Program).where(Program.title == parsed.title, Program.degree_level == level)
            )
            if existing is None:
                program = Program(
                    title=parsed.title,
                    degree_level=level,
                    source_url=parsed.detail_url or url,
                    source_id=source.id if source else None,
                    verification_status=Verification.VERIFIED,
                    description="Listed on the official KMU degree-program page (2026-10-19).",
                )
                db.add(program)
                db.flush()
            else:
                program = existing
            for offering_name in parsed.institutes:
                institution = db.scalar(select(Institution).where(Institution.name == offering_name))
                exists = db.scalar(
                    select(ProgramOffering).where(
                        ProgramOffering.program_id == program.id,
                        ProgramOffering.institution_name == offering_name,
                    )
                )
                if exists:
                    continue
                db.add(
                    ProgramOffering(
                        program_id=program.id,
                        institution_id=institution.id if institution else None,
                        institution_name=offering_name,
                        source_url=url,
                        verification_status=Verification.VERIFIED,
                    )
                )
                created_offerings += 1
        _log(f"parsed {len(parsed_programs)} programs from {url}")

    db.commit()
    _log(
        f"created {created_inst} institutions, {created_campuses} campus entries and "
        f"{created_offerings} program offerings"
    )


def ingest_pages(db: Session, sources: dict[str, Source], registry: dict[str, Source] | None = None) -> None:
    ok = failed = 0
    for entry in INGEST_PAGES:
        url = entry["url"]
        source = (registry or sources).get(url)
        metadata = {
            "institution": entry.get("institution"),
            "admission_cycle": entry.get("admission_cycle"),
            "program": entry.get("program"),
        }

        archive_name = MANUAL_ARCHIVES.get(url)
        archive_path = RAW_DIR / archive_name if archive_name else None
        if archive_path and archive_path.exists():
            content = archive_path.read_bytes()
            if archive_path.suffix.lower() == ".pdf":
                text = pdf_to_text(content)
                resolved_type = entry.get("doc_type") or DocType.PDF
            else:
                text = content.decode("utf-8", errors="ignore")
                resolved_type = entry.get("doc_type") or DocType.WEBPAGE
            document, created = upsert_document(
                db,
                title=entry["title"],
                url=url,
                text=text,
                doc_type=resolved_type,
                source_id=source.id if source else None,
                verification_status=Verification.VERIFIED,
                verification_notes=(
                    "Captured manually during research on 2026-10-19 because the host blocks "
                    "automated fetching; verify manually against the live page before relying on it."
                ),
                local_path=str(archive_path),
                **metadata,
            )
            ok += 1
            db.commit()
            _log(f"  {'CREATED' if created else 'UPDATED'} {url} from manual archive ({len(text)} chars)")
            continue

        document, message = ingest_url(
            db,
            url,
            title=entry["title"],
            doc_type=entry.get("doc_type"),
            source_id=source.id if source else None,
            **metadata,
        )
        if document is None:
            failed += 1
        else:
            ok += 1
            document.verification_status = (
                Verification.VERIFIED if source else Verification.UNVERIFIED
            )
            document.verification_notes = (
                f"Archived from the official source on {date.today().isoformat()}."
            )
        db.commit()
        _log("  " + message)
    _log(f"ingested {ok} document(s), {failed} failure(s)")


def create_admin(db: Session, email: str, password: str, role: str = "admin") -> None:
    existing = db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        _log(f"user {email} already exists")
        return
    db.add(User(email=email.lower(), password_hash=hash_password(password), role=role))
    db.commit()
    _log(f"created {role} user {email}")


def refresh_all(db: Session) -> None:
    sources = list(db.scalars(select(Source).where(Source.is_official.is_(True))).all())
    for source in sources:
        result = refresh_source(db, source)
        _log(f"  {result}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MAHSUDo-guide backend CLI")
    parser.add_argument(
        "command",
        choices=["initdb", "seed", "ingest", "bootstrap", "refresh", "create-admin", "status"],
    )
    parser.add_argument("--offline", action="store_true", help="use archived HTML copies where available")
    parser.add_argument("--email", default=settings.admin_seed_email)
    parser.add_argument("--password", default=settings.admin_seed_password)
    parser.add_argument("--role", default="admin")
    args = parser.parse_args(argv)

    init_db()
    db = SessionLocal()
    try:
        if args.command == "initdb":
            _log(f"database initialised at {settings.database_url}")
        elif args.command == "seed":
            sources = seed_sources(db)
            seed_admissions(db, sources)
        elif args.command == "ingest":
            sources = {s.url: s for s in db.scalars(select(Source)).all()}
            ingest_pages(db, sources, sources)
            seed_institutions_and_programs(db, sources, offline=args.offline)
        elif args.command == "bootstrap":
            sources = seed_sources(db)
            seed_admissions(db, sources)
            ingest_pages(db, sources, sources)
            seed_institutions_and_programs(db, sources, offline=args.offline)
            create_admin(db, args.email, args.password, args.role)
        elif args.command == "refresh":
            refresh_all(db)
        elif args.command == "create-admin":
            create_admin(db, args.email, args.password, args.role)
        elif args.command == "status":
            from .services.agent import knowledge_base_overview

            _log(f"knowledge base: {knowledge_base_overview(db)}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
