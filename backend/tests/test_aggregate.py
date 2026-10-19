"""Deterministic aggregate calculation tests.

The worked example (SSC 80, FSc 80, MDCAT 60 -> 70.00000) comes from the
official KMU admission policy PDF and is the acceptance test for the
calculator's arithmetic.
"""

from __future__ import annotations

import pytest

from app.constants import FormulaStatus
from app.services.aggregate import (
    AggregateError,
    FormulaUnavailable,
    calculate_aggregate,
    validate_formula,
)
from tests.conftest import make_mbbs_formula


def test_official_worked_example_from_policy():
    formula = make_mbbs_formula()
    result = calculate_aggregate(formula, {"ssc": 80, "hssc": 80, "mdcat": 60})
    assert result.aggregate == pytest.approx(70.0, abs=1e-9)
    assert round(result.aggregate, 5) == 70.0
    contributions = {c.key: c.contribution for c in result.components}
    assert contributions["ssc"] == pytest.approx(8.0)
    assert contributions["hssc"] == pytest.approx(32.0)
    assert contributions["mdcat"] == pytest.approx(30.0)
    assert result.as_dict()["is_estimate"] is True


def test_marks_mode_obtained_and_total():
    formula = make_mbbs_formula(
        components=[
            {"key": "ssc", "label": "SSC", "weight": 0.5, "input": "marks", "max_marks": 1100},
            {"key": "hssc", "label": "HSSC", "weight": 0.5, "input": "marks", "max_marks": 1100},
        ]
    )
    result = calculate_aggregate(formula, {"ssc": {"obtained": 880, "total": 1100}, "hssc": {"obtained": 990, "total": 1100}})
    assert result.aggregate == pytest.approx(85.0)
    assert result.components[0].percent == pytest.approx(80.0)


def test_percent_dict_with_obtained_total():
    formula = make_mbbs_formula(
        components=[{"key": "mdcat", "label": "MDCAT", "weight": 1.0, "input": "percent"}]
    )
    result = calculate_aggregate(formula, {"mdcat": {"obtained": 150, "total": 200}})
    assert result.aggregate == pytest.approx(75.0)


def test_missing_required_component_raises():
    formula = make_mbbs_formula()
    with pytest.raises(AggregateError, match="Missing required component"):
        calculate_aggregate(formula, {"ssc": 80})


def test_out_of_range_percent_raises():
    formula = make_mbbs_formula(
        components=[{"key": "ssc", "label": "SSC", "weight": 1.0, "input": "percent"}]
    )
    with pytest.raises(AggregateError, match="between 0 and 100"):
        calculate_aggregate(formula, {"ssc": 140})


def test_obtained_greater_than_total_raises():
    formula = make_mbbs_formula(
        components=[{"key": "ssc", "label": "SSC", "weight": 1.0, "input": "marks", "max_marks": 1100}]
    )
    with pytest.raises(AggregateError, match="cannot exceed"):
        calculate_aggregate(formula, {"ssc": {"obtained": 1200, "total": 1100}})


def test_pending_unverified_formula_is_refused():
    formula = make_mbbs_formula(verified=False, status=FormulaStatus.PENDING)
    with pytest.raises(FormulaUnavailable, match="not been verified"):
        calculate_aggregate(formula, {"ssc": 80, "hssc": 80, "mdcat": 60})


def test_superseded_formula_is_refused():
    formula = make_mbbs_formula(status=FormulaStatus.SUPERSEDED)
    with pytest.raises(FormulaUnavailable, match="superseded"):
        calculate_aggregate(formula, {"ssc": 80, "hssc": 80, "mdcat": 60})


def test_formula_without_source_url_is_refused():
    formula = make_mbbs_formula(source_url=None)
    with pytest.raises(FormulaUnavailable, match="no official source URL"):
        validate_formula(formula)


def test_weights_must_sum_to_one():
    formula = make_mbbs_formula(
        components=[
            {"key": "a", "label": "A", "weight": 0.3, "input": "percent"},
            {"key": "b", "label": "B", "weight": 0.3, "input": "percent"},
        ]
    )
    with pytest.raises(AggregateError, match="summing to"):
        validate_formula(formula)
