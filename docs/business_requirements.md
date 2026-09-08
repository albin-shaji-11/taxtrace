# Business Requirements — TaxTrace

**Client:** Meridian Commerce Group
**Engagement:** Tax Data Automation, indirect tax validation and reconciliation
**Prepared by:** Tax Transformation and Technology
**Status:** Baseline, v1.0

---

## 1. Client background

Meridian Commerce Group is a mid-market retail and e-commerce group operating
across Australia, New Zealand, the United Kingdom and eight United States
states. Annual revenue is approximately AUD 480 million.

Growth by acquisition has left Meridian with four finance systems that were
never consolidated.

| Source system | Region | Approx. share of transactions |
|---|---|---|
| SAP ECC | Australia | 36% |
| Microsoft Dynamics 365 | United Kingdom | 28% |
| Oracle Fusion | United States | 24% |
| NetSuite | New Zealand | 12% |

Each system holds the same concepts under different field names, different
boolean conventions, and different date formats. Tax rates are configured
independently in each, by different people, at different times.

## 2. The problem

Indirect tax returns are prepared monthly in Excel. A senior analyst downloads
extracts from each ERP, joins them by hand, eyeballs the totals against last
month, and files. The process takes nine working days.

Three incidents in the last eighteen months have driven this engagement.

* A UK VAT rate change was applied in Dynamics two weeks late. 4,100
  transactions were filed at the wrong rate. The error was found by the
  external auditor, not by Meridian.
* An expired US resale exemption certificate continued to be honoured for
  seven months, understating collected sales tax.
* A duplicate invoice feed from NetSuite double counted NZD 210,000 of output
  tax. It was found only because a customer queried their statement.

None of these were found by a control. All three were found by an outsider.

## 3. Business objective

> Automatically determine, validate and reconcile indirect tax on every
> transaction before filing, so that errors are found by Meridian's own
> controls rather than by an auditor or a customer, and so that every
> calculated figure can be traced back to the source record and the rule that
> produced it.

## 4. Users

| User | What they need |
|---|---|
| Indirect Tax Manager | Confidence the filing is right, and evidence for why |
| Tax Analyst | To change a rate or a treatment without a developer |
| Finance Operations | A clear, categorised exception list to work through |
| Data Engineering | Reproducible, testable, version controlled transformations |
| Internal Audit | A traceable line from filed figure back to source row and rule |
| External Auditor | Documented rules, documented controls, evidence of testing |

## 5. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Ingest transaction extracts from all four source systems | Must |
| FR-02 | Map each source schema onto a single canonical transaction model | Must |
| FR-03 | Profile incoming data and report quality before processing | Must |
| FR-04 | Standardise country, currency, region, category and date values | Must |
| FR-05 | Determine the applicable tax code from jurisdiction, product category, customer status and transaction date | Must |
| FR-06 | Apply the rate effective **on the transaction date**, not today's rate | Must |
| FR-07 | Support tax-inclusive and tax-exclusive source amounts | Must |
| FR-08 | Honour customer exemption certificates only within their validity dates | Must |
| FR-09 | Allow a Tax Analyst to add or change a rule in configuration, with no code change | Must |
| FR-10 | Record rule id and rule version against every calculated result | Must |
| FR-11 | Reconcile calculated tax against source tax and classify each variance | Must |
| FR-12 | Run a named, versioned set of data quality checks with severities | Must |
| FR-13 | Produce an exception report categorised by cause and owner | Must |
| FR-14 | Compare output against a golden dataset and report pass, fail or warning | Must |
| FR-15 | Detect statistical anomalies in tax rate, tax amount and volume | Should |
| FR-16 | Detect duplicate transactions and duplicate invoices | Must |
| FR-17 | Expose results through SQL for ad hoc investigation | Must |
| FR-18 | Log every run with row counts, rules applied, and elapsed time | Must |
| FR-19 | Provide a dashboard summarising the current filing position | Could |
| FR-20 | Evaluate AI generated rule proposals before a human approves them | Could |

## 6. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Full pipeline run on a month of data | Under 5 minutes on a laptop |
| NFR-02 | Deterministic. Same input and config produce identical output | Exact |
| NFR-03 | Idempotent. Re-running does not duplicate or corrupt results | Exact |
| NFR-04 | Automated test coverage of tax calculation and rule resolution | 90%+ |
| NFR-05 | Every rule change is version controlled and reviewable | 100% |
| NFR-06 | No personally identifying data in logs | 100% |
| NFR-07 | Runs locally with free and open source tooling only | Required |

## 7. Assumptions

1. Source extracts are delivered daily as CSV. Real time is out of scope.
2. Jurisdiction is determined by the customer's billing address. Meridian
   accepts this simplification for the pilot.
3. United States sales tax is modelled at state level only. County and city
   precision is out of scope for the pilot and is a known limitation.
4. Currency conversion uses a monthly average rate, supplied by Finance.
5. Meridian's Tax team owns the rule configuration. Engineering owns the engine.
6. Historical filings will not be restated as part of this engagement.

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Rule configuration becomes as complex as code | High | Decision table format, mandatory review, versioning |
| Tax SME and engineer interpret a rule differently | High | Golden dataset agreed and signed off before build |
| Source system changes a field without notice | Medium | Schema validation on ingest, fail loudly |
| Exception list too large to action | Medium | Severity and materiality thresholds, ranked by value |
| Over-reliance on AI generated rules | High | Deterministic validation and mandatory human approval |
| State level US modelling misses local rates | Medium | Documented limitation, flagged on every US output |

## 9. Acceptance criteria

The pilot is accepted when all of the following hold on one full month.

1. Every transaction in the source extracts appears exactly once in the
   canonical model, or on the rejection report with a reason.
2. 100% of golden dataset transactions produce the expected tax code, rate and
   tax amount.
3. Reconciliation classifies 100% of variances into a named category. No
   variance is left as UNKNOWN.
4. All twelve mandatory data quality checks execute and report.
5. Every calculated row carries a rule id, rule version and timestamp.
6. A Tax Analyst can change a rate in configuration and see the effect, with no
   Python change, and the regression suite proves nothing else moved.
7. The pipeline reruns end to end and produces byte-identical output.
8. An auditor can select any filed figure and trace it to the source row and
   the rule that produced it, in under two minutes.

---

## Open questions for the Tax SME

Deliberately unanswered. You will resolve these in the Day 3 and Day 7
requirements workshop simulations.

1. When a customer's exemption certificate expires mid-month, is the whole
   month taxable or only transactions after the expiry date?
2. For a UK sale shipped to Northern Ireland, which rules apply?
3. If a credit note reverses a transaction taxed at an old rate, does the
   credit use the original rate or the current one?
4. What is the materiality threshold below which a variance is not worth
   investigating?
5. Freight is currently treated as its own category. Should it follow the tax
   treatment of the goods it delivers?
