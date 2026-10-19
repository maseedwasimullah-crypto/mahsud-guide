"""Deterministic aggregate (merit) calculation.

Kept strictly separate from the AI layer: the AI may *describe* a result but
never computes one. A formula is only usable when its source has been verified
(``verified=True`` and ``status='active'``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..constants import FormulaStatus
from ..models import AggregateFormula


class AggregateError(ValueError):
    """Raised for invalid inputs or an unusable formula."""


class FormulaUnavailable(AggregateError):
    """Raised when a formula exists but is not verified/active."""


@dataclass
class ComponentResult:
    key: str
    label: str
    weight: float
    percent: float
    contribution: float
    obtained: float | None = None
    total: float | None = None

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "weight": self.weight,
            "percent": round(self.percent, 5),
            "contribution": round(self.contribution, 5),
            "obtained": self.obtained,
            "total": self.total,
        }


@dataclass
class AggregateResult:
    formula_id: int
    formula_name: str
    program_scope: str
    admission_session: str
    aggregate: float
    components: list[ComponentResult] = field(default_factory=list)
    source_url: str | None = None
    source_title: str | None = None
    rounding: int = 5
    explanation: str | None = None
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "formula_id": self.formula_id,
            "formula_name": self.formula_name,
            "program_scope": self.program_scope,
            "admission_session": self.admission_session,
            "aggregate": round(self.aggregate, self.rounding),
            "is_estimate": True,
            "components": [c.as_dict() for c in self.components],
            "source": {"url": self.source_url, "title": self.source_title},
            "rounding": self.rounding,
            "explanation": self.explanation,
            "limitations": self.limitations
            + [
                "This is an estimate computed from the values you entered.",
                "It does not guarantee admission or predict a merit position.",
                "Verify the applicable formula in the current official admission notice.",
            ],
        }


def validate_formula(formula: AggregateFormula) -> None:
    if not formula.verified:
        raise FormulaUnavailable(
            f"The formula '{formula.name}' has not been verified against an official "
            "admission document, so the calculator will not use it."
        )
    if formula.status != FormulaStatus.ACTIVE:
        raise FormulaUnavailable(
            f"The formula '{formula.name}' is marked '{formula.status}' and is not "
            "applicable to the current admission cycle."
        )
    weights = [float(c.get("weight", 0)) for c in formula.components]
    if not weights or abs(sum(weights) - 1.0) > 1e-6:
        raise AggregateError(
            f"Formula '{formula.name}' has component weights summing to {sum(weights):.4f} "
            "instead of 1.0 and cannot be used."
        )
    if not formula.source_url:
        raise FormulaUnavailable(
            f"The formula '{formula.name}' has no official source URL recorded."
        )


def _extract_component_input(component: dict, payload: dict) -> tuple[float, float | None, float | None]:
    """Return (percent, obtained, total)."""
    key = component["key"]
    label = component.get("label", key)
    mode = component.get("input", "percent")
    raw = payload.get(key)
    if raw is None:
        if component.get("required", True):
            raise AggregateError(f"Missing required component: {label}.")
        return 0.0, None, None

    if mode == "percent":
        if isinstance(raw, (int, float)):
            percent = float(raw)
            return percent, None, None
        if isinstance(raw, dict):
            if "percent" in raw:
                return float(raw["percent"]), None, None
            obtained = raw.get("obtained")
            total = raw.get("total")
            if obtained is None or not total:
                raise AggregateError(f"{label}: provide a percentage, or both obtained and total marks.")
            return float(obtained) / float(total) * 100.0, float(obtained), float(total)
        raise AggregateError(f"{label}: unsupported input for a percentage component.")

    # marks mode
    if not isinstance(raw, dict):
        raise AggregateError(f"{label}: provide 'obtained' and optionally 'total' marks.")
    obtained = raw.get("obtained")
    total = raw.get("total", component.get("max_marks"))
    if obtained is None or total in (None, 0):
        raise AggregateError(f"{label}: both obtained and total marks are required.")
    obtained = float(obtained)
    total = float(total)

    allowed_totals = component.get("allowed_totals")
    if allowed_totals and total not in [float(t) for t in allowed_totals]:
        raise AggregateError(
            f"{label}: total marks {total:g} is not one of the accepted values "
            f"({', '.join(str(int(t)) for t in allowed_totals)})."
        )
    min_total = component.get("min_marks")
    max_total = component.get("max_marks")
    if min_total is not None and total < float(min_total):
        raise AggregateError(f"{label}: total marks cannot be below {min_total:g}.")
    if max_total is not None and total > float(max_total):
        raise AggregateError(f"{label}: total marks cannot exceed {max_total:g}.")
    if obtained < 0:
        raise AggregateError(f"{label}: obtained marks cannot be negative.")
    if obtained > total:
        raise AggregateError(f"{label}: obtained marks ({obtained:g}) cannot exceed total ({total:g}).")
    return obtained / total * 100.0, obtained, total


def calculate_aggregate(formula: AggregateFormula, payload: dict) -> AggregateResult:
    validate_formula(formula)
    results: list[ComponentResult] = []
    total = 0.0
    for component in formula.components:
        percent, obtained, comp_total = _extract_component_input(component, payload)
        if percent < 0 or percent > 100:
            raise AggregateError(
                f"{component.get('label', component['key'])}: percentage must be between 0 and 100."
            )
        contribution = percent * float(component["weight"])
        total += contribution
        results.append(
            ComponentResult(
                key=component["key"],
                label=component.get("label", component["key"]),
                weight=float(component["weight"]),
                percent=percent,
                contribution=contribution,
                obtained=obtained,
                total=comp_total,
            )
        )

    return AggregateResult(
        formula_id=formula.id,
        formula_name=formula.name,
        program_scope=formula.program_scope,
        admission_session=formula.admission_session,
        aggregate=total,
        components=results,
        source_url=formula.source_url,
        source_title=formula.source_title,
        rounding=formula.rounding,
        explanation=formula.explanation,
    )


def describe_formula(formula: AggregateFormula) -> dict:
    return {
        "id": formula.id,
        "name": formula.name,
        "program_scope": formula.program_scope,
        "admission_session": formula.admission_session,
        "components": formula.components,
        "rounding": formula.rounding,
        "verified": formula.verified,
        "status": formula.status,
        "source_url": formula.source_url,
        "source_title": formula.source_title,
        "effective_from": formula.effective_from.isoformat() if formula.effective_from else None,
        "effective_to": formula.effective_to.isoformat() if formula.effective_to else None,
        "verification_notes": formula.verification_notes,
        "explanation": formula.explanation,
        "usable": formula.verified and formula.status == FormulaStatus.ACTIVE,
    }
