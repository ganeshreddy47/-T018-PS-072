# PS-072 – Online Exam Proctoring Result Engine with Negative Marking, Sectional Cut-offs and Shift Normalisation — Sample Data Pack

Prepared by 10 SECONDS for Team T018.

## Files

| File | What it holds | Row count |
|---|---|---|
| `exam.csv` | Exam-level parameters (overall cut-off, top fraction, minimum attempts, pooling threshold) | 1 data rows |
| `sections.csv` | 4 sections: question ranges, marks, negative scheme, time window, GEN cut-off, tie-breaker | 4 data rows |
| `vacancies.csv` | Vacancies per category (merit list size = vacancies x 10) | 5 data rows |
| `shifts.csv` | 6 shifts over 2 days, one paper each | 6 data rows |
| `answer_keys.csv` | Provisional answer key, 100 questions x 6 papers | 600 data rows |
| `candidates.csv` | 3,000 candidates with category, PwD flag, DOB and shift | 3000 data rows |
| `responses.csv` | One row per candidate per question (3,000 x 100) | 300000 data rows |
| `proctoring_flags.csv` | ~400 proctoring flags with severity | 400 data rows |
| `challenges.csv` | 15 answer-key challenges with the expert decision | 15 data rows |
| `commands.txt` | Scoring, challenge application, normalisation, merit generation, re-evaluation and prints | 54 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and only occurs in columns whose notes say so.

### `exam.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| exam_id | string | EXM-YYYY-nn | — | — |
| exam_name | string | — | — | — |
| total_questions | int | — | — | — |
| overall_cutoff_pct | decimal | % | — | GEN overall cut-off on the raw score after penalties (relaxed like sections) |
| top_fraction_pct | decimal | % | 0.10 | top 0.1%: count = ceil(n x 0.001), at least 1 |
| min_attempt_pct | decimal | % | 10.00 | attempted < this % of total questions -> NOT_QUALIFIED_MIN_ATTEMPT |
| pooling_min_candidates | int | — | 100 | a shift with fewer candidates is pooled with the next shift of the same day |

### `sections.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| section_id | string | SEC-n | — | — |
| section_name | string | — | — | — |
| question_from | int | — | — | inclusive |
| question_to | int | — | — | inclusive |
| marks_per_question | int | — | 1, 2 | — |
| negative_scheme | enum | — | THIRD, QUARTER | wrong answer deducts 1/3 or 1/4 of the question's marks |
| window_start_min | int | minutes from shift start | — | section opens |
| window_end_min | int | minutes from shift start | — | section closes; a response recorded at exactly this instant is inside the window |
| cutoff_pct | decimal | % | — | GEN sectional cut-off; OBC/EWS -5, SC/ST -10, PwD a further -5 |
| tie_breaker | enum | — | TIE_BREAKER_1 | empty for non-tie-breaker sections |

### `vacancies.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| category | enum | — | GEN, OBC, SC, ST, EWS | — |
| vacancies | int | — | — | — |

### `shifts.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| shift_id | string | SH-n | — | shift order = id order |
| exam_date | date | — | — | — |
| slot | enum | — | MORNING, AFTERNOON, EVENING | — |
| start_time | string | HH:MM:SS | — | IST |
| paper_id | string | PAPER-nn | — | one paper per shift |

### `answer_keys.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| paper_id | string | — | shifts.csv | — |
| question_no | int | 1-100 | — | — |
| section_id | string | — | sections.csv | — |
| correct_options | string | letters A-D, sorted | — | two letters for multi-correct questions |
| multi_correct | bool | — | — | true: full marks only for the exact set, otherwise 0 with no negative |

### `candidates.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| roll_no | string | RN-nnnnnn | — | primary key |
| candidate_name | string | — | — | last tie-breaker (alphabetical) |
| gender | enum | — | M, F | — |
| date_of_birth | date | — | — | older DOB ranks higher on ties |
| category | enum | — | GEN, OBC, SC, ST, EWS | — |
| pwd | bool | — | — | — |
| shift_id | string | — | shifts.csv | — |

### `responses.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| roll_no | string | — | candidates.csv | — |
| question_no | int | 1-100 | — | every candidate has exactly 100 rows |
| option_chosen | string | letters A-D | — | empty when nothing chosen |
| status | enum | — | ANSWERED, NOT_ATTEMPTED, MARKED_FOR_REVIEW | MARKED_FOR_REVIEW with an option is scored as attempted |
| time_spent_sec | int | s | — | informational |
| recorded_at_sec | int | s from shift start | — | when the final option was recorded; empty when no option; after the section window -> NOT_ATTEMPTED |

### `proctoring_flags.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| flag_id | string | PF-nnnn | — | — |
| roll_no | string | — | candidates.csv | — |
| flag_type | enum | — | FACE_NOT_VISIBLE, MULTIPLE_FACES, TAB_SWITCH, AUDIO, CONFIRMED_MALPRACTICE | — |
| severity | int | — | 1-3 | summed per candidate |
| flag_ts | timestamp | — | — | — |

### `challenges.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| challenge_id | string | CHL-nnn | — | — |
| paper_id | string | — | shifts.csv | — |
| question_no | int | — | — | — |
| raised_by | string | — | candidates.csv | — |
| claimed_options | string | — | — | — |
| decision | enum | — | REJECTED, KEY_CHANGED, DROPPED | applied only when its APPLY_CHALLENGE command is processed |
| final_options | string | — | — | new key for KEY_CHANGED; empty otherwise |
| decided_on | date | — | — | — |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An empty argument (two pipes in a row) means "not supplied". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `SCORE_ALL` | `` | Compute raw section and overall scores for every candidate with the current key, penalties and status |
| `APPLY_CHALLENGE` | `challenge_id` | Apply the decision in challenges.csv (key change or drop) and supersede earlier results of that paper |
| `NORMALISE` | `` | Normalise overall scores across shifts (pooling, guard, 5 decimals) |
| `GENERATE_MERIT` | `` | Build merit list version 1 (or next version) and the category cut-offs |
| `REEVALUATE` | `roll_no` | Recompute one candidate; regenerate merit + bump version only if the result changes |
| `PRINT_SHIFT_STATS` | `shift_id` | Per-shift (or pooled group) statistics |
| `PRINT_MERIT` | `category or ALL` | Print the merit list (ALL or a category list) |
| `PRINT_SCORECARD` | `roll_no` | Per-candidate score card |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Raw section score exactly equal to the cut-off marks after relaxation**
  - RN-001729 (OBC, not PwD, SH-3): SEC-1 has 7 correct (x2) and 3 wrong (QUARTER: -0.5 each) = 12.50 = (30 - 5)% of 50 exactly -> passes the sectional cut-off (>=); every other section is well above. No challenge touches PAPER-03, so the score is final — `candidates.csv RN-001729 (row 1729); responses.csv rows 172801-172825 (Q1-Q25)`
- **EC-02 A dropped question that a candidate had marked for review without an option**
  - CHL-012 drops PAPER-05 Q46 (SEC-2). RN-002639 has it MARKED_FOR_REVIEW with no option -> not attempted -> 0 for the dropped question; RN-002467 answered it (wrongly) -> attempted -> full 2 marks and no negative; SEC-2 maximum stays 50 — `challenges.csv CHL-012 (row 12); candidates.csv RN-002639 (row 2639); candidates.csv RN-002467 (row 2467); commands.txt line 20; responses.csv RN-002639 (row 263846) Q46; responses.csv RN-002467 (row 246646) Q46`
- **EC-03 Shift with exactly 100 candidates versus 99 (pooled)**
  - SH-2 has exactly 100 candidates -> normalised on its own; SH-4 has 99 -> pooled with SH-5 (next shift the same day, 2026-10-11) into one group of 499. No candidate in SH-2 or SH-4 is DISQUALIFIED, so the counts are unambiguous — `shifts.csv SH-2 (row 2); shifts.csv SH-4 (row 4); candidates.csv shift_id column`
- **EC-04 Top 0.1% of 1,500 candidates (1.5, ceil to 2)**
  - SH-1 has 1,500 candidates: top 0.1% = 1.5 -> ceil -> 2 candidates for the shift top-mean; across all 3,000 candidates the top 0.1% is exactly 3. No SH-1 candidate is DISQUALIFIED — `shifts.csv SH-1 (row 1); exam.csv EXM-2026-01 (row 1)`
- **EC-05 Cumulative proctoring severity exactly 6 and exactly 7**
  - RN-000188: flags 3+2+1 = cumulative severity exactly 6 -> 5% of raw overall deducted; RN-000985: flags 3+2+2 = exactly 7 -> 15% deducted (both before normalisation) — `candidates.csv RN-000188 (row 188); proctoring_flags.csv PF-0022 (row 22); proctoring_flags.csv PF-0080 (row 80); proctoring_flags.csv PF-0131 (row 131); candidates.csv RN-000985 (row 985); proctoring_flags.csv PF-0031 (row 31); proctoring_flags.csv PF-0090 (row 90); proctoring_flags.csv PF-0164 (row 164)`
- **EC-06 Two candidates with identical normalised score, tie-breaker section score, wrong count and date of birth**
  - RN-000031 and RN-000541 (same shift SH-1, identical responses -> identical raw, normalised, SEC-2 tie-breaker score and wrong count = 0, same date of birth 1999-06-15) -> ordered alphabetically by name: '... Acharya' before '... Bhat' — `candidates.csv RN-000031 (row 31); candidates.csv RN-000541 (row 541)`
- **EC-07 Candidate attempting exactly 10% of questions**
  - RN-002714 attempts exactly 10 of 100 questions (Q1-3, Q26-28, Q51-52, Q76-77; 10% = minimum, so NOT_QUALIFIED_MIN_ATTEMPT must NOT fire); the candidate then fails sectional cut-offs (NOT_QUALIFIED_SECTIONAL) — `candidates.csv RN-002714 (row 2714); responses.csv rows 271301-271400 (all 100 questions)`
- **EC-08 SC candidate above the GEN cut-off and the resulting shift of the SC cut-off**
  - RN-001688 (SC) answers all 100 correctly (raw 150) -> far above the GEN cut-off -> counted in the GEN list and NOT against the 45 SC vacancies, which moves the SC cut-off down to the next SC candidate (vacancies.csv SC row) — `candidates.csv RN-001688 (row 1688); vacancies.csv SC (row 3)`
- **Extra traps (not in the brief, but realistic):**
  - RN-001636: a single CONFIRMED_MALPRACTICE flag of severity 1 -> DISQUALIFIED (score 0) regardless of severity; RN-002905: 3+3+3+1 = 10 -> DISQUALIFIED; neither enters normalisation — `candidates.csv RN-001636 (row 1636); proctoring_flags.csv PF-0256 (row 256); candidates.csv RN-002905 (row 2905); proctoring_flags.csv PF-0361 (row 361); proctoring_flags.csv PF-0368 (row 368); proctoring_flags.csv PF-0378 (row 378); proctoring_flags.csv PF-0387 (row 387)`
  - REEVALUATE for RN-001729 and RN-000031: the recomputed raw score is unchanged, so the merit-list version must stay at 1 (it increments only when a result changes) — `candidates.csv RN-001729 (row 1729); candidates.csv RN-000031 (row 31)`
  - RN-002730: Q70 (SEC-3, window 60-80 min) recorded at 4800 s = exactly the window close -> counts; Q95 (SEC-4, window 80-100 min) recorded at 6001 s = 1 s after close -> NOT_ATTEMPTED — `candidates.csv RN-002730 (row 2730); responses.csv RN-002730 (row 272970) Q70; responses.csv RN-002730 (row 272995) Q95`
  - RN-001816: all 4 SEC-4 answers recorded after the SEC-4 window closed -> 0 attempted in SEC-4 -> SECTION_SKIPPED and fails that cut-off — `candidates.csv RN-001816 (row 1816); responses.csv rows 181576-181579 (Q76-Q79)`
  - RN-001524: PAPER-02 Q26 is multi-correct (key AD); the candidate chose only 'A' -> 0 marks and NO negative — `candidates.csv RN-001524 (row 1524); answer_keys.csv PAPER-02 (row 126) Q26; responses.csv RN-001524 (row 152326) Q26`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `scorecards.csv`

One row per candidate (latest result), sorted by roll_no.

Columns, in order: `roll_no`, `shift_id`, `sec1_raw`, `sec2_raw`, `sec3_raw`, `sec4_raw`, `attempted`, `correct`, `wrong`, `raw_total`, `proctor_severity`, `penalty_pct`, `raw_after_penalty`, `normalised`, `status`, `reason`

### `shift_stats.csv`

One row per normalisation group (pooled shifts joined with ';').

Columns, in order: `group_id`, `shift_ids`, `candidates`, `mean_raw`, `top_count`, `top_mean`, `normalisation_flag`

### `merit_list.csv`

One row per qualified candidate per version, ordered by rank.

Columns, in order: `version`, `rank`, `roll_no`, `category`, `normalised`, `tie_breaker_score`, `wrong`, `date_of_birth`, `candidate_name`, `counted_in`

### `category_cutoffs.csv`

One row per category per version.

Columns, in order: `version`, `category`, `vacancies`, `list_size`, `cutoff_normalised`

Binding choices: raw scores 2 decimals, normalised 5 decimals (display only; compare unrounded); `status` QUALIFIED, NOT_QUALIFIED_SECTIONAL, NOT_QUALIFIED_OVERALL, NOT_QUALIFIED_MIN_ATTEMPT, DISQUALIFIED; `reason` lists failing section ids / SECTION_SKIPPED separated by ';'; `normalisation_flag` NORMALISED or NO_NORMALISATION; `counted_in` is GEN or the candidate's own category. All candidates in candidates.csv sat the exam (no absentees); shift counts include disqualified candidates.
