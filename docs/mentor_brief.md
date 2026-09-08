# Mentor brief — TaxTrace

The full engagement brief, saved so a new Claude session picks up exactly where
the last one stopped. `CLAUDE.md` is the short version and is loaded
automatically; this is the detail behind it.

---

## Role Claude plays

Technical mentor, project architect, data engineer, Python and SQL interviewer,
and coding coach. One week to prepare Albin for **Deloitte, Analyst, Tax Data
Automation (Python & SQL)**, Melbourne, requisition 41834.

## Job description themes to cover

Python and SQL for ELT and rules-based processing; tax calculation,
classification and validation rules; relational data; ETL/ELT; data quality;
data reconciliation; reference and golden datasets; output comparisons;
regression testing; anomaly detection; production issue troubleshooting;
requirements gathering with Tax SMEs; rules engines and decision tables;
configuration-driven processing; data schemas and mappings; ERP and finance
data; Pandas, Polars, DuckDB; Git, code reviews, automated testing, CI/CD;
technical documentation; AI-assisted engineering, LLM evaluation, agentic
workflows; conceptual exposure to Azure, Docker, Kubernetes, Airflow.

## The 24 things the platform must do

Ingest messy source data, profile it, identify quality problems, clean and
standardise, map source fields to a canonical schema, apply configurable tax
rules, calculate expected tax, classify transactions, identify exceptions,
reconcile calculated against source tax, detect anomalies, compare against a
golden dataset, run automated tests, generate an exception report, generate a
reconciliation report, simulate a production incident, diagnose it, fix the
underlying rule or data issue, rerun regression tests, produce auditable
output, document the rules and decisions, expose results through SQL, provide a
small dashboard, and include an AI-assisted evaluation harness.

---

## Work packages

Numbered as in the original brief so nothing is skipped.

| # | Package | Day | State |
|---|---|---|---|
| 1 | Business scenario and requirements document | Pre | Done |
| 2 | Messy mock data, 20k+ rows, deliberate faults | Pre | Done, 50,300 rows |
| 3 | Data profiling framework and report | 1 | **In progress** |
| 4 | Data cleaning pipeline, proper modules | 1-2 | Not started |
| 5 | SQL, relational model, 20+ interview questions | 2 | Not started |
| 6 | Tax rule engine, YAML decision tables | 3 | Not started |
| 7 | Tax calculation, spec written before code | 3 | Not started |
| 8 | Golden dataset and comparison | 4 | Data ready, logic not started |
| 9 | Reconciliation framework and variance classes | 4 | Not started |
| 10 | Data quality controls DQ001 to DQ012 | 4 | Not started |
| 11 | Anomaly detection, deterministic and statistical | 4 | Not started |
| 12 | Production incident simulation | 5 | Not started |
| 13 | Regression testing suite | 5 | Not started |
| 14 | Property-based and edge testing | 5 | Not started |
| 15 | Pandas vs Polars vs DuckDB, measured benchmark | 2 | Not started |
| 16 | ETL/ELT architecture and cloud mapping | Pre | Done |
| 17 | Git, repo structure, branch workflow | 6 | Repo done, workflow not taught |
| 18 | CI/CD with GitHub Actions | 6 | Not started |
| 19 | Logging and observability | 6 | Not started |
| 20 | Documentation set and data dictionary | 6 | Partly done |
| 21 | AI / LLM evaluation harness | 6 | Not started |
| 22 | Optional Streamlit app | 6 | Optional, low priority |
| 23 | Interview question bank, 185+ questions | 7 | Not started |
| 24 | Mock interview, graded 1 to 5 | 7 | Not started |
| 25 | Requirements workshop simulation, Claude as Tax SME | 3 and 7 | Not started |
| 26 | SQL investigation simulations, at least 5 | 7 | Not started |
| 27 | Python debugging simulations | 7 | Not started |
| 28 | Code review simulations | 7 | Not started |
| 29 | Seven day study plan | Pre | Done |
| 30 | Resume-ready project description | 7 | Not started |
| 31 | GitHub and LinkedIn presentation | 7 | Not started |
| 32 | Final knowledge matrix | 7 | Not started |

### Question bank targets for package 23

Python 30, SQL 30, data engineering 25, tax data automation 25, rules engines
15, data quality 15, production incident scenarios 15, behavioural 20.
Difficulty should increase through each set.

### Mock interview format for package 24

One question at a time. Wait for the answer. Grade 1 to 5 on technical
correctness, business reasoning, communication, depth and practicality. Then
give: what he did well, what he missed, the ideal answer, how a strong Deloitte
candidate would answer, and a follow-up question.

### Requirements workshop format for package 25

Claude plays a Tax SME and gives a deliberately vague requirement, for example
"we need to make sure tax is calculated correctly for interstate transactions".
Albin must ask clarifying questions. Claude answers in character. The lesson is
identifying missing assumptions, exceptions, precedence, expected outcomes,
source data, edge cases and acceptance criteria.

---

## Data design, already built

Ground truth is generated **first**, then the source data is deliberately
corrupted, so every exception the pipeline raises can be checked against a
known answer and precision and recall can be measured rather than guessed.

- 50,000 clean rows, 50,300 delivered after duplicate injection
- 12,468 faults across 20 types, logged by transaction id
- Three tiers: LOUD 6,025 findable by profiling, MEDIUM 2,792 findable by joins
  and business rules, SUBTLE 3,651 findable only by reconciliation or statistics
- Four ERP extracts with genuinely different field names, boolean conventions
  and rate formats: SAP AU, Dynamics UK, Oracle US, NetSuite NZ
- Effective-dated rate history, including a real UK reduced-rate change in 2022
- 250-row golden dataset
- Answer key at `data/_answer_key/`, **not to be revealed early**

---

## Reminders that are easy to lose between sessions

1. Do not dump code. He must attempt first.
2. Do not run ahead of the study plan.
3. Do not reveal the answer key before the Day 1 checkpoint is met.
4. Do not give away the production incident cause on Day 5. Give symptoms only,
   let him investigate, then review his reasoning.
5. Label things INTERVIEW ALERT, PRODUCTION ALERT and DELOITTE RELEVANCE.
6. Free and local only. No paid services, no cloud account.
7. Never claim Azure, Docker, Kubernetes or Airflow on the resume. Not used.
8. Run the tests before saying anything is complete.
9. Do not fabricate benchmark or business results. Measure or omit.
