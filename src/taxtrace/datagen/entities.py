"""Customers and vendors for Meridian Commerce Group.

Entities are generated CLEAN here. Corruption happens later, in corrupt.py,
so that the answer key always knows what the truth was.

PRODUCTION ALERT
    Customer master data is where most tax determination bugs actually start.
    A customer with a stale address, a missing country, or an expired
    exemption certificate will silently produce the wrong rate on every line
    they appear on. That is why the exemption certificate here carries valid
    from and valid to dates rather than a simple yes/no flag.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .reference import JURISDICTIONS

CUSTOMER_TYPES = ["B2C", "B2B", "B2B_RESALE", "GOV"]

AU_STATES = ["VIC", "NSW", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
NZ_REGIONS = ["AUK", "WGN", "CAN", "OTA", "WKO"]
GB_REGIONS = ["ENG", "SCT", "WLS", "NIR"]

FIRST = ["Amara", "Ben", "Chen", "Divya", "Elena", "Farouk", "Grace", "Hiro",
         "Isla", "Jonas", "Kiri", "Liam", "Mei", "Noor", "Oliver", "Priya",
         "Quinn", "Rahul", "Sofia", "Tane", "Uma", "Victor", "Wren", "Xu",
         "Yara", "Zane"]
LAST = ["Adeyemi", "Baker", "Chen", "Dubois", "Edwards", "Fitzgerald", "Gupta",
        "Hoffman", "Ibrahim", "Jensen", "Kowalski", "Lombardi", "Marsh",
        "Nguyen", "OConnor", "Patel", "Quintero", "Rossi", "Silva", "Tanaka",
        "Ueda", "Vargas", "Whitfield", "Xavier", "Yildiz", "Zhang"]
ORG_SUFFIX = ["Pty Ltd", "Limited", "Holdings", "Group", "Trading Co",
              "Enterprises", "Partners", "Industries"]
STREETS = ["High", "Collins", "Queen", "King", "Bourke", "Elizabeth", "Market",
           "Station", "Church", "Victoria", "Albert", "George"]


def _postcode(rng: np.random.Generator, country: str) -> str:
    if country == "AU":
        return f"{rng.integers(2000, 7999):04d}"
    if country == "NZ":
        return f"{rng.integers(1000, 9999):04d}"
    if country == "GB":
        letters = "ABCDEFGHIJKLMNOPRSTUWYZ"
        return (f"{letters[rng.integers(0, len(letters))]}"
                f"{letters[rng.integers(0, len(letters))]}"
                f"{rng.integers(1, 99)} "
                f"{rng.integers(1, 9)}"
                f"{letters[rng.integers(0, len(letters))]}"
                f"{letters[rng.integers(0, len(letters))]}")
    return f"{rng.integers(10000, 99999):05d}"


def _region(rng: np.random.Generator, country: str) -> str:
    if country == "AU":
        return str(rng.choice(AU_STATES))
    if country == "NZ":
        return str(rng.choice(NZ_REGIONS))
    if country == "GB":
        return str(rng.choice(GB_REGIONS))
    return ""


def build_customers(rng: np.random.Generator, n: int = 4000) -> pd.DataFrame:
    """Customer master with addresses, types and exemption certificates."""
    jur = [j for j in JURISDICTIONS]
    rows = []
    for i in range(1, n + 1):
        country_code, jurisdiction_code, name, regime, rate = jur[
            rng.integers(0, len(jur))
        ]
        ctype = str(rng.choice(CUSTOMER_TYPES, p=[0.55, 0.30, 0.10, 0.05]))
        is_org = ctype != "B2C"
        if is_org:
            cust_name = f"{rng.choice(LAST)} {rng.choice(ORG_SUFFIX)}"
        else:
            cust_name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"

        # Exemption certificates only exist for resale and government buyers,
        # and only some of those actually hold a current one.
        has_cert = ctype in ("B2B_RESALE", "GOV") and bool(rng.random() < 0.72)
        if has_cert:
            start = date(2021, 1, 1) + timedelta(days=int(rng.integers(0, 900)))
            # ~18 per cent of certificates have already expired. This is the
            # single most useful trap in the whole dataset.
            if rng.random() < 0.18:
                end = start + timedelta(days=int(rng.integers(180, 700)))
            else:
                end = date(2027, 12, 31)
            cert_id = f"EX{i:06d}"
        else:
            start = end = None
            cert_id = None

        rows.append({
            "customer_id": f"CUST{i:06d}",
            "customer_name": cust_name,
            "customer_type": ctype,
            "country_code": country_code,
            "jurisdiction_code": jurisdiction_code,
            "region": _region(rng, country_code),
            "city": str(rng.choice(["Melbourne", "Sydney", "Auckland", "London",
                                    "Manchester", "Los Angeles", "New York",
                                    "Austin", "Seattle", "Chicago", "Miami",
                                    "Portland", "Wilmington", "Wellington"])),
            "address_line1": f"{rng.integers(1, 499)} {rng.choice(STREETS)} Street",
            "postcode": _postcode(rng, country_code),
            "exemption_certificate_id": cert_id,
            "exemption_valid_from": start,
            "exemption_valid_to": end,
            "created_date": date(2020, 1, 1) + timedelta(days=int(rng.integers(0, 1500))),
            "is_active": bool(rng.random() > 0.06),
        })
    return pd.DataFrame(rows)


def build_vendors(rng: np.random.Generator, n: int = 800) -> pd.DataFrame:
    jur = [j for j in JURISDICTIONS]
    rows = []
    for i in range(1, n + 1):
        country_code, jurisdiction_code, name, regime, rate = jur[
            rng.integers(0, len(jur))
        ]
        rows.append({
            "vendor_id": f"VEND{i:05d}",
            "vendor_name": f"{rng.choice(LAST)} {rng.choice(ORG_SUFFIX)}",
            "country_code": country_code,
            "jurisdiction_code": jurisdiction_code,
            "tax_registration_number": f"{country_code}{rng.integers(10**8, 10**9)}",
            "is_registered_for_tax": bool(rng.random() > 0.12),
            "created_date": date(2020, 1, 1) + timedelta(days=int(rng.integers(0, 1500))),
        })
    return pd.DataFrame(rows)
