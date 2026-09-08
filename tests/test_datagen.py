"""Tests for the data generator.

The generator is the foundation of every later exercise, so it gets tests from
day one. If the ground truth is wrong, everything you measure against it is
wrong and you will not know.

INTERVIEW ALERT
    "What would you test first in a data pipeline?" The determinism of your
    inputs. If you cannot reproduce the input you cannot reproduce the bug.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from taxtrace.datagen import reference
from taxtrace.datagen.corrupt import corrupt
from taxtrace.datagen.entities import build_customers, build_vendors
from taxtrace.datagen.truth import build_ground_truth, money


# --------------------------------------------------------------- rounding
@pytest.mark.parametrize(
    "raw,expected",
    [(2.675, 2.68), (2.665, 2.67), (0.125, 0.13), (10.0, 10.0), (0.005, 0.01)],
)
def test_money_rounds_half_up(raw, expected):
    """Finance rounds half up. Python's round() does not."""
    assert money(raw) == expected


def test_money_differs_from_python_round_somewhere():
    """Guard the assumption above. If this ever fails, the docs are wrong."""
    assert money(2.675) != round(2.675, 2)


# ------------------------------------------------------------- reference
def test_every_jurisdiction_has_a_standard_code():
    for _cc, jc, _name, _regime, _rate in reference.JURISDICTIONS:
        assert jc in reference.STANDARD_CODE


def test_every_tax_code_has_an_effective_rate_today():
    for code, *_ in reference.TAX_CODES:
        assert reference.rate_on(code, date(2025, 6, 30)) >= 0


def test_uk_reduced_rate_is_effective_dated():
    """The 2022 window is the whole point of having a rate history."""
    assert reference.rate_on("GB-VAT-RED", date(2022, 1, 15)) == 0.05
    assert reference.rate_on("GB-VAT-RED", date(2022, 6, 15)) == 0.00
    assert reference.rate_on("GB-VAT-RED", date(2023, 1, 15)) == 0.05


def test_exempt_customer_beats_category_treatment():
    """Precedence: exemption wins over the category rule."""
    normal = reference.resolve_tax_code("AU-FED", "ELEC", customer_exempt=False)
    exempt = reference.resolve_tax_code("AU-FED", "ELEC", customer_exempt=True)
    assert normal == "AU-GST-STD"
    assert exempt == "AU-GST-FRE"


def test_unlisted_category_falls_through_to_standard():
    assert reference.resolve_tax_code("NZ-FED", "ELEC", False) == "NZ-GST-STD"


# ----------------------------------------------------------- ground truth
@pytest.fixture(scope="module")
def truth():
    rng = np.random.default_rng(1234)
    customers = build_customers(rng, 300)
    vendors = build_vendors(rng, 60)
    return build_ground_truth(rng, customers, vendors, 800)


def test_ground_truth_has_expected_shape(truth):
    assert len(truth) == 800
    assert truth["transaction_id"].is_unique


def test_ground_truth_tax_reconciles_to_rate(truth):
    """Before corruption, every non credit note must reconcile to within a cent.

    PRODUCTION ALERT, and this test found it for real.

    The first version of this assertion was `(diff <= 0.01).all()` and it
    FAILED on three rows where the difference was exactly one cent. The reason
    is that 2.52 - 2.51 evaluates to 0.010000000000000231 in binary floating
    point, which is greater than 0.01.

    This is not a contrived example. It is the single most common source of
    spurious tax variances in production, and it is why a reconciliation
    tolerance must be applied to a ROUNDED difference, never to a raw float.
    Day 4 builds the reconciliation engine on exactly this principle.

    Tax-inclusive rows derive tax by subtraction, so a one cent difference from
    the multiply-and-round path is expected and acceptable.
    """
    live = truth[~truth["is_credit_note"]]
    expected = (live["taxable_amount"] * live["tax_rate"]).map(money)
    diff = (expected - live["tax_amount"]).abs().round(2)
    assert (diff <= 0.01).all()


def test_float_subtraction_is_not_exact():
    """Guards the lesson above so nobody 'simplifies' the tolerance away."""
    assert 2.52 - 2.51 != 0.01
    assert round(2.52 - 2.51, 2) == 0.01


def test_zero_rated_codes_produce_zero_tax(truth):
    zero = truth[truth["tax_rate"] == 0]
    assert (zero["tax_amount"].abs() < 0.005).all()


def test_credit_notes_are_negative(truth):
    cn = truth[truth["is_credit_note"]]
    if len(cn):
        assert (cn["tax_amount"] <= 0).all()
        assert (cn["taxable_amount"] <= 0).all()


def test_generation_is_deterministic():
    def build():
        rng = np.random.default_rng(99)
        c = build_customers(rng, 100)
        v = build_vendors(rng, 20)
        return build_ground_truth(rng, c, v, 200)

    a, b = build(), build()
    assert a.equals(b)


# --------------------------------------------------------------- corruption
def test_corruption_logs_every_fault(truth):
    rng = np.random.default_rng(7)
    dirty, log = corrupt(truth, rng)
    faults = log.to_frame()
    assert len(faults) > 0
    assert set(faults.columns) == {"transaction_id", "fault_code", "tier", "field", "note"}
    assert faults["tier"].isin({"LOUD", "MEDIUM", "SUBTLE"}).all()


def test_corruption_does_not_shrink_the_population(truth):
    rng = np.random.default_rng(7)
    dirty, _ = corrupt(truth, rng)
    assert len(dirty) >= len(truth)


def test_corruption_does_not_mutate_the_input(truth):
    before = truth.copy()
    corrupt(truth, np.random.default_rng(7))
    assert truth.equals(before)
