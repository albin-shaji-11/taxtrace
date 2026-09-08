"""Ground truth generation.

The important idea, and the reason this project can teach you anything:

    We compute the CORRECT answer first, store it in an answer key, and only
    then corrupt the source data that you will be given.

That means every exception your pipeline finds can be checked. You are not
guessing whether a variance is real. You can measure your own precision and
recall against a known truth, which is exactly what a real data quality
engagement does with a sampled and manually verified population.

INTERVIEW ALERT
    "How do you know your data quality rules are any good?" The honest answer
    is that you need labelled data. Either someone verifies a sample by hand,
    or you inject known faults. This module is the injected-faults approach.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .reference import (CATEGORIES, JURISDICTIONS, rate_on, resolve_tax_code)

CURRENCY_BY_COUNTRY = {"AU": "AUD", "NZ": "NZD", "GB": "GBP", "US": "USD"}

SOURCE_SYSTEMS = {
    "SAP_AU": {"country": "AU", "share": 0.36},
    "DYNAMICS_UK": {"country": "GB", "share": 0.28},
    "ORACLE_US": {"country": "US", "share": 0.24},
    "NETSUITE_NZ": {"country": "NZ", "share": 0.12},
}

# Categories weighted so the dataset is not uniform. Real ERP extracts are
# dominated by a handful of high volume categories.
CATEGORY_WEIGHTS = {
    "ELEC": 0.19, "FOOD_BASIC": 0.14, "FOOD_PREP": 0.09, "BOOKS": 0.06,
    "CLOTH_ADULT": 0.12, "CLOTH_CHILD": 0.05, "MEDICAL": 0.05,
    "SERVICES_PRO": 0.10, "SOFTWARE": 0.08, "FREIGHT": 0.07,
    "EDUCATION": 0.03, "ENERGY_DOM": 0.02,
}

GL_ACCOUNTS = ["400100", "400200", "400300", "410100", "410200", "420100",
               "430100", "440100"]


def money(x: float) -> float:
    """Round to 2 decimal places, half up, the way finance systems do.

    PRODUCTION ALERT
        Python's round() uses banker's rounding, so round(2.675, 2) is 2.67,
        not 2.68. Finance and tax almost always want half-up. Getting this
        wrong produces thousands of one cent variances that look like a rate
        problem and are not.
    """
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _customer_is_exempt(cust: pd.Series, txn_date: date) -> bool:
    """Exemption applies only if a certificate exists AND is valid that day."""
    if not cust["exemption_certificate_id"]:
        return False
    vf, vt = cust["exemption_valid_from"], cust["exemption_valid_to"]
    if vf is None or vt is None:
        return False
    return vf <= txn_date <= vt


def build_ground_truth(rng: np.random.Generator, customers: pd.DataFrame,
                       vendors: pd.DataFrame, n_rows: int,
                       start: date = date(2023, 1, 1),
                       end: date = date(2025, 12, 31)) -> pd.DataFrame:
    """Generate the correct, uncorrupted transaction population."""
    cat_codes = [c for c, _ in CATEGORIES]
    cat_p = np.array([CATEGORY_WEIGHTS[c] for c in cat_codes], dtype=float)
    cat_p = cat_p / cat_p.sum()

    src_names = list(SOURCE_SYSTEMS)
    src_p = np.array([SOURCE_SYSTEMS[s]["share"] for s in src_names])
    src_p = src_p / src_p.sum()

    # Index customers by country so a US source system sells to US customers.
    cust_by_country: dict[str, pd.DataFrame] = {
        c: customers[customers["country_code"] == c].reset_index(drop=True)
        for c in CURRENCY_BY_COUNTRY
    }
    vend_by_country: dict[str, pd.DataFrame] = {
        c: vendors[vendors["country_code"] == c].reset_index(drop=True)
        for c in CURRENCY_BY_COUNTRY
    }

    span = (end - start).days
    rows = []
    for i in range(1, n_rows + 1):
        source = src_names[rng.choice(len(src_names), p=src_p)]
        country = SOURCE_SYSTEMS[source]["country"]

        pool = cust_by_country[country]
        cust = pool.iloc[int(rng.integers(0, len(pool)))]
        vpool = vend_by_country[country]
        vend = vpool.iloc[int(rng.integers(0, len(vpool)))]

        txn_date = start + timedelta(days=int(rng.integers(0, span + 1)))
        category = cat_codes[rng.choice(len(cat_codes), p=cat_p)]
        jurisdiction = cust["jurisdiction_code"]

        # Amounts. Log-normal gives a realistic long tail rather than a
        # uniform spread, which matters when you later test outlier detection.
        net = float(np.exp(rng.normal(4.2, 1.15)))
        net = money(min(max(net, 1.50), 250_000.0))

        # Some source systems send tax-inclusive (gross) amounts.
        inclusive = bool(rng.random() < (0.35 if source == "DYNAMICS_UK" else 0.12))

        exempt = _customer_is_exempt(cust, txn_date)
        tax_code = resolve_tax_code(jurisdiction, category, exempt)
        rate = rate_on(tax_code, txn_date)

        if inclusive:
            gross = net
            taxable = money(gross / (1 + rate)) if rate else gross
            tax = money(gross - taxable)
        else:
            taxable = net
            tax = money(taxable * rate)
            gross = money(taxable + tax)

        rows.append({
            "transaction_id": f"TXN{i:08d}",
            "invoice_number": f"INV-{country}-{txn_date.year}-{i:07d}",
            "source_system": source,
            "transaction_date": txn_date,
            "posting_date": txn_date + timedelta(days=int(rng.integers(0, 6))),
            "customer_id": cust["customer_id"],
            "vendor_id": vend["vendor_id"],
            "country_code": country,
            "jurisdiction_code": jurisdiction,
            "region": cust["region"],
            "postcode": cust["postcode"],
            "product_category": category,
            "currency_code": CURRENCY_BY_COUNTRY[country],
            "amount_type": "GROSS" if inclusive else "NET",
            "gross_amount": gross,
            "taxable_amount": taxable,
            "tax_code": tax_code,
            "tax_rate": rate,
            "tax_amount": tax,
            "gl_account": str(rng.choice(GL_ACCOUNTS)),
            "customer_exempt": exempt,
            "is_credit_note": bool(rng.random() < 0.035),
        })

    df = pd.DataFrame(rows)

    # Credit notes are negative on every monetary column.
    neg = df["is_credit_note"]
    for col in ("gross_amount", "taxable_amount", "tax_amount"):
        df.loc[neg, col] = -df.loc[neg, col]

    return df
