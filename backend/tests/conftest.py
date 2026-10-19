"""Shared pytest fixtures.

Environment variables are set *before* any app import so that Settings reads
the test configuration instead of the developer's real .env / database.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "mahsud_pytest.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["LLM_PROVIDER"] = "none"
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["RATE_LIMIT_REQUESTS"] = "100000"
os.environ["MIN_REQUEST_INTERVAL_SECONDS"] = "0"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.constants import FormulaStatus, Role, RuleType, Verification  # noqa: E402
from app.db import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AdmissionRule, AggregateFormula, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.ingest import upsert_document  # noqa: E402

ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "correct-horse-battery-staple"

MBBS_COMPONENTS = [
    {"key": "ssc", "label": "SSC / Matriculation", "weight": 0.10, "input": "percent"},
    {"key": "hssc", "label": "FSc / HSSC", "weight": 0.40, "input": "percent"},
    {"key": "mdcat", "label": "MDCAT", "weight": 0.50, "input": "percent"},
]


def make_mbbs_formula(**overrides) -> AggregateFormula:
    defaults = dict(
        name="MBBS test formula",
        program_scope="MBBS",
        admission_session="2025-26",
        components=MBBS_COMPONENTS,
        rounding=5,
        source_url="https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        source_title="Admission Policy 2025-26",
        verified=True,
        status=FormulaStatus.ACTIVE,
    )
    defaults.update(overrides)
    return AggregateFormula(**defaults)


@pytest.fixture()
def db() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded_db(db: Session) -> Session:
    db.add(make_mbbs_formula())
    db.add(
        make_mbbs_formula(
            name="Postgraduate test formula",
            program_scope="Postgraduate",
            admission_session="2025-26",
            verified=False,
            status=FormulaStatus.PENDING,
        )
    )
    db.add(
        AdmissionRule(
            program_scope="MBBS",
            rule_type=RuleType.ELIGIBILITY,
            title="MBBS basic eligibility (HSSC and MDCAT)",
            text="HSSC with 60% and MDCAT with 55%; subjects Biology, Chemistry, Physics/Mathematics.",
            min_hssc_percent=60.0,
            min_mdcat_percent=55.0,
            required_subjects=["Biology", "Chemistry", "Physics or Mathematics"],
            source_url="https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
            verification_status=Verification.VERIFIED,
        )
    )
    db.add(User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role=Role.ADMIN))
    db.add(
        upsert_document(
            db,
            title="KMU Admission Policy 2025-26 (extract)",
            url="https://example.test/kmu-policy",
            text=(
                "ADMISSION POLICY 2025-26 Public Sector Medical and Dental Colleges of "
                "Khyber Pakhtunkhwa. The aggregate for MBBS and BDS is calculated as SSC "
                "10 percent, FSc 40 percent and MDCAT 50 percent. The minimum MDCAT "
                "score for MBBS is 55 percent. The closing date for online applications "
                "is 9 October 2026."
            ),
            verification_status=Verification.VERIFIED,
        )[0]
    )
    db.commit()
    return db


@pytest.fixture()
def client(seeded_db: Session):
    def override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
