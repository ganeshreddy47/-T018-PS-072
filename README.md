# PS-072: Online Exam Proctoring Result Engine

**Domain:** Education – Online Assessment  
**Language:** Python 3.10+ (Developed and tested on Python 3.14)  
**Team ID:** T018  
**Section:** CSDS A  
**Repository:** [https://github.com/ganeshreddy47/-T018-PS-072](https://github.com/ganeshreddy47/-T018-PS-072)

---

## 👥 Team Information
* **Member 1:** K GANESH REDDY – 1AT24CD036 (`ganeshreddy9995239@gmail.com`)
* **Member 2:** KATTE SHREYAS – 1AT24CD037 (`shreyaskatte19@gmail.com`)

---

## 🎯 Project Overview
This project delivers a robust, production-grade back-end result engine used by a national-level recruitment exam to:
1. Ingest multi-shift exam structures, sectional constraints, candidate profiles, response recordings, answer keys, proctoring flags, and challenges.
2. Score responses with negative marking (`THIRD` and `QUARTER` schemes) and multiple-correct question validation.
3. Process post-exam challenges (dropped questions and key changes) with dynamic supersession and re-scoring.
4. Enforce strict sectional time window constraints and skipped-section detection.
5. Apply cumulative proctoring penalties and automatic disqualification for malpractice.
6. Enforce category-relaxed sectional and overall cut-offs (`GEN`, `OBC`, `SC`, `ST`, `EWS`, and `PwD`).
7. Normalise scores across shifts using the national recruitment normalisation formula with pooling for low-volume shifts (< 100 candidates) and guard against zero/negative denominators.
8. Produce a merit list with a 5-level deterministic tie-breaking hierarchy.
9. Implement constitutional reservation migration (reserved candidates scoring at or above the `GEN` cut-off are counted against `GEN` vacancies).
10. Support single-candidate re-evaluation with automated version increments only upon score changes.

---

## 🏗️ Architecture & Project Structure

```text
T018-PS-072/
├── src/
│   ├── __init__.py           # Package marker
│   ├── models.py             # Typed dataclasses for Exam, Section, Candidate, etc.
│   ├── scoring.py            # Response evaluation, negative marking, penalties, cut-offs
│   ├── normalisation.py      # Pooling, top fraction ceil, formula, denominator guard
│   ├── merit.py              # 5-level tie-breaking, reservation migration, cut-off computation
│   └── engine.py             # Command file processor (SCORE_ALL, NORMALISE, REEVALUATE, etc.)
├── tests/
│   ├── __init__.py           # Test package marker
│   ├── test_scoring.py       # Unit tests for scoring, penalties, and cut-offs
│   ├── test_normalisation.py # Unit tests for pooling, top fraction, and guards
│   ├── test_edge_cases.py    # Explicit tests for EC-01 through EC-08 and extra traps
│   └── test_end_to_end.py    # End-to-end pipeline verification test
├── sample_data/              # Sample exam CSV files and commands.txt
├── output/                   # Generated evaluation CSV outputs
│   ├── scorecards.csv        # Per-candidate score cards
│   ├── shift_stats.csv       # Shift / pooled group statistics
│   ├── merit_list.csv        # Final merit list with tie-breaking and reservation migration
│   └── category_cutoffs.csv  # Category-wise cut-off marks and list sizes
├── main.py                   # CLI entry point to run command file and generate outputs
├── DESIGN_DOCUMENT.md        # Comprehensive technical and mathematical design document
├── DECISION_LOG.md           # Architecture Decision Records (ADRs)
└── push_to_github.bat        # Helper script to commit and push to remote repository
```

---

## 📜 Business Rules Register (BR-01 to BR-13)

| Rule ID | Name | Description |
|---|---|---|
| **BR-01** | Scoring Scheme & Negative Marking | Correct answer earns section marks (1 or 2). Wrong answer deducts 1/3 (if `THIRD`) or 1/4 (if `QUARTER`) of question marks. `NOT_ATTEMPTED` earns 0. `MARKED_FOR_REVIEW` with an option is scored as attempted. Multi-correct questions earn full marks only for exact set; 0 otherwise with no negative deduction and no wrong increment. |
| **BR-02** | Dropped Questions & Key Changes | Dropped questions after challenge award full marks (+marks) only if attempted (any option), 0 if unattempted. Section maximum marks remain unchanged. Key changes re-score all candidates of that paper; earlier results superseded. |
| **BR-03** | Sectional Time & Skipped Sections | Responses with `recorded_at_sec > window_end_min * 60` are treated as `NOT_ATTEMPTED`. Sections with 0 attempted questions are flagged `SECTION_SKIPPED` and automatically fail their sectional cut-off. |
| **BR-04** | Sectional Cut-offs & Relaxations | Raw section score must be `>= cut-off marks`. Cut-off % relaxed by 5 percentage points for `OBC` / `EWS`, 10 points for `SC` / `ST`. `PwD` candidates receive an additional 5 percentage points. Failing any section results in `NOT_QUALIFIED_SECTIONAL`. |
| **BR-05** | Overall Cut-off | Raw overall score after penalties must be `>= overall cut-off marks` (relaxed identically by category and PwD). Passing all sections but failing overall yields `NOT_QUALIFIED_OVERALL`. |
| **BR-06** | Minimum Attempts | Candidates attempting fewer than 10% of total questions (e.g. < 10 of 100) are flagged `NOT_QUALIFIED_MIN_ATTEMPT` regardless of score. |
| **BR-07** | Proctoring Penalties & Disqualification | Proctoring flags have severity 1–3. Cumulative severity 4–6 deducts 5% of raw overall score; 7–9 deducts 15%. Cumulative severity >= 10 or any `CONFIRMED_MALPRACTICE` results in `DISQUALIFIED` with score 0. Penalties are applied before normalisation. Normalisation is NEVER applied to disqualified candidates. |
| **BR-08** | Shift Pooling | If a shift has fewer than 100 candidates (`pooling_min_candidates`), it is pooled with the next shift of the same day into a unified normalisation group. |
| **BR-09** | Top 0.1% Candidate Fraction | Candidate count for top fraction mean: `count = max(1, math.ceil(n * 0.001))`. Disqualified candidates are excluded from normalisation pools. |
| **BR-10** | Shift Normalisation & Guard | Formula: `Normalised = ((M_gt - M_g) / (M_st - M_s)) * (raw - M_s) + M_g`. If denominator `(M_st - M_s) <= 0`, normalised score = raw score and shift is flagged `NO_NORMALISATION`. Results rounded to 5 decimals for display. |
| **BR-11** | Merit List & 5-Level Tie-Breaking | Qualified candidates ordered by: 1) Normalised score DESC, 2) Section 2 (`TIE_BREAKER_1`) raw score DESC, 3) Fewer wrong answers overall (`wrong` ASC), 4) Older Date of Birth (`date_of_birth` ASC), 5) Candidate Name (`candidate_name` ASC). |
| **BR-12** | Category Cut-offs & Reservation Migration | `list_size = vacancies * 10`. GEN cut-off is the normalised score of candidate at rank `vacancies['GEN'] * 10`. Reserved candidates scoring `>= GEN cut-off` are counted in `GEN` and NOT against reserved vacancies. Reserved cut-offs are determined by the remaining candidates of that category. |
| **BR-13** | Re-evaluation & Versioning | Candidates may request re-evaluation once. Raw score is recomputed from final keys and penalties. If score or status changes, version increments and merit list is regenerated; if unchanged, version remains unchanged. |

---

## 🔍 Edge Cases Handled Explicitly

* **EC-01 (Boundary Section Score Equal to Cut-off):** Candidate `RN-001729` (OBC, SH-3) scores exactly 12.50 in SEC-1. OBC cut-off is `(30 - 5)% = 25%` of 50 = 12.50. Tested and verified: exact `>=` comparison qualifies the candidate.
* **EC-02 (Dropped Question Attempted vs Unattempted):** CHL-012 drops PAPER-05 Q46. `RN-002639` had it `MARKED_FOR_REVIEW` with no option chosen (unattempted) -> earns 0. `RN-002467` answered it -> earns full 2 marks with no negative penalty.
* **EC-03 (Shift with Exactly 100 vs 99 Candidates):** SH-2 has 100 candidates -> normalized standalone (GRP-2). SH-4 has 99 candidates -> pooled with SH-5 (GRP-4) into a group of 499.
* **EC-04 (Top 0.1% Ceil Calculation):** SH-1 has 1,500 candidates: `1500 * 0.001 = 1.5 -> ceil = 2`. Across all 2,998 valid candidates: `2998 * 0.001 = 2.998 -> ceil = 3`.
* **EC-05 (Proctoring Severity Boundaries 6 and 7):** `RN-000188` has cumulative severity 6 -> 5% deduction. `RN-000985` has cumulative severity 7 -> 15% deduction.
* **EC-06 (Complete 5-Level Tie-Breaking):** `RN-000031` and `RN-000541` (same shift SH-1) have identical raw score, normalised score (124.21070), SEC-2 score (48.00), wrong answers (0), and identical date of birth (1999-06-15). Resolved alphabetically: `Shruthi Acharya` ranks before `Shruthi Bhat`.
* **EC-07 (Exact 10% Minimum Attempt Boundary):** `RN-002714` attempts exactly 10 of 100 questions (10%). `NOT_QUALIFIED_MIN_ATTEMPT` does not trigger; candidate fails sectional cut-offs.
* **EC-08 (Reserved Candidate Migrating to GEN):** `RN-001688` (SC) scores 147.50000 (rank 2) -> far above GEN cut-off (65.98590) -> counted in `GEN`, leaving the 45 SC vacancies to candidates below the GEN cut-off.
* **Extra Traps:**
  * `RN-001636`: Single `CONFIRMED_MALPRACTICE` flag of severity 1 -> immediately `DISQUALIFIED` with score 0.
  * `RN-002905`: Cumulative severity 10 -> `DISQUALIFIED` with score 0.
  * `RN-001816`: All SEC-4 responses recorded after 6000 seconds -> 0 attempts in SEC-4 -> `SECTION_SKIPPED` in reason.
  * `RN-001524`: PAPER-02 Q26 is multi-correct (key AD). Candidate chose only 'A' -> earns 0 marks, 0 negative deduction, wrong count not incremented.
  * `RN-002730`: Section window boundary edge: Q70 recorded at 4800s (window close) counts; Q95 recorded at 6001s (after window close) treated as `NOT_ATTEMPTED`.
  * `REEVALUATE`: For `RN-001729` and `RN-000031`, scores are unchanged, ensuring version remains at 1.

---

## 🎓 Viva Voce Preparation Guide

### 1. Order of Operations in Result Processing
In examination result processing, the order of application is critical to legal and mathematical fairness:
$$\text{Raw Section Scoring} \longrightarrow \text{Dropped Questions Adjustment} \longrightarrow \text{Proctoring Penalties} \longrightarrow \text{Sectional \& Overall Cut-offs} \longrightarrow \text{Shift Normalisation} \longrightarrow \text{Merit List \& Tie-Breaking} \longrightarrow \text{Category Reservation Migration}$$

* **Why Dropped Questions come before Penalties:** Dropped questions alter the academic scoring of the paper itself (academic key finalization).
* **Why Penalties come before Normalisation:** Normalisation standardizes candidate ability across papers. A candidate penalized for malpractice must have their penalized score (actual final merit potential) enter the normalisation equation; otherwise shifts would suffer distorted means.
* **Why Cut-offs compare Unrounded Raw Scores:** Section cut-offs assess competency in specific subject papers. Normalisation is an overall cross-shift leveling tool, not a section-level metric.
* **Why Normalisation precedes Merit List & Reservation:** Relative rank across different papers can only be fairly decided on normalised scores.

### 2. Derivation of the Normalisation Formula on a Concrete Example
The national recruitment exam normalisation formula is:
$$\widehat{X}_{ij} = \frac{\overline{M}_t^g - \overline{M}_q^g}{\overline{M}_{ti} - \overline{M}_{iq}} \cdot (X_{ij} - \overline{M}_{iq}) + \overline{M}_q^g$$

Where:
* $\widehat{X}_{ij}$: Normalised mark of candidate $j$ in shift $i$.
* $\overline{M}_t^g$: Mean marks of the top 0.1% candidates across all shifts.
* $\overline{M}_q^g$: Mean marks of all candidates across all shifts.
* $\overline{M}_{ti}$: Mean marks of top 0.1% candidates in shift $i$.
* $\overline{M}_{iq}$: Mean marks of all candidates in shift $i$.
* $X_{ij}$: Candidate's raw score after penalties.

#### Numerical Walkthrough Example (from our run):
* Overall top 0.1% mean ($\overline{M}_t^g$): $147.50000$
* Overall global mean ($\overline{M}_q^g$): $56.20640$
* Difference in global performance: $\overline{M}_t^g - \overline{M}_q^g = 147.50000 - 56.20640 = 91.29360$
* Consider a candidate in Shift 1 (Group GRP-1):
  * Shift top 0.1% mean ($\overline{M}_{ti}$): $141.79167$
  * Shift mean ($\overline{M}_{iq}$): $56.36874$
  * Shift spread (denominator): $\overline{M}_{ti} - \overline{M}_{iq} = 141.79167 - 56.36874 = 85.42293$
  * Scaling factor: $\frac{91.29360}{85.42293} \approx 1.068725$
* Candidate `RN-000019` has raw score $X_{ij} = 120.00$:
  * Deviation from shift mean: $120.00 - 56.36874 = 63.63126$
  * Scaled deviation: $63.63126 \times 1.068725 = 68.00430$
  * Final Normalised Score: $68.00430 + 56.20640 = \mathbf{124.21070}$

---

## 🚀 Execution & Verification

### Prerequisites
* Python 3.10+ (Standard Library only; no external pip dependencies needed).

### Running the Engine
```bash
python main.py
```
Or with custom arguments:
```bash
python main.py --data-dir "sample_data/T018-PS-072-sample-data" --commands "sample_data/T018-PS-072-sample-data/commands.txt" --output-dir "output"
```

### Running Test Suite
```bash
python -m unittest discover -s tests -v
```
All 20 unit, integration, and edge-case tests execute and pass in under 4 seconds.

---

## 📤 Output CSV Files Summary
The engine produces the four evaluation CSV files in `output/`:
1. `output/scorecards.csv` (3,000 rows): Detailed scorecard per candidate with raw section scores, penalties, normalised scores, qualification status, and failure reasons.
2. `output/shift_stats.csv` (5 rows): Statistics per normalisation group (SH-1, SH-2, SH-3, SH-4;SH-5, SH-6) showing candidate count, shift mean, top 0.1% mean, and normalisation flag.
3. `output/merit_list.csv` (1,483 rows): Full merit list of all qualified candidates with 5-level tie-breaking and reservation migration.
4. `output/category_cutoffs.csv` (5 rows): Final cut-off marks and qualified list sizes for GEN, OBC, SC, ST, and EWS categories.
