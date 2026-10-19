"""Rule-based eligibility check tests."""

from __future__ import annotations

from app.services.eligibility import (
    ELIGIBLE,
    INSUFFICIENT,
    NOT_ELIGIBLE,
    NO_RULES,
    check_eligibility,
)


def test_eligible_when_all_requirements_met(seeded_db):
    result = check_eligibility(
        seeded_db,
        "MBBS",
        {
            "hssc_percent": 85.0,
            "mdcat_percent": 70.0,
            "subjects": ["Biology", "Chemistry", "Physics"],
        },
    )
    assert result.status == ELIGIBLE
    assert all(e.satisfied for e in result.evaluations)
    payload = result.as_dict()
    assert payload["is_admission_decision"] is False
    assert any("confirm with the official" in note for note in payload["notes"])


def test_not_eligible_when_mdcat_below_minimum(seeded_db):
    result = check_eligibility(
        seeded_db,
        "MBBS",
        {
            "hssc_percent": 85.0,
            "mdcat_percent": 50.0,
            "subjects": ["Biology", "Chemistry", "Physics"],
        },
    )
    assert result.status == NOT_ELIGIBLE
    failed = [e for e in result.evaluations if e.satisfied is False]
    assert failed and any("55" in e.requirement for e in failed)


def test_not_eligible_when_subject_missing(seeded_db):
    result = check_eligibility(
        seeded_db,
        "MBBS",
        {"hssc_percent": 85.0, "mdcat_percent": 70.0, "subjects": ["Biology", "Chemistry"]},
    )
    assert result.status == NOT_ELIGIBLE
    assert any("Missing subject" in e.detail for e in result.evaluations)


def test_subject_alternative_mathematics_accepted(seeded_db):
    result = check_eligibility(
        seeded_db,
        "MBBS",
        {"hssc_percent": 85.0, "mdcat_percent": 70.0, "subjects": ["Biology", "Chemistry", "Mathematics"]},
    )
    assert result.status == ELIGIBLE


def test_insufficient_information_when_fields_omitted(seeded_db):
    result = check_eligibility(seeded_db, "MBBS", {})
    assert result.status == INSUFFICIENT
    assert "HSSC / FSc percentage" in result.missing_information
    assert "MDCAT percentage" in result.missing_information
    assert all(e.satisfied is None for e in result.evaluations)


def test_no_rules_for_unknown_program(seeded_db):
    result = check_eligibility(seeded_db, "BS Astronautics", {})
    assert result.status == NO_RULES
    assert result.notes
