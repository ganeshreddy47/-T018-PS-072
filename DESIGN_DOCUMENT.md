# DESIGN DOCUMENT: Online Exam Proctoring Result Engine (PS-072)

**Team ID:** T018  
**Section:** CSDS A  
**Members:** K GANESH REDDY (1AT24CD036), KATTE SHREYAS (1AT24CD037)  
**Domain:** Education – Online Assessment  
**Language:** Python 3.10+ (Tested on Python 3.14)

---

## 1. System Architecture & High-Level Design

The Result Engine is built as a modular, command-driven batch processing system designed for precision, determinism, and high throughput. The architecture separates core mathematical scoring, statistical normalisation, reservation policies, and command orchestration into distinct decoupled modules.

```
+-----------------------------------------------------------------------------------+
|                                 ExamResultEngine                                  |
|   (Coordinates Ingestion, Command Execution, Versioning, and Evaluation Export)    |
+-----------------------------------------------------------------------------------+
           |                     |                      |                     |
           v                     v                      v                     v
   +---------------+   +-------------------+   +------------------+   +-------------+
   |   scoring.py  |   | normalisation.py  |   |     merit.py     |   |  models.py  |
   | - BR-01..07   |   | - BR-08..10       |   | - BR-11..12      |   | - Data      |
   | - Responses   |   | - Pooling         |   | - 5-Level Ties   |   |   Entities  |
   | - Penalties   |   | - Top 0.1% Ceil   |   | - Migration to   |   | - Types     |
   | - Cut-offs    |   | - Normalisation   |   |   GEN Vacancies  |   |             |
   +---------------+   +-------------------+   +------------------+   +-------------+
```

### Module Responsibilities
1. **`models.py`:** Strongly-typed immutable dataclasses encapsulating all entities: `Exam`, `Section`, `Shift`, `Candidate`, `CandidateResponse`, `AnswerKeyQuestion`, `ProctorFlag`, `Challenge`, `ScoreCard`, `ShiftStats`, `MeritCandidate`, and `CategoryCutoff`.
2. **`scoring.py`:** Implements per-candidate response evaluation, time-window checking, negative deduction rules, dropped-question adjustments, cumulative proctoring penalty evaluation, and sectional/overall cut-off verification.
3. **`normalisation.py`:** Implements shift grouping and pooling (< 100 candidates), calculation of shift and global statistics (mean and top 0.1% ceil mean), zero/negative denominator guard, and normalisation scaling.
4. **`merit.py`:** Implements the 5-tier deterministic tie-breaking engine, reservation migration (merit-based migration of reserved candidates to GEN vacancies), and category cut-off determination.
5. **`engine.py`:** State machine executing commands strictly in file order, maintaining scorecards and merit versions, and serializing the final evaluation CSVs.

---

## 2. Business Rules Specification

### BR-01: Scoring Scheme & Negative Marking
* Each section defines `marks_per_question` ($M_q \in \{1, 2\}$) and `negative_scheme` ($\text{frac} \in \{1/3, 1/4\}$).
* A correct answer earns $+M_q$.
* A wrong answer deducts $M_q \times \text{frac}$.
* Unattempted questions earn 0.
* A question `MARKED_FOR_REVIEW` with an option chosen is scored as attempted.
* Multiple-correct questions (`multi_correct == True`): earn full marks $+M_q$ ONLY for the exact sorted set of correct options; otherwise earn 0 with no negative marking and no wrong answer count increment.

### BR-02: Dropped Questions & Key Changes
* Dropped questions: If a question is dropped after challenge, every candidate in that shift who attempted the question receives $+M_q$; unattempted candidates receive 0. Section maximum marks remain unchanged.
* Key changes: Correct options are updated, and all candidates belonging to the affected paper are dynamically re-scored.

### BR-03: Sectional Time Windows & Skipped Sections
* Responses with `recorded_at_sec > window_end_min * 60` are strictly treated as `NOT_ATTEMPTED`.
* Any section with 0 attempted questions is flagged `SECTION_SKIPPED` and automatically fails that section cut-off.

### BR-04 & BR-05: Sectional & Overall Cut-offs with Category Relaxations
* Relaxations applied as percentage points subtracted from base cut-off %:
  * `GEN`: $0\%$
  * `OBC` / `EWS`: $5\%$
  * `SC` / `ST`: $10\%$
  * `PwD`: Additional $5\%$ (cumulative with category relaxation).
* Sectional Cut-off Check: Unrounded raw section score must be $\ge \frac{\text{Cutoff}_{\text{relaxed}}}{100} \times \text{Section Max Marks}$.
* Overall Cut-off Check: Unrounded raw score after penalties must be $\ge \frac{\text{Overall Cutoff}_{\text{relaxed}}}{100} \times \text{Exam Max Marks}$.
* Candidate failing any section is `NOT_QUALIFIED_SECTIONAL`. Candidate passing all sections but failing overall is `NOT_QUALIFIED_OVERALL`.

### BR-06: Minimum Attempts
* Candidates attempting fewer than $10\%$ of total questions are flagged `NOT_QUALIFIED_MIN_ATTEMPT` regardless of marks.

### BR-07: Proctoring Penalties & Disqualification
* Sum of severities $S = \sum s_i$.
* $S \in [4, 6] \implies 5\%$ deduction on raw overall score.
* $S \in [7, 9] \implies 15\%$ deduction on raw overall score.
* $S \ge 10$ OR flag `CONFIRMED_MALPRACTICE` $\implies$ `DISQUALIFIED` with raw score 0.
* Disqualified candidates do not enter shift statistics and are never normalised.

### BR-08, BR-09, BR-10: Shift Normalisation & Pooling
* Shifts with candidate count $< 100$ are pooled with the next shift of the same date.
* Top fraction count: $N_{\text{top}} = \max(1, \lceil n \times 0.001 \rceil)$.
* Normalisation formula:
  $$\widehat{X}_{ij} = \frac{\overline{M}_t^g - \overline{M}_q^g}{\overline{M}_{ti} - \overline{M}_{iq}} \cdot (X_{ij} - \overline{M}_{iq}) + \overline{M}_q^g$$
* Normalisation guard: If denominator $\overline{M}_{ti} - \overline{M}_{iq} \le 0$, normalised score = raw score and flag is `NO_NORMALISATION`.

### BR-11: Merit List & 5-Level Deterministic Tie-Breaking
Only candidates with status `QUALIFIED` enter the merit list, ranked by:
1. Normalised overall score (Descending)
2. Score in Section 2 (`TIE_BREAKER_1`) (Descending)
3. Wrong answer count (Ascending)
4. Date of birth (Ascending, older candidates rank higher)
5. Candidate name (Ascending, alphabetical order)

### BR-12: Reservation Migration & Category Cut-offs
* $\text{GEN}$ list size $= \text{Vacancies}_{\text{GEN}} \times 10$.
* The $\text{GEN}$ cut-off is the normalised score of the candidate at rank $\text{Vacancies}_{\text{GEN}} \times 10$ in the global merit list.
* Any reserved candidate (`OBC`, `SC`, `ST`, `EWS`) scoring $\ge \text{GEN cut-off}$ is counted in $\text{GEN}$ (`counted_in = 'GEN'`) and does not exhaust reserved quotas.
* Reserved quotas are filled from remaining qualified candidates of that category.

### BR-13: Re-evaluation
* Candidate raw score is recomputed from the final key and penalties.
* Version number increments and merit list is regenerated only if the candidate's score or status changes.

---

## 3. Mathematical Analysis & Edge Case Proofs

### Exact Boundary Comparisons
In floating-point environments, comparisons against boundary thresholds (e.g. EC-01 where raw score = 12.50) are evaluated using exact numerical equality without premature rounding.

### Denominator Guard Proof
When all candidates in a shift have identical scores, $\overline{M}_{ti} = \overline{M}_{iq} \implies \text{Denominator} = 0$. Division by zero is trapped by the guard condition:
$$\text{Denominator} \le 0 \implies \widehat{X}_{ij} = X_{ij}, \quad \text{flag} = \text{NO\_NORMALISATION}$$
This guarantees mathematical stability under degenerate test conditions.

---

## 4. Verification & Validation Strategy
The test suite consists of 20 automated tests:
* **Unit Tests (`test_scoring.py`):** Negative schemes, proctoring tiers, multi-correct, and attempt criteria.
* **Normalisation Tests (`test_normalisation.py`):** Shift pooling (< 100), top 0.1% ceil calculations, and zero-denominator guard.
* **Edge Case Verification (`test_edge_cases.py`):** Explicit assertions for all planted cases EC-01 through EC-08 and extra traps.
* **End-to-End Tests (`test_end_to_end.py`):** Complete execution of `commands.txt` and strict schema validation of all 4 output CSV files.
