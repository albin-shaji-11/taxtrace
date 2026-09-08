"""Orchestrates data generation and writes the four source extracts.

Each ERP sends the same concepts under different column names. Mapping those
onto one canonical schema is Day 2 work, and it is a large part of what a Tax
Data Automation analyst actually does.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import reference
from .corrupt import corrupt
from .entities import build_customers, build_vendors
from .truth import build_ground_truth

# Canonical field -> per source column name. Deliberately inconsistent.
SOURCE_SCHEMAS: dict[str, dict[str, str]] = {
    "SAP_AU": {
        "transaction_id": "BELNR", "invoice_number": "XBLNR",
        "transaction_date": "BUDAT", "posting_date": "CPUDT",
        "customer_id": "KUNNR", "vendor_id": "LIFNR",
        "country_code": "LAND1", "jurisdiction_code": "TXJCD",
        "region": "REGIO", "postcode": "PSTLZ",
        "product_category": "MATKL", "currency_code": "WAERS",
        "amount_type": "AMT_TYPE", "gross_amount": "WRBTR",
        "taxable_amount": "NETWR", "tax_code": "MWSKZ",
        "tax_rate": "KBETR", "tax_amount": "WMWST",
        "gl_account": "HKONT", "customer_exempt": "EXEMPT_FLG",
        "is_credit_note": "SHKZG",
    },
    "DYNAMICS_UK": {
        "transaction_id": "DocumentNo", "invoice_number": "InvoiceNo",
        "transaction_date": "DocumentDate", "posting_date": "PostingDate",
        "customer_id": "CustomerNo", "vendor_id": "VendorNo",
        "country_code": "CountryRegionCode", "jurisdiction_code": "TaxJurisdiction",
        "region": "County", "postcode": "PostCode",
        "product_category": "ItemCategoryCode", "currency_code": "CurrencyCode",
        "amount_type": "AmountBasis", "gross_amount": "AmountIncludingVAT",
        "taxable_amount": "VATBaseAmount", "tax_code": "VATProdPostingGroup",
        "tax_rate": "VATPct", "tax_amount": "VATAmount",
        "gl_account": "GLAccountNo", "customer_exempt": "VATExempt",
        "is_credit_note": "CreditMemo",
    },
    "ORACLE_US": {
        "transaction_id": "TRX_NUMBER", "invoice_number": "INVOICE_ID",
        "transaction_date": "TRX_DATE", "posting_date": "GL_DATE",
        "customer_id": "BILL_TO_CUSTOMER_ID", "vendor_id": "SUPPLIER_ID",
        "country_code": "COUNTRY", "jurisdiction_code": "TAX_JURISDICTION_CODE",
        "region": "STATE", "postcode": "POSTAL_CODE",
        "product_category": "PRODUCT_FISCAL_CLASS", "currency_code": "CURRENCY_CODE",
        "amount_type": "AMOUNT_INCLUDES_TAX_FLAG", "gross_amount": "TRX_AMOUNT",
        "taxable_amount": "TAXABLE_AMOUNT", "tax_code": "TAX_RATE_CODE",
        "tax_rate": "TAX_RATE", "tax_amount": "TAX_AMT",
        "gl_account": "CODE_COMBINATION_ID", "customer_exempt": "EXEMPT_FLAG",
        "is_credit_note": "CM_FLAG",
    },
    "NETSUITE_NZ": {
        "transaction_id": "tranid", "invoice_number": "custbody_invoice_ref",
        "transaction_date": "trandate", "posting_date": "postingperiod",
        "customer_id": "entity", "vendor_id": "custbody_vendor",
        "country_code": "shipcountry", "jurisdiction_code": "taxjurisdiction",
        "region": "shipstate", "postcode": "shipzip",
        "product_category": "custcol_item_category", "currency_code": "currency",
        "amount_type": "custbody_amount_basis", "gross_amount": "total",
        "taxable_amount": "netamount", "tax_code": "taxcode",
        "tax_rate": "taxrate", "tax_amount": "taxtotal",
        "gl_account": "account", "customer_exempt": "custbody_tax_exempt",
        "is_credit_note": "custbody_credit_memo",
    },
}

# Some systems express booleans and rates differently. More realism, more work.
BOOL_STYLE = {
    "SAP_AU": {True: "X", False: ""},
    "DYNAMICS_UK": {True: "Yes", False: "No"},
    "ORACLE_US": {True: "Y", False: "N"},
    "NETSUITE_NZ": {True: "T", False: "F"},
}
RATE_AS_PERCENT = {"DYNAMICS_UK", "ORACLE_US"}  # 20 rather than 0.20


def _rename_for_source(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = df.copy()
    style = BOOL_STYLE[source]
    for col in ("customer_exempt", "is_credit_note"):
        out[col] = out[col].map(lambda v: style[bool(v)])
    if source in RATE_AS_PERCENT:
        out["tax_rate"] = (out["tax_rate"].astype(float) * 100).round(3)
    if source == "ORACLE_US":
        out["amount_type"] = out["amount_type"].map({"GROSS": "Y", "NET": "N"})
    mapping = SOURCE_SCHEMAS[source]
    out = out[list(mapping)].rename(columns=mapping)
    return out


def generate(out_dir: Path, n_rows: int = 50_000, seed: int = 20260908,
             n_customers: int = 4000, n_vendors: int = 800) -> dict:
    rng = np.random.default_rng(seed)

    raw = out_dir / "raw"
    ref = out_dir / "reference"
    gold = out_dir / "golden"
    key = out_dir / "_answer_key"
    for p in (raw, ref, gold, key):
        p.mkdir(parents=True, exist_ok=True)

    customers = build_customers(rng, n_customers)
    vendors = build_vendors(rng, n_vendors)
    truth = build_ground_truth(rng, customers, vendors, n_rows)

    dirty, log = corrupt(truth, rng)

    # ---- reference data, lightly untidy but structurally sound
    reference.jurisdictions_df().to_csv(ref / "jurisdictions.csv", index=False)
    reference.categories_df().to_csv(ref / "product_categories.csv", index=False)
    reference.tax_codes_df().to_csv(ref / "tax_codes.csv", index=False)
    reference.tax_rates_df().to_csv(ref / "tax_rates.csv", index=False)

    # ---- master data, with a little real world mess
    cust_out = customers.copy()
    for i in rng.choice(cust_out.index, size=int(len(cust_out) * 0.04), replace=False):
        cust_out.at[i, "postcode"] = ""
    for i in rng.choice(cust_out.index, size=int(len(cust_out) * 0.03), replace=False):
        cust_out.at[i, "customer_name"] = f"  {cust_out.at[i, 'customer_name'].upper()}  "
    cust_out.to_csv(raw / "customers.csv", index=False)
    vendors.to_csv(raw / "vendors.csv", index=False)

    # ---- four ERP extracts
    counts = {}
    for source in SOURCE_SCHEMAS:
        part = dirty[dirty["source_system"] == source]
        renamed = _rename_for_source(part, source)
        fname = f"erp_{source.lower()}_transactions.csv"
        renamed.to_csv(raw / fname, index=False)
        counts[fname] = len(renamed)

    # ---- golden dataset, a hand-verifiable slice with expected outputs
    golden = truth.sample(n=250, random_state=7).copy()
    golden = golden[["transaction_id", "jurisdiction_code", "product_category",
                     "customer_exempt", "transaction_date", "amount_type",
                     "taxable_amount", "tax_code", "tax_rate", "tax_amount"]]
    golden = golden.rename(columns={
        "tax_code": "expected_tax_code",
        "tax_rate": "expected_tax_rate",
        "taxable_amount": "expected_taxable_amount",
        "tax_amount": "expected_tax_amount",
    })
    golden.to_csv(gold / "golden_dataset.csv", index=False)

    # ---- answer key. Do not open this until an exercise tells you to.
    truth.to_csv(key / "ground_truth_transactions.csv", index=False)
    log.to_frame().to_csv(key / "fault_log.csv", index=False)

    summary = {
        "seed": seed,
        "generated_on": date.today().isoformat(),
        "clean_rows": int(len(truth)),
        "delivered_rows": int(len(dirty)),
        "customers": int(len(customers)),
        "vendors": int(len(vendors)),
        "faults_injected": int(len(log.rows)),
        "faults_by_tier": log.to_frame()["tier"].value_counts().to_dict()
        if log.rows else {},
        "faults_by_code": log.to_frame()["fault_code"].value_counts().to_dict()
        if log.rows else {},
        "rows_per_source_file": counts,
        "golden_rows": int(len(golden)),
    }
    (key / "generation_summary.json").write_text(json.dumps(summary, indent=2))
    return summary
