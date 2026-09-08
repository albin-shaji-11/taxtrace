# Deloitte Analyst, Tax Data Automation — skill matrix

Requisition 41834, Melbourne. Derived from the advertised responsibilities and
requirements, then ranked by how much of the interview is likely to sit on each.

## The job in one sentence

Take a client's messy ERP finance data, turn the tax team's rules into
configuration a machine can execute, and prove the answer is right, repeatably,
with a trail an auditor can follow.

## Full requirement mapping

| # | Job requirement | Category | Weight | Where the project covers it |
|---|---|---|---|---|
| 1 | Python for ETL/ELT processing | Core | High | Days 1, 2, 4 |
| 2 | SQL over relational data | Core | High | Day 2, DuckDB model |
| 3 | Translate tax requirements into executable rules | Core | High | Day 3 rules engine |
| 4 | Tax calculation, classification, validation rules | Core | High | Day 3 |
| 5 | Automated data quality controls | Core | High | Day 4 DQ framework |
| 6 | Reconciliation systems | Core | High | Day 4 |
| 7 | Data validation | Core | High | Days 1, 4 |
| 8 | Diagnose production issues in tax modules | Core | High | Day 5 incident |
| 9 | Automated testing, regression | Core | High | Day 5 pytest suite |
| 10 | Git, code review, CI/CD | Core | Medium | Day 6 |
| 11 | Data workflows, schemas and mappings | Core | High | Day 2 canonical model |
| 12 | ERP and finance data | Domain | High | 4 source extracts |
| 13 | Requirements workshops with Tax SMEs | Soft | High | Day 3 + Day 7 simulation |
| 14 | Document technical decisions and rules | Soft | Medium | Throughout, docs/ |
| 15 | Pandas, Polars, DuckDB | Tools | Medium | Day 2 benchmark |
| 16 | Rules engines, decision tables | Concept | High | Day 3 |
| 17 | Configuration driven processing | Concept | High | Day 3 YAML |
| 18 | Reference / golden datasets | Concept | Medium | Day 4 |
| 19 | Output comparison, regression testing | Concept | Medium | Day 5 |
| 20 | Anomaly detection | Concept | Medium | Day 4 |
| 21 | AI assisted engineering, LLM evaluation | Emerging | Medium | Day 6 eval harness |
| 22 | Agentic workflows | Emerging | Low | Day 6, conceptual |
| 23 | Azure, Docker, Kubernetes, Airflow | Cloud | Low | Day 6, conceptual only |
| 24 | Statistical anomaly detection | Advantageous | Low | Day 4 |

## The 13 skills to actually master this week

Ranked. If you run out of time, cut from the bottom.

1. **Rules as configuration, not code.** The single most distinguishing idea in
   this job. A Tax SME must be able to change a rate without a developer.
2. **Reconciliation and variance classification.** Source tax versus calculated
   tax, and being able to say *why* they differ.
3. **SQL for investigation.** CTEs, window functions, duplicate detection,
   conditional aggregation. This is what a live technical screen will test.
4. **Data quality controls with severity and thresholds.** Named, versioned,
   measurable checks. Not ad hoc asserts.
5. **Effective dating and rule precedence.** Which rate applied *on that date*.
6. **Canonical schema and source mapping.** Four ERPs, one model.
7. **Rounding, tax-inclusive versus exclusive, currency.** The arithmetic that
   quietly generates thousands of one cent variances.
8. **Pytest and regression testing of business logic.** Change a rule, prove
   nothing else moved.
9. **Production incident diagnosis.** Symptom to root cause to fix to
   verification to written incident report.
10. **Traceability.** Every calculated number carries the rule id and version
    that produced it. This is the audit requirement and your differentiator.
11. **Pandas versus Polars versus DuckDB.** When and why, with a measured
    benchmark rather than an opinion.
12. **Git discipline.** Branches, meaningful commits, a PR you would approve.
13. **AI evaluation harness.** Natural language rule to structured proposal to
    deterministic validation to human approval.

## Where your existing background already maps

You are not starting from zero on the domain half, which is the half most
candidates for this role are weakest on.

| Your experience | Job requirement it maps to |
|---|---|
| Stripe tax operations, multi state US filings | ERP and finance data, tax compliance context |
| Correcting tax refunds and tax data | Reconciliation, exception handling |
| Addresses affecting tax calculation | Jurisdiction determination, the hardest part of sales tax |
| Escalation team for complex cases | Production incident triage |
| US stakeholders | Requirements gathering with SMEs |
| Excel macro, 20 per cent time saved | Automation, process improvement |
| Master of Data Science | Python, SQL, statistics, anomaly detection |

The gap is not tax knowledge and it is not analysis. The gap is **engineering
practice**: configuration driven design, automated tests, version control
discipline, and being able to prove correctness rather than assert it. That is
what the next seven days are for.
