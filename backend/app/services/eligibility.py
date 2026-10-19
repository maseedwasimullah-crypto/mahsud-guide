"""Rule-based eligibility checks.

Every decision is traceable to a stored AdmissionRule with an official source.
If the student's information is incomplete, the function returns
``insufficient_information`` instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..constants import Verification
from ..models import AdmissionRule

ELIGIBLE = "eligible"
NOT_ELIGIBLE = "not_eligible"
INSUFFICIENT = "insufficient_information"
NO_RULES = "no_matching_rules"


@dataclass
class RuleEvaluation:
    rule_id: int
    title: str
    requirement: str
    satisfied: bool | None
    detail: str
    source_url: str | None
    verification_status: str

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "requirement": self.requirement,
            "satisfied": self.satisfied,
            "detail": self.detail,
            "source_url": self.source_url,
            "verification_status": self.verification_status,
        }


@dataclass
class EligibilityResult:
    status: str
    program: str | None
    evaluations: list[RuleEvaluation] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "program": self.program,
            "evaluations": [e.as_dict() for e in self.evaluations],
            "missing_information": self.missing_information,
            "notes": self.notes
            + [
                "Eligibility guidance is based only on the official rules stored for the "
                "selected admission cycle; always confirm with the official admission office.",
            ],
            "is_admission_decision": False,
        }


def _matches(rule: AdmissionRule, program: str | None) -> bool:
    if not program:
        return True
    scope = (rule.program_scope or "").lower()
    if not scope or scope in {"all", "general"}:
        return True
    return program.lower() in scope or scope in program.lower()


def _subject_alternatives(requirement: str) -> set[str]:
    """Expand a requirement such as 'Physics or Mathematics' into its alternatives.

    Official rules sometimes express alternatives in one entry ("Physics or
    Mathematics", "Physics/Mathematics"); a student offering either subject must
    satisfy the requirement.
    """
    parts = requirement.replace("/", " or ").lower().split(" or ")
    return {part.strip() for part in parts if part.strip()}


def check_eligibility(db: Session, program: str | None, profile: dict) -> EligibilityResult:
    stmt = select(AdmissionRule).where(AdmissionRule.rule_type == "eligibility")
    if program:
        stmt = stmt.where(
            or_(
                AdmissionRule.program_scope.ilike(f"%{program}%"),
                AdmissionRule.program_scope.ilike("%all%"),
                AdmissionRule.program_scope.is_(None),
            )
        )
    rules = [r for r in db.scalars(stmt).all() if _matches(r, program)]

    if not rules:
        return EligibilityResult(
            status=NO_RULES,
            program=program,
            notes=[
                "No verified eligibility rules are stored for this program yet. "
                "Please consult the official KMU admissions page.",
            ],
        )

    evaluations: list[RuleEvaluation] = []
    missing: list[str] = []
    any_failed = False
    any_unknown = False

    for rule in rules:
        checks: list[tuple[str, float | None, float | None, str]] = []
        if rule.min_hssc_percent is not None:
            checks.append(("hssc_percent", profile.get("hssc_percent"), rule.min_hssc_percent, "HSSC / FSc percentage"))
        if rule.min_mdcat_percent is not None:
            checks.append(("mdcat_percent", profile.get("mdcat_percent"), rule.min_mdcat_percent, "MDCAT percentage"))
        if rule.min_entrance_percent is not None:
            checks.append(
                ("entrance_test_percent", profile.get("entrance_test_percent"), rule.min_entrance_percent, "Entrance test percentage")
            )
        if rule.required_subjects:
            provided = {s.lower().strip() for s in (profile.get("subjects") or [])}
            if not provided:
                any_unknown = True
                missing.append(f"Required subjects for {rule.program_scope or 'this program'}")
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.id,
                        title=rule.title,
                        requirement=f"Subjects required: {', '.join(rule.required_subjects)}",
                        satisfied=None,
                        detail="Your subject list was not provided, so this requirement could not be checked.",
                        source_url=rule.source_url,
                        verification_status=rule.verification_status,
                    )
                )
            else:
                lacked = [
                    str(requirement)
                    for requirement in rule.required_subjects
                    if not any(
                        alternative in provided
                        for alternative in _subject_alternatives(str(requirement))
                    )
                ]
                satisfied = not lacked
                any_failed = any_failed or not satisfied
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.id,
                        title=rule.title,
                        requirement=f"Subjects required: {', '.join(rule.required_subjects)}",
                        satisfied=satisfied,
                        detail="All required subjects present."
                        if satisfied
                        else f"Missing subject(s): {', '.join(lacked)}.",
                        source_url=rule.source_url,
                        verification_status=rule.verification_status,
                    )
                )

        for field_name, value, threshold, label in checks:
            if value is None:
                any_unknown = True
                missing.append(label)
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.id,
                        title=rule.title,
                        requirement=f"Minimum {label}: {threshold:g}%",
                        satisfied=None,
                        detail=f"Not checked: {label} was not provided.",
                        source_url=rule.source_url,
                        verification_status=rule.verification_status,
                    )
                )
                continue
            satisfied = float(value) >= float(threshold) - 1e-9
            any_failed = any_failed or not satisfied
            evaluations.append(
                RuleEvaluation(
                    rule_id=rule.id,
                    title=rule.title,
                    requirement=f"Minimum {label}: {threshold:g}%",
                    satisfied=satisfied,
                    detail=f"Your {label}: {float(value):g}%."
                    + ("" if satisfied else " This does not currently meet the official minimum."),
                    source_url=rule.source_url,
                    verification_status=rule.verification_status,
                )
            )

    if any_failed:
        status = NOT_ELIGIBLE
    elif any_unknown:
        status = INSUFFICIENT
    else:
        status = ELIGIBLE

    notes = []
    if any(r.verification_status == Verification.HISTORICAL for r in rules):
        notes.append("Some rules apply to a previous admission cycle and are shown for reference only.")
    if any(r.verification_status == Verification.CONFLICTING for r in rules):
        notes.append("Official sources disagree on some requirements; the latest official notice takes precedence.")
    if any(r.is_demo for r in rules):
        notes.append("Some rules are clearly marked demonstration data and are not official.")

    return EligibilityResult(
        status=status,
        program=program,
        evaluations=evaluations,
        missing_information=sorted(set(missing)),
        notes=notes,
    )
