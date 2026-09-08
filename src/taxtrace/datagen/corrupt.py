"""Deliberate corruption of the clean transaction population.

Every corruption is recorded against the transaction id in a fault log, so the
answer key knows exactly what was done. That lets you score your own pipeline:

    precision = of the exceptions you raised, how many were real faults
    recall    = of the real faults, how many did you catch

INTERVIEW ALERT
    A data quality framework that flags everything has perfect recall and is
    useless. One that flags nothing has perfect precision and is useless.
    Being able to say that sentence out loud puts you ahead of most candidates.

The corruptions are split into three tiers.

    LOUD    obvious on a profile, e.g. a null id or a text date
    MEDIUM  needs a rule or a join to find, e.g. an unknown tax code
    SUBTLE  needs reconciliation or statistics to find, e.g. a rate applied
            from the wrong effective period, or a 0.4 per cent understatement

The SUBTLE tier is the point of the exercise. Anyone can find a null.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .truth import money

# --------------------------------------------------------------------------
# Value variants used to make the same real world thing look different
# --------------------------------------------------------------------------
COUNTRY_VARIANTS = {
    "AU": ["AU", "AUS", "Australia", "australia", "AUSTRALIA", " AU "],
    "NZ": ["NZ", "NZL", "New Zealand", "new zealand", "N.Z."],
    "GB": ["GB", "UK", "United Kingdom", "Great Britain", "gb", "U.K."],
    "US": ["US", "USA", "United States", "U.S.A.", "united states"],
}
CURRENCY_VARIANTS = {
    "AUD": ["AUD", "aud", "AU$", "A$"],
    "NZD": ["NZD", "nzd", "NZ$"],
    "GBP": ["GBP", "gbp", "£", "GBP "],
    "USD": ["USD", "usd", "US$", "$"],
}
REGION_VARIANTS = {
    "VIC": ["VIC", "Vic", "Victoria", "vic"],
    "NSW": ["NSW", "N.S.W.", "New South Wales"],
    "QLD": ["QLD", "Qld", "Queensland"],
    "ENG": ["ENG", "England", "eng"],
    "SCT": ["SCT", "Scotland"],
}
UNKNOWN_TAX_CODES = ["AU-GST-OLD", "ZZ-UNKNOWN", "GB-VAT-15", "US-NA-STD",
                     "TAXFREE", "N/A", "-"]
BAD_GL = ["999999", "TBC", "", "40010O", "SUSPENSE"]


class FaultLog:
    """Records every corruption applied, keyed by transaction id."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, txn_id: str, fault_code: str, tier: str, field: str,
            note: str = "") -> None:
        self.rows.append({"transaction_id": txn_id, "fault_code": fault_code,
                          "tier": tier, "field": field, "note": note})

    def to_frame(self) -> pd.DataFrame:
        if not self.rows:
            return pd.DataFrame(columns=["transaction_id", "fault_code", "tier",
                                         "field", "note"])
        return pd.DataFrame(self.rows)


def _pick(rng: np.random.Generator, idx: pd.Index, frac: float) -> np.ndarray:
    """Choose a random subset of row labels."""
    n = max(1, int(len(idx) * frac))
    return rng.choice(np.asarray(idx), size=min(n, len(idx)), replace=False)


def corrupt(df: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, FaultLog]:
    """Return a corrupted copy of the transactions plus the fault log."""
    d = df.copy()
    log = FaultLog()

    # Everything below writes into object columns, so widen the money and id
    # columns up front rather than fighting dtype warnings later.
    for c in ("transaction_id", "customer_id", "vendor_id", "tax_code",
              "country_code", "currency_code", "region", "postcode",
              "gl_account", "product_category", "amount_type"):
        d[c] = d[c].astype("object")
    d["transaction_date"] = d["transaction_date"].astype("object")

    # ---------------------------------------------------------------- LOUD
    # 1. missing customer id
    for i in _pick(rng, d.index, 0.012):
        log.add(d.at[i, "transaction_id"], "F001", "LOUD", "customer_id",
                "customer id blanked")
        d.at[i, "customer_id"] = None

    # 2. duplicate transaction ids (same id reused on a different row)
    dup_src = _pick(rng, d.index, 0.004)
    dup_tgt = _pick(rng, d.index, 0.004)
    for s, t in zip(dup_src, dup_tgt):
        if s == t:
            continue
        log.add(d.at[t, "transaction_id"], "F002", "LOUD", "transaction_id",
                f"id overwritten with {d.at[s, 'transaction_id']}")
        d.at[t, "transaction_id"] = d.at[s, "transaction_id"]

    # 3. mixed date formats and a few unparseable ones
    for i in _pick(rng, d.index, 0.09):
        dt = d.at[i, "transaction_date"]
        style = rng.integers(0, 5)
        if style == 0:
            d.at[i, "transaction_date"] = dt.strftime("%d/%m/%Y")
        elif style == 1:
            d.at[i, "transaction_date"] = dt.strftime("%m-%d-%Y")
        elif style == 2:
            d.at[i, "transaction_date"] = dt.strftime("%d %b %Y")
        elif style == 3:
            d.at[i, "transaction_date"] = dt.strftime("%Y%m%d")
        else:
            d.at[i, "transaction_date"] = dt.strftime("%d.%m.%Y")
        log.add(d.at[i, "transaction_id"], "F003", "LOUD", "transaction_date",
                "non ISO date format")

    for i in _pick(rng, d.index, 0.0035):
        log.add(d.at[i, "transaction_id"], "F004", "LOUD", "transaction_date",
                "invalid or impossible date")
        d.at[i, "transaction_date"] = str(rng.choice(
            ["2024-02-30", "31/13/2024", "0000-00-00", "TBC", ""]))

    # 4. null and unknown tax codes
    for i in _pick(rng, d.index, 0.011):
        log.add(d.at[i, "transaction_id"], "F005", "LOUD", "tax_code", "null tax code")
        d.at[i, "tax_code"] = None
    for i in _pick(rng, d.index, 0.009):
        bad = str(rng.choice(UNKNOWN_TAX_CODES))
        log.add(d.at[i, "transaction_id"], "F006", "MEDIUM", "tax_code",
                f"unknown tax code {bad}")
        d.at[i, "tax_code"] = bad

    # 5. country, currency, region and case/whitespace noise
    for i in _pick(rng, d.index, 0.22):
        cc = d.at[i, "country_code"]
        d.at[i, "country_code"] = str(rng.choice(COUNTRY_VARIANTS[cc]))
    for i in _pick(rng, d.index, 0.20):
        cur = str(d.at[i, "currency_code"]).strip()
        if cur in CURRENCY_VARIANTS:
            d.at[i, "currency_code"] = str(rng.choice(CURRENCY_VARIANTS[cur]))
    for i in _pick(rng, d.index, 0.10):
        r = d.at[i, "region"]
        if r in REGION_VARIANTS:
            d.at[i, "region"] = str(rng.choice(REGION_VARIANTS[r]))
    for i in _pick(rng, d.index, 0.06):
        d.at[i, "product_category"] = f"  {str(d.at[i, 'product_category']).lower()} "

    # 6. malformed postcodes and missing addresses
    for i in _pick(rng, d.index, 0.02):
        log.add(d.at[i, "transaction_id"], "F007", "MEDIUM", "postcode",
                "malformed postcode")
        d.at[i, "postcode"] = str(rng.choice(["0", "ABCDE", "999999", "", "N/A"]))

    # 7. invalid GL accounts
    for i in _pick(rng, d.index, 0.008):
        log.add(d.at[i, "transaction_id"], "F008", "MEDIUM", "gl_account",
                "invalid GL account")
        d.at[i, "gl_account"] = str(rng.choice(BAD_GL))

    # 8. zero value and unexplained negative transactions
    for i in _pick(rng, d.index, 0.006):
        log.add(d.at[i, "transaction_id"], "F009", "MEDIUM", "taxable_amount",
                "zero value transaction")
        d.at[i, "taxable_amount"] = 0.0
        d.at[i, "tax_amount"] = 0.0
        d.at[i, "gross_amount"] = 0.0
    for i in _pick(rng, d.index, 0.004):
        if bool(d.at[i, "is_credit_note"]):
            continue
        log.add(d.at[i, "transaction_id"], "F010", "MEDIUM", "taxable_amount",
                "negative amount without credit note flag")
        for c in ("taxable_amount", "tax_amount", "gross_amount"):
            d.at[i, c] = -abs(float(d.at[i, c]))

    # -------------------------------------------------------------- SUBTLE
    # 9. tax amount understated or overstated by a small percentage
    for i in _pick(rng, d.index, 0.014):
        base = float(d.at[i, "tax_amount"])
        if base == 0:
            continue
        drift = float(rng.uniform(0.004, 0.02)) * (1 if rng.random() < 0.5 else -1)
        d.at[i, "tax_amount"] = money(base * (1 + drift))
        log.add(d.at[i, "transaction_id"], "F011", "SUBTLE", "tax_amount",
                f"tax drifted by {drift:+.3%}")

    # 10. correct code, wrong rate applied. classic config error.
    for i in _pick(rng, d.index, 0.009):
        taxable = float(d.at[i, "taxable_amount"])
        if taxable == 0:
            continue
        wrong = float(rng.choice([0.10, 0.15, 0.20, 0.05, 0.0725]))
        if abs(wrong - float(d.at[i, "tax_rate"])) < 1e-9:
            continue
        d.at[i, "tax_amount"] = money(taxable * wrong)
        log.add(d.at[i, "transaction_id"], "F012", "SUBTLE", "tax_amount",
                f"rate {wrong} applied instead of {d.at[i, 'tax_rate']}")

    # 11. tax-inclusive treated as tax-exclusive by the source system
    incl = d.index[d["amount_type"] == "GROSS"]
    for i in _pick(rng, incl, 0.05) if len(incl) else []:
        log.add(d.at[i, "transaction_id"], "F013", "SUBTLE", "amount_type",
                "gross amount reported as NET")
        d.at[i, "amount_type"] = "NET"

    # 12. exemption claimed with no certificate on the customer record
    non_ex = d.index[~d["customer_exempt"].astype(bool)]
    for i in _pick(rng, non_ex, 0.005) if len(non_ex) else []:
        log.add(d.at[i, "transaction_id"], "F014", "SUBTLE", "customer_exempt",
                "exemption flag set without a valid certificate")
        d.at[i, "customer_exempt"] = True
        d.at[i, "tax_amount"] = 0.0

    # 13. rounding done with banker's rounding instead of half up
    for i in _pick(rng, d.index, 0.02):
        taxable = float(d.at[i, "taxable_amount"])
        rate = float(d.at[i, "tax_rate"])
        if taxable == 0 or rate == 0:
            continue
        bankers = round(taxable * rate, 2)
        if abs(bankers - float(d.at[i, "tax_amount"])) > 0.0049:
            d.at[i, "tax_amount"] = bankers
            log.add(d.at[i, "transaction_id"], "F015", "SUBTLE", "tax_amount",
                    "banker's rounding instead of half up")

    # 14. floating point residue, e.g. 41.30000000000001
    for i in _pick(rng, d.index, 0.01):
        v = float(d.at[i, "tax_amount"])
        d.at[i, "tax_amount"] = v + float(rng.choice([1e-9, -1e-9, 4e-10]))
        log.add(d.at[i, "transaction_id"], "F016", "SUBTLE", "tax_amount",
                "floating point residue")

    # 15. duplicate invoices, same invoice re-sent minutes apart
    dupes = []
    for i in _pick(rng, d.index, 0.006):
        row = d.loc[i].copy()
        row["transaction_id"] = str(row["transaction_id"]) + "-R"
        row["posting_date"] = row["posting_date"]
        dupes.append(row)
        log.add(str(row["transaction_id"]), "F017", "MEDIUM", "invoice_number",
                "duplicate invoice resent")
    if dupes:
        d = pd.concat([d, pd.DataFrame(dupes)], ignore_index=True)

    # 16. stale customer reference, points at a customer that does not exist
    for i in _pick(rng, d.index, 0.003):
        log.add(d.at[i, "transaction_id"], "F018", "MEDIUM", "customer_id",
                "customer id not in master")
        d.at[i, "customer_id"] = f"CUST9{rng.integers(10000, 99999)}"

    # 17. suspiciously large tax relative to the taxable amount
    for i in _pick(rng, d.index, 0.0015):
        taxable = float(d.at[i, "taxable_amount"])
        if taxable <= 0:
            continue
        d.at[i, "tax_amount"] = money(taxable * float(rng.uniform(0.45, 0.95)))
        log.add(d.at[i, "transaction_id"], "F019", "SUBTLE", "tax_amount",
                "tax to base ratio far above any real rate")

    # 18. whitespace on ids, the classic silent join killer
    for i in _pick(rng, d.index, 0.03):
        cid = d.at[i, "customer_id"]
        if isinstance(cid, str):
            d.at[i, "customer_id"] = f" {cid} "
            log.add(d.at[i, "transaction_id"], "F020", "SUBTLE", "customer_id",
                    "leading and trailing whitespace on join key")

    return d.reset_index(drop=True), log
