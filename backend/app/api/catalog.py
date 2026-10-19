from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..constants import Verification
from ..db import get_db
from ..models import (
    AdmissionCycle,
    AdmissionRule,
    Campus,
    CurriculumRecord,
    Document,
    FacultyMember,
    Institution,
    Policy,
    Program,
)
from ..schemas import (
    AdmissionCycleOut,
    AdmissionRuleOut,
    CampusOut,
    CurriculumOut,
    DocumentDetail,
    DocumentOut,
    FacultyOut,
    InstitutionListResponse,
    InstitutionOut,
    PolicyOut,
    ProgramDetail,
    ProgramListResponse,
    ProgramOut,
    SourceOut,
)
from ..models import Source

router = APIRouter(tags=["catalog"])


@router.get("/sources", response_model=list[SourceOut])
def list_sources(
    db: Session = Depends(get_db),
    q: str | None = None,
    category: str | None = None,
    verification_status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Source]:
    stmt = select(Source).order_by(Source.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Source.name.ilike(like), Source.url.ilike(like), Source.institution.ilike(like)))
    if category:
        stmt = stmt.where(Source.category == category)
    if verification_status:
        stmt = stmt.where(Source.verification_status == verification_status)
    return list(db.scalars(stmt.limit(limit)).all())


@router.get("/sources/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db)) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return source


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    q: str | None = None,
    doc_type: str | None = None,
    institution: str | None = None,
    admission_cycle: str | None = None,
    verification_status: str | None = None,
    include_demo: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Document]:
    stmt = select(Document).order_by(Document.retrieved_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Document.title.ilike(like), Document.url.ilike(like)))
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if institution:
        stmt = stmt.where(Document.institution.ilike(f"%{institution}%"))
    if admission_cycle:
        stmt = stmt.where(Document.admission_cycle.ilike(f"%{admission_cycle}%"))
    if verification_status:
        stmt = stmt.where(Document.verification_status == verification_status)
    if not include_demo:
        stmt = stmt.where(Document.is_demo.is_(False))
    return list(db.scalars(stmt.limit(limit)).all())


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentDetail:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    chunks = sorted(document.chunks, key=lambda c: c.chunk_index)[:5]
    detail = DocumentDetail.model_validate(document)
    detail.chunk_count = len(document.chunks)
    detail.preview = [
        {"index": c.chunk_index, "heading": c.heading, "text": c.text[:600]} for c in chunks
    ]
    return detail


@router.get("/programs", response_model=ProgramListResponse)
def list_programs(
    db: Session = Depends(get_db),
    q: str | None = None,
    degree_level: str | None = None,
    institution: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ProgramListResponse:
    stmt = select(Program)
    if q:
        stmt = stmt.where(Program.title.ilike(f"%{q}%"))
    if degree_level:
        stmt = stmt.where(Program.degree_level == degree_level)
    if institution:
        from ..models import ProgramOffering

        subquery = select(ProgramOffering.program_id).where(
            ProgramOffering.institution_name.ilike(f"%{institution}%")
        )
        stmt = stmt.where(Program.id.in_(subquery))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Program.title).offset(offset).limit(limit)).all())
    return ProgramListResponse(total=total, items=[ProgramOut.model_validate(p) for p in items])


@router.get("/programs/{program_id}", response_model=ProgramDetail)
def get_program(program_id: int, db: Session = Depends(get_db)) -> ProgramDetail:
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found.")
    detail = ProgramDetail.model_validate(program)
    detail.offerings = [
        {
            "institution_id": o.institution_id,
            "institution_name": o.institution_name,
            "source_url": o.source_url,
            "verification_status": o.verification_status,
        }
        for o in program.offerings
    ]
    return detail


@router.get("/institutions", response_model=InstitutionListResponse)
def list_institutions(
    db: Session = Depends(get_db),
    q: str | None = None,
    type: str | None = Query(default=None, description="institution_type filter"),
    city: str | None = None,
    limit: int = Query(default=100, ge=1, le=600),
    offset: int = Query(default=0, ge=0),
) -> InstitutionListResponse:
    stmt = select(Institution)
    if q:
        stmt = stmt.where(Institution.name.ilike(f"%{q}%"))
    if type:
        stmt = stmt.where(Institution.institution_type == type)
    if city:
        stmt = stmt.where(Institution.city.ilike(f"%{city}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Institution.name).offset(offset).limit(limit)).all())
    return InstitutionListResponse(total=total, items=[InstitutionOut.model_validate(i) for i in items])


@router.get("/institutions/{institution_id}", response_model=InstitutionOut)
def get_institution(institution_id: int, db: Session = Depends(get_db)) -> Institution:
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found.")
    return institution


@router.get("/campuses", response_model=list[CampusOut])
def list_campuses(
    db: Session = Depends(get_db),
    q: str | None = None,
    city: str | None = None,
) -> list[Campus]:
    stmt = select(Campus).order_by(Campus.name)
    if q:
        stmt = stmt.where(Campus.name.ilike(f"%{q}%"))
    if city:
        stmt = stmt.where(Campus.city.ilike(f"%{city}%"))
    return list(db.scalars(stmt).all())


@router.get("/faculty", response_model=list[FacultyOut])
def list_faculty(
    db: Session = Depends(get_db),
    q: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[FacultyMember]:
    stmt = select(FacultyMember)
    if q:
        stmt = stmt.where(FacultyMember.name.ilike(f"%{q}%"))
    return list(db.scalars(stmt.limit(limit)).all())


@router.get("/curriculum", response_model=list[CurriculumOut])
def list_curriculum(
    db: Session = Depends(get_db),
    q: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[CurriculumRecord]:
    stmt = select(CurriculumRecord)
    if q:
        stmt = stmt.where(CurriculumRecord.title.ilike(f"%{q}%"))
    return list(db.scalars(stmt.limit(limit)).all())


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    category: str | None = None,
) -> list[Policy]:
    stmt = select(Policy).order_by(Policy.title)
    if category:
        stmt = stmt.where(Policy.category == category)
    return list(db.scalars(stmt).all())


@router.get("/admission-cycles", response_model=list[AdmissionCycleOut])
def list_cycles(
    db: Session = Depends(get_db),
    session: str | None = None,
) -> list[AdmissionCycle]:
    stmt = select(AdmissionCycle).order_by(AdmissionCycle.session.desc(), AdmissionCycle.name)
    if session:
        stmt = stmt.where(AdmissionCycle.session == session)
    return list(db.scalars(stmt).all())


@router.get("/admission-rules", response_model=list[AdmissionRuleOut])
def list_rules(
    db: Session = Depends(get_db),
    program: str | None = None,
    rule_type: str | None = None,
) -> list[AdmissionRule]:
    stmt = select(AdmissionRule)
    if program:
        stmt = stmt.where(AdmissionRule.program_scope.ilike(f"%{program}%"))
    if rule_type:
        stmt = stmt.where(AdmissionRule.rule_type == rule_type)
    return list(db.scalars(stmt).all())


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)) -> dict:
    """Honest coverage report so the UI never overstates what is known."""
    counts = {
        "sources": db.scalar(select(func.count(Source.id))) or 0,
        "documents": db.scalar(select(func.count(Document.id))) or 0,
        "verified_documents": db.scalar(
            select(func.count(Document.id)).where(Document.verification_status == Verification.VERIFIED)
        )
        or 0,
        "unverified_documents": db.scalar(
            select(func.count(Document.id)).where(Document.verification_status == Verification.UNVERIFIED)
        )
        or 0,
        "institutions": db.scalar(select(func.count(Institution.id))) or 0,
        "programs": db.scalar(select(func.count(Program.id))) or 0,
        "admission_rules": db.scalar(select(func.count(AdmissionRule.id))) or 0,
        "faculty_records": db.scalar(select(func.count(FacultyMember.id))) or 0,
        "curriculum_records": db.scalar(select(func.count(CurriculumRecord.id))) or 0,
    }
    gaps = [
        "Individual faculty members are not yet extracted; the official page indexes faculty per institute only.",
        "Postgraduate merit formula has not been retrieved from an official document; the calculator refuses it.",
        "Curriculum documents are not linked per-program yet.",
        "Affiliated-college affiliation dates are not published in the KMU directory.",
    ]
    return {"counts": counts, "known_gaps": gaps}
