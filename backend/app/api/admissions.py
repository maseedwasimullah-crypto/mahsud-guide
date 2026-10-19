from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import FormulaStatus
from ..db import get_db
from ..models import AggregateFormula
from ..schemas import (
    AggregateRequest,
    AggregateResponse,
    EligibilityRequest,
    EligibilityResponse,
    FormulaOut,
)
from ..services.aggregate import AggregateError, calculate_aggregate, describe_formula
from ..services.eligibility import check_eligibility

router = APIRouter(tags=["admissions"])


@router.get("/aggregate/formulas", response_model=list[FormulaOut])
def list_formulas(
    db: Session = Depends(get_db),
    program: str | None = Query(default=None),
    session: str | None = Query(default=None),
    include_pending: bool = True,
) -> list[FormulaOut]:
    stmt = select(AggregateFormula)
    if program:
        stmt = stmt.where(AggregateFormula.program_scope.ilike(f"%{program}%"))
    if session:
        stmt = stmt.where(AggregateFormula.admission_session == session)
    statuses = [FormulaStatus.ACTIVE]
    if include_pending:
        statuses += [FormulaStatus.PENDING, FormulaStatus.SUPERSEDED]
    stmt = stmt.where(AggregateFormula.status.in_(statuses))
    return [FormulaOut(**describe_formula(f)) for f in db.scalars(stmt).all()]


@router.post("/aggregate/calculate", response_model=AggregateResponse)
def calculate(payload: AggregateRequest, db: Session = Depends(get_db)) -> AggregateResponse:
    formula = db.get(AggregateFormula, payload.formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="Aggregate formula not found.")
    try:
        result = calculate_aggregate(formula, payload.inputs)
    except AggregateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AggregateResponse(**result.as_dict())


@router.post("/eligibility/check", response_model=EligibilityResponse)
def eligibility(payload: EligibilityRequest, db: Session = Depends(get_db)) -> EligibilityResponse:
    profile = {
        "hssc_percent": payload.hssc_percent,
        "mdcat_percent": payload.mdcat_percent,
        "entrance_test_percent": payload.entrance_test_percent,
        "subjects": payload.subjects,
    }
    result = check_eligibility(db, payload.program, profile)
    return EligibilityResponse(**result.as_dict())
