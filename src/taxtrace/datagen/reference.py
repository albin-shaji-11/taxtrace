"""Reference data for TaxTrace: jurisdictions, tax codes, rates, categories.

This module is the SINGLE SOURCE OF TRUTH for how tax *should* be determined.
Everything downstream (the ground truth, the golden dataset, and later your
YAML rules engine) traces back to the tables defined here.

DELOITTE RELEVANCE
    In a real engagement the client's tax treatment matrix looks exactly like
    TREATMENTS below: a jurisdiction, a product category, a customer type, and
    an effective date window that together decide one rate. Your job as an
    analyst is to get that matrix out of a Tax SME's head and into something a
    machine can execute and an auditor can read.

INTERVIEW ALERT
    "How do you decide which tax rate applies?" is a precedence question. The
    order in PRECEDENCE_NOTES below is the answer. Learn it.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

# --------------------------------------------------------------------------
# Jurisdictions
# --------------------------------------------------------------------------
# country_code, jurisdiction_code, name, tax_regime, standard_rate
JURISDICTIONS: list[tuple[str, str, str, str, float]] = [
    ("AU", "AU-FED", "Australia (Federal GST)", "GST", 0.10),
    ("NZ", "NZ-FED", "New Zealand (GST)", "GST", 0.15),
    ("GB", "GB-VAT", "United Kingdom (VAT)", "VAT", 0.20),
    # United States sales tax is state level. Rates below are destination
    # state rates, simplified to state level (no county/city precision).
    ("US", "US-CA", "California", "SALES_TAX", 0.0725),
    ("US", "US-NY", "New York", "SALES_TAX", 0.04),
    ("US", "US-TX", "Texas", "SALES_TAX", 0.0625),
    ("US", "US-WA", "Washington", "SALES_TAX", 0.065),
    ("US", "US-IL", "Illinois", "SALES_TAX", 0.0625),
    ("US", "US-FL", "Florida", "SALES_TAX", 0.06),
    ("US", "US-OR", "Oregon", "SALES_TAX", 0.00),
    ("US", "US-DE", "Delaware", "SALES_TAX", 0.00),
]

# --------------------------------------------------------------------------
# Product / service categories
# --------------------------------------------------------------------------
CATEGORIES: list[tuple[str, str]] = [
    ("ELEC", "Consumer electronics"),
    ("FOOD_BASIC", "Basic unprepared food"),
    ("FOOD_PREP", "Prepared food and catering"),
    ("BOOKS", "Books and printed matter"),
    ("CLOTH_ADULT", "Adult clothing and footwear"),
    ("CLOTH_CHILD", "Children's clothing and footwear"),
    ("MEDICAL", "Medical devices and supplies"),
    ("SERVICES_PRO", "Professional services"),
    ("SOFTWARE", "Software and SaaS subscriptions"),
    ("FREIGHT", "Freight and delivery"),
    ("EDUCATION", "Education and training"),
    ("ENERGY_DOM", "Domestic energy supply"),
]

# --------------------------------------------------------------------------
# Tax codes
# --------------------------------------------------------------------------
# tax_code, jurisdiction_code, description, rate, is_exempt, is_zero_rated
TAX_CODES: list[tuple[str, str, str, float, bool, bool]] = [
    ("AU-GST-STD", "AU-FED", "Australia GST standard rated", 0.10, False, False),
    ("AU-GST-FRE", "AU-FED", "Australia GST-free supply", 0.00, False, True),
    ("AU-GST-EXP", "AU-FED", "Australia GST-free export", 0.00, False, True),
    ("NZ-GST-STD", "NZ-FED", "New Zealand GST standard rated", 0.15, False, False),
    ("NZ-GST-ZER", "NZ-FED", "New Zealand GST zero rated", 0.00, False, True),
    ("NZ-GST-EXE", "NZ-FED", "New Zealand GST exempt supply", 0.00, True, False),
    ("GB-VAT-STD", "GB-VAT", "UK VAT standard rate", 0.20, False, False),
    ("GB-VAT-RED", "GB-VAT", "UK VAT reduced rate", 0.05, False, False),
    ("GB-VAT-ZER", "GB-VAT", "UK VAT zero rate", 0.00, False, True),
    ("GB-VAT-EXE", "GB-VAT", "UK VAT exempt supply", 0.00, True, False),
]
for _cc, _jc, _name, _regime, _rate in JURISDICTIONS:
    if _cc == "US":
        _st = _jc.split("-")[1]
        TAX_CODES.append((f"US-{_st}-STD", _jc, f"{_name} sales tax standard", _rate, False, False))
        TAX_CODES.append((f"US-{_st}-EXE", _jc, f"{_name} sales tax exempt", 0.00, True, False))

# --------------------------------------------------------------------------
# Treatment matrix. (jurisdiction_code, category) -> tax_code
# --------------------------------------------------------------------------
# Anything not listed falls through to the jurisdiction's standard code.
# These are simplified but directionally real treatments.
TREATMENTS: dict[tuple[str, str], str] = {
    # Australia: basic food, medical and education are GST-free
    ("AU-FED", "FOOD_BASIC"): "AU-GST-FRE",
    ("AU-FED", "MEDICAL"): "AU-GST-FRE",
    ("AU-FED", "EDUCATION"): "AU-GST-FRE",
    # New Zealand taxes almost everything, but financial/education supplies are exempt
    ("NZ-FED", "EDUCATION"): "NZ-GST-EXE",
    # United Kingdom
    ("GB-VAT", "FOOD_BASIC"): "GB-VAT-ZER",
    ("GB-VAT", "BOOKS"): "GB-VAT-ZER",
    ("GB-VAT", "CLOTH_CHILD"): "GB-VAT-ZER",
    ("GB-VAT", "MEDICAL"): "GB-VAT-ZER",
    ("GB-VAT", "ENERGY_DOM"): "GB-VAT-RED",
    ("GB-VAT", "EDUCATION"): "GB-VAT-EXE",
}
# United States: groceries, medical and most professional services are exempt
# in the modelled states. Software and electronics are taxable.
for _cc, _jc, _name, _regime, _rate in JURISDICTIONS:
    if _cc == "US":
        _st = _jc.split("-")[1]
        for _cat in ("FOOD_BASIC", "MEDICAL", "SERVICES_PRO", "EDUCATION"):
            TREATMENTS[(_jc, _cat)] = f"US-{_st}-EXE"

STANDARD_CODE: dict[str, str] = {
    "AU-FED": "AU-GST-STD",
    "NZ-FED": "NZ-GST-STD",
    "GB-VAT": "GB-VAT-STD",
}
for _cc, _jc, _name, _regime, _rate in JURISDICTIONS:
    if _cc == "US":
        STANDARD_CODE[_jc] = f"US-{_jc.split('-')[1]}-STD"

# --------------------------------------------------------------------------
# Rate history. Rates change. Effective dating is the point of this table.
# --------------------------------------------------------------------------
# tax_code, rate, effective_from, effective_to (None = open ended)
RATE_HISTORY: list[tuple[str, float, date, date | None]] = []
for code, jur, desc, rate, is_ex, is_zero in TAX_CODES:
    RATE_HISTORY.append((code, rate, date(2020, 1, 1), None))
# One genuine historical change, so effective dating actually matters:
# UK reduced rate for domestic energy was cut for part of 2022.
RATE_HISTORY = [r for r in RATE_HISTORY if r[0] != "GB-VAT-RED"]
RATE_HISTORY += [
    ("GB-VAT-RED", 0.05, date(2020, 1, 1), date(2022, 3, 31)),
    ("GB-VAT-RED", 0.00, date(2022, 4, 1), date(2022, 9, 30)),
    ("GB-VAT-RED", 0.05, date(2022, 10, 1), None),
]

PRECEDENCE_NOTES = """
Rate determination precedence used by TaxTrace, highest priority first:

  1. Customer exemption certificate, valid for the jurisdiction on the
     transaction date  ->  exempt code, 0%
  2. Explicit (jurisdiction, product category) treatment in TREATMENTS
  3. Jurisdiction standard rate

The rate itself is then looked up from RATE_HISTORY using the transaction
date, not the current date. Using "today's rate" to reprice a historical
transaction is one of the most common and most expensive tax data bugs.
"""


# --------------------------------------------------------------------------
def jurisdictions_df() -> pd.DataFrame:
    return pd.DataFrame(
        JURISDICTIONS,
        columns=["country_code", "jurisdiction_code", "jurisdiction_name",
                 "tax_regime", "standard_rate"],
    )


def categories_df() -> pd.DataFrame:
    return pd.DataFrame(CATEGORIES, columns=["category_code", "category_name"])


def tax_codes_df() -> pd.DataFrame:
    return pd.DataFrame(
        TAX_CODES,
        columns=["tax_code", "jurisdiction_code", "description", "rate",
                 "is_exempt", "is_zero_rated"],
    )


def tax_rates_df() -> pd.DataFrame:
    return pd.DataFrame(
        RATE_HISTORY,
        columns=["tax_code", "rate", "effective_from", "effective_to"],
    )


def rate_on(tax_code: str, when: date) -> float:
    """Rate for a tax code on a given date. Raises if no rate is effective."""
    for code, rate, eff_from, eff_to in RATE_HISTORY:
        if code != tax_code:
            continue
        if when < eff_from:
            continue
        if eff_to is not None and when > eff_to:
            continue
        return rate
    raise KeyError(f"no effective rate for {tax_code} on {when}")


def resolve_tax_code(jurisdiction_code: str, category_code: str,
                     customer_exempt: bool) -> str:
    """Apply the precedence rules and return the tax code that should be used."""
    if customer_exempt:
        exempt = {
            "AU-FED": "AU-GST-FRE",
            "NZ-FED": "NZ-GST-EXE",
            "GB-VAT": "GB-VAT-EXE",
        }.get(jurisdiction_code)
        if exempt:
            return exempt
        return f"US-{jurisdiction_code.split('-')[1]}-EXE"
    treated = TREATMENTS.get((jurisdiction_code, category_code))
    if treated:
        return treated
    return STANDARD_CODE[jurisdiction_code]
