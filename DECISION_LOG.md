# DECISION LOG: Online Exam Proctoring Result Engine (PS-072)

**Team ID:** T018  
**Project:** PS-072 Online Exam Proctoring Result Engine  
**Team Members:** K GANESH REDDY, KATTE SHREYAS  

---

## Architecture Decision Records (ADRs)

### ADR-01: Programming Language Choice – Python 3.10+
* **Context:** The brief permitted Java 17+ or Python 3.10+.
* **Decision:** We chose Python 3.10+ (specifically Python 3.14 on the host environment).
* **Rationale:** Python provides superior built-in data manipulation capabilities (`dataclasses`, `defaultdict`, `csv`), zero third-party dependencies required, fast test cycle turnaround, and transparent floating-point calculations with clear mathematical readability for viva defense.

### ADR-02: Zero External Dependencies Policy
* **Context:** Evaluation environments vary widely and may lack access to internet or package managers (such as pip or pandas).
* **Decision:** Rely 100% on Python's built-in standard library (`csv`, `math`, `collections`, `dataclasses`, `typing`, `unittest`).
* **Rationale:** Ensures zero installation friction, instant portable execution across any platform, zero dependency security vulnerabilities, and deterministic reproducibility.

### ADR-03: Two-Phase Cut-off Comparison (Unrounded vs Display)
* **Context:** The brief specifies: "raw scores are shown to 2 decimals, normalised to 5 decimals; percentages for cut-offs compare the unrounded raw section score against the cut-off marks with exact comparison."
* **Decision:** Keep all internal scores as full unrounded floating-point values throughout scoring, cut-off evaluation, and normalisation; only format with rounding during printing and CSV file serialization.
* **Rationale:** Prevents precision truncation errors that could incorrectly disqualify a borderline candidate (e.g. EC-01 where 12.50 is exactly equal to the cut-off marks).

### ADR-04: Multi-Correct Questions Scoring & Wrong Answer Count
* **Context:** BR-01 states: "a question with multiple correct options earns full marks only for the exact set and 0 otherwise with no negative."
* **Decision:** A candidate choosing a partial or incorrect set on a multi-correct question receives 0 marks, 0 deduction, and the question is NOT incremented in the `wrong` counter.
* **Rationale:** Confirmed by planted trap `RN-001524` (Q26 chose A for AD) where wrong answers did not count from Q26.

### ADR-05: Dropped Questions and Section Maximum Marks
* **Context:** When a question is dropped after a challenge, the brief states: "every candidate in that shift receives full marks for it only if they attempted it (any option), else 0, and the section maximum is unchanged."
* **Decision:** When Q is dropped, candidate gets full $+M_q$ if attempted. The section maximum marks denominator remains constant at its initial value (e.g. 50 marks for SEC-1/2, 25 marks for SEC-3/4).
* **Rationale:** Aligns with standard Indian recruitment exam rules (e.g. SSC/IBPS/UPSC) where section maximum remains constant so percentage cut-offs remain stable.

### ADR-06: Strict Order of Normalisation and Disqualified Candidates Exclusion
* **Context:** Disqualified candidates receive score 0 and normalisation is never applied to them.
* **Decision:** Disqualified candidates are excluded from the candidate pool entering mean ($\overline{M}_q^g, \overline{M}_{iq}$) and top 0.1% mean ($\overline{M}_t^g, \overline{M}_{ti}$) computations. However, shift candidate counts in `shift_stats.csv` include all candidates who sat the exam (including disqualified candidates) as specified in README line 200.
* **Rationale:** Disqualification due to malpractice reflects invalid test data. Including a compromised 0 score in the normalisation mean would artificially drag down the shift mean and unfairly inflate scores of innocent candidates in that shift.

### ADR-07: Deterministic 5-Level Tie-Breaking
* **Context:** Candidate ties on normalised score must be resolved completely deterministically.
* **Decision:** Implement a 5-tier composite sort key:
  1. `normalised` DESC
  2. `sec2_raw` (`TIE_BREAKER_1`) DESC
  3. `wrong` ASC
  4. `date_of_birth` ASC (older candidate first)
  5. `candidate_name` ASC (alphabetical)
* **Rationale:** Guarantees 100% deterministic ranking across all runs and platforms, verified on `RN-000031` and `RN-000541` (EC-06).

### ADR-08: Constitutional Reservation Migration
* **Context:** BR-12 states: "a reserved-category candidate scoring at or above the GEN cut-off is counted in GEN and not against the reserved vacancies."
* **Decision:** Top `vacancies['GEN'] * 10` candidates of the merit list are assigned `counted_in = 'GEN'`. Reserved candidates inside this pool migrate to GEN. The reserved quota is filled by candidates of that category ranked below the GEN cut-off.
* **Rationale:** Follows established supreme court precedent and Indian civil service examination reservation jurisprudence (e.g. EC-08 `RN-001688`).
