"""
Engine module for PS-072 Result Engine.
Coordinates data ingestion, command-file execution, re-evaluation, printing, and CSV export.
"""

import csv
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .models import (
    Exam, Section, Shift, AnswerKeyQuestion,
    Candidate, CandidateResponse, ProctorFlag, Challenge,
    ScoreCard, ShiftStats, MeritCandidate, CategoryCutoff
)
from .scoring import score_single_candidate
from .normalisation import form_normalisation_groups, compute_shift_normalisation
from .merit import generate_merit_list_and_cutoffs


class ExamResultEngine:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.exam: Optional[Exam] = None
        self.sections: Dict[str, Section] = {}
        self.vacancies: Dict[str, int] = {}
        self.shifts: Dict[str, Shift] = {}
        self.candidates: Dict[str, Candidate] = {}
        self.responses: Dict[str, List[CandidateResponse]] = defaultdict(list)
        self.proctor_flags: Dict[str, List[ProctorFlag]] = defaultdict(list)
        self.challenges: Dict[str, Challenge] = {}
        self.answer_keys: Dict[str, Dict[int, AnswerKeyQuestion]] = defaultdict(dict)

        # Engine state
        self.scorecards: Dict[str, ScoreCard] = {}
        self.shift_groups: List[Dict] = []
        self.shift_stats: List[ShiftStats] = []
        self.merit_list: List[MeritCandidate] = []
        self.category_cutoffs: List[CategoryCutoff] = []
        self.all_merit_versions: List[List[MeritCandidate]] = []
        self.all_cutoff_versions: List[List[CategoryCutoff]] = []
        self.current_version: int = 1
        self.applied_challenges: set = set()

    def load_data(self):
        """Loads all input CSV files from the specified data directory."""
        # 1. exam.csv
        exam_path = os.path.join(self.data_dir, "exam.csv")
        with open(exam_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.exam = Exam(
                exam_id=row["exam_id"],
                exam_name=row["exam_name"],
                total_questions=int(row["total_questions"]),
                overall_cutoff_pct=float(row["overall_cutoff_pct"]),
                top_fraction_pct=float(row["top_fraction_pct"]),
                min_attempt_pct=float(row["min_attempt_pct"]),
                pooling_min_candidates=int(row["pooling_min_candidates"])
            )

        # 2. sections.csv
        sections_path = os.path.join(self.data_dir, "sections.csv")
        with open(sections_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.sections[row["section_id"]] = Section(
                    section_id=row["section_id"],
                    section_name=row["section_name"],
                    question_from=int(row["question_from"]),
                    question_to=int(row["question_to"]),
                    marks_per_question=int(row["marks_per_question"]),
                    negative_scheme=row["negative_scheme"],
                    window_start_sec=int(row["window_start_min"]) * 60,
                    window_end_sec=int(row["window_end_min"]) * 60,
                    cutoff_pct=float(row["cutoff_pct"]),
                    is_tie_breaker=(row["tie_breaker"] == "TIE_BREAKER_1")
                )

        # 3. vacancies.csv
        vac_path = os.path.join(self.data_dir, "vacancies.csv")
        with open(vac_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.vacancies[row["category"]] = int(row["vacancies"])

        # 4. shifts.csv
        shifts_path = os.path.join(self.data_dir, "shifts.csv")
        with open(shifts_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.shifts[row["shift_id"]] = Shift(
                    shift_id=row["shift_id"],
                    exam_date=row["exam_date"],
                    slot=row["slot"],
                    start_time=row["start_time"],
                    paper_id=row["paper_id"]
                )

        # 5. answer_keys.csv
        keys_path = os.path.join(self.data_dir, "answer_keys.csv")
        with open(keys_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                paper_id = row["paper_id"]
                q_no = int(row["question_no"])
                self.answer_keys[paper_id][q_no] = AnswerKeyQuestion(
                    paper_id=paper_id,
                    question_no=q_no,
                    section_id=row["section_id"],
                    correct_options=row["correct_options"],
                    multi_correct=(row["multi_correct"].strip().lower() == "true"),
                    is_dropped=False
                )

        # 6. candidates.csv
        cands_path = os.path.join(self.data_dir, "candidates.csv")
        with open(cands_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.candidates[row["roll_no"]] = Candidate(
                    roll_no=row["roll_no"],
                    candidate_name=row["candidate_name"],
                    gender=row["gender"],
                    date_of_birth=row["date_of_birth"],
                    category=row["category"],
                    pwd=(row["pwd"].strip().lower() == "true"),
                    shift_id=row["shift_id"]
                )

        # 7. responses.csv
        resp_path = os.path.join(self.data_dir, "responses.csv")
        with open(resp_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rec = row["recorded_at_sec"]
                rec_sec = int(rec) if rec and rec.strip() != "" else None
                self.responses[row["roll_no"]].append(CandidateResponse(
                    roll_no=row["roll_no"],
                    question_no=int(row["question_no"]),
                    option_chosen=row["option_chosen"].strip(),
                    status=row["status"].strip(),
                    time_spent_sec=int(row["time_spent_sec"]) if row["time_spent_sec"] else 0,
                    recorded_at_sec=rec_sec
                ))

        # 8. proctoring_flags.csv
        flags_path = os.path.join(self.data_dir, "proctoring_flags.csv")
        with open(flags_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.proctor_flags[row["roll_no"]].append(ProctorFlag(
                    flag_id=row["flag_id"],
                    roll_no=row["roll_no"],
                    flag_type=row["flag_type"].strip(),
                    severity=int(row["severity"]),
                    flag_ts=row["flag_ts"]
                ))

        # 9. challenges.csv
        chal_path = os.path.join(self.data_dir, "challenges.csv")
        with open(chal_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.challenges[row["challenge_id"]] = Challenge(
                    challenge_id=row["challenge_id"],
                    paper_id=row["paper_id"],
                    question_no=int(row["question_no"]),
                    raised_by=row["raised_by"],
                    claimed_options=row["claimed_options"],
                    decision=row["decision"].strip(),
                    final_options=row["final_options"].strip(),
                    decided_on=row["decided_on"]
                )

        # Form normalisation groups
        cand_counts = defaultdict(int)
        for c in self.candidates.values():
            cand_counts[c.shift_id] += 1
        self.shift_groups = form_normalisation_groups(
            list(self.shifts.values()),
            cand_counts,
            self.exam.pooling_min_candidates
        )

    def score_all(self):
        """Scores all candidates across all shifts using the current answer keys and flags."""
        for roll_no, cand in self.candidates.items():
            shift = self.shifts[cand.shift_id]
            paper_key = self.answer_keys[shift.paper_id]
            resps = self.responses.get(roll_no, [])
            flags = self.proctor_flags.get(roll_no, [])

            sc = score_single_candidate(
                candidate=cand,
                paper_key=paper_key,
                responses=resps,
                sections=self.sections,
                exam=self.exam,
                proctor_flags=flags
            )
            # Preserve previously computed normalised score if available
            if roll_no in self.scorecards and self.scorecards[roll_no].normalised is not None:
                sc.normalised = self.scorecards[roll_no].normalised
            self.scorecards[roll_no] = sc

    def apply_challenge(self, challenge_id: str):
        """Applies a challenge decision (KEY_CHANGED or DROPPED) to answer keys."""
        if challenge_id not in self.challenges:
            print(f"Warning: Challenge {challenge_id} not found.")
            return

        ch = self.challenges[challenge_id]
        paper_id = ch.paper_id
        q_no = ch.question_no
        decision = ch.decision

        if decision == "KEY_CHANGED":
            self.answer_keys[paper_id][q_no].correct_options = ch.final_options
            self.applied_challenges.add(challenge_id)
        elif decision == "DROPPED":
            self.answer_keys[paper_id][q_no].is_dropped = True
            self.applied_challenges.add(challenge_id)
        elif decision == "REJECTED":
            pass

    def normalise(self):
        """Executes the shift normalisation formula across all groups."""
        self.shift_stats, _ = compute_shift_normalisation(
            scorecards=self.scorecards,
            shifts=list(self.shifts.values()),
            groups=self.shift_groups,
            top_fraction_pct=self.exam.top_fraction_pct
        )

    def generate_merit(self):
        """Generates the merit list and category cut-offs for the current version."""
        self.merit_list, self.category_cutoffs = generate_merit_list_and_cutoffs(
            scorecards=self.scorecards,
            candidates=self.candidates,
            vacancies=self.vacancies,
            version=self.current_version
        )
        self.all_merit_versions.append(list(self.merit_list))
        self.all_cutoff_versions.append(list(self.category_cutoffs))

    def reevaluate(self, roll_no: str):
        """
        Recomputes raw score for candidate roll_no from the final key and penalties.
        If the result changes, increments the version and regenerates merit list.
        """
        if roll_no not in self.candidates:
            print(f"Candidate {roll_no} not found.")
            return

        cand = self.candidates[roll_no]
        shift = self.shifts[cand.shift_id]
        paper_key = self.answer_keys[shift.paper_id]
        resps = self.responses.get(roll_no, [])
        flags = self.proctor_flags.get(roll_no, [])

        prev_sc = self.scorecards.get(roll_no)
        new_sc = score_single_candidate(
            candidate=cand,
            paper_key=paper_key,
            responses=resps,
            sections=self.sections,
            exam=self.exam,
            proctor_flags=flags
        )

        # Check if score or status changed
        changed = False
        if prev_sc is None:
            changed = True
        else:
            if (round(prev_sc.raw_after_penalty, 2) != round(new_sc.raw_after_penalty, 2) or
                    prev_sc.status != new_sc.status):
                changed = True

        if changed:
            self.scorecards[roll_no] = new_sc
            self.current_version += 1
            # Re-normalise and re-generate merit
            self.normalise()
            self.generate_merit()
            print(f"Candidate {roll_no} re-evaluated: score changed. Merit list bumped to version {self.current_version}.")
        else:
            print(f"Candidate {roll_no} re-evaluated: score unchanged ({new_sc.raw_after_penalty:.2f}). Merit list version remains {self.current_version}.")

    def print_shift_stats(self, shift_id: str):
        """Prints shift statistics for the given shift_id or its pooled group."""
        # Find group containing shift_id
        target_group = None
        for grp in self.shift_groups:
            if shift_id in grp["shift_ids"]:
                target_group = grp
                break

        if not target_group:
            print(f"Shift {shift_id} not found in any normalisation group.")
            return

        # Find ShiftStats
        stats = next((s for s in self.shift_stats if s.group_id == target_group["group_id"]), None)
        if not stats:
            print(f"Shift stats not computed yet for {shift_id}.")
            return

        print(f"\n--- Shift Statistics [{shift_id}] (Group: {stats.group_id}) ---")
        print(f"  Shift IDs:           {stats.shift_ids}")
        print(f"  Total Candidates:    {stats.candidates}")
        print(f"  Shift Mean (M_s):    {stats.mean_raw:.2f}")
        print(f"  Top 0.1% Count:      {stats.top_count}")
        print(f"  Top 0.1% Mean (M_st):{stats.top_mean:.2f}")
        print(f"  Normalisation Flag:  {stats.normalisation_flag}")

    def print_merit(self, category_or_all: str):
        """
        Prints the merit list:
        - If 'ALL': prints overall qualified merit list.
        - If specific category (e.g. 'OBC'): prints all candidates of that category
          qualified in GEN plus those qualified in that category.
        """
        target = category_or_all.strip().upper()
        if target == "ALL":
            print(f"\n--- Merit List (Version {self.current_version}) [ALL Qualified Candidates: {len(self.merit_list)}] ---")
            print(f"{'Rank':<6}{'Roll No':<12}{'Category':<10}{'Normalised':<14}{'SEC-2 Score':<14}{'Wrong':<8}{'DOB':<12}{'Counted In':<12}{'Name'}")
            print("-" * 96)
            for mc in self.merit_list[:50]:  # Print top 50 in console
                print(f"{mc.rank:<6}{mc.roll_no:<12}{mc.category:<10}{mc.normalised:<14.5f}{mc.tie_breaker_score:<14.2f}{mc.wrong:<8}{mc.date_of_birth:<12}{mc.counted_in:<12}{mc.candidate_name}")
            if len(self.merit_list) > 50:
                print(f"... and {len(self.merit_list) - 50} more qualified candidates.")
        else:
            # Brief: category merit lists are built from the same ordering filtered by category plus all GEN-qualified candidates of that category
            cat_list = [mc for mc in self.merit_list if mc.category == target]
            print(f"\n--- Category Merit List [{target}] (Version {self.current_version}) [Total: {len(cat_list)}] ---")
            print(f"{'Rank':<6}{'Roll No':<12}{'Category':<10}{'Normalised':<14}{'SEC-2 Score':<14}{'Wrong':<8}{'DOB':<12}{'Counted In':<12}{'Name'}")
            print("-" * 96)
            for mc in cat_list[:30]:
                print(f"{mc.rank:<6}{mc.roll_no:<12}{mc.category:<10}{mc.normalised:<14.5f}{mc.tie_breaker_score:<14.2f}{mc.wrong:<8}{mc.date_of_birth:<12}{mc.counted_in:<12}{mc.candidate_name}")
            if len(cat_list) > 30:
                print(f"... and {len(cat_list) - 30} more candidates in {target} list.")

    def print_scorecard(self, roll_no: str):
        """Prints a detailed scorecard for the specified candidate."""
        sc = self.scorecards.get(roll_no)
        if not sc:
            print(f"Scorecard not available for candidate {roll_no}.")
            return

        cand = self.candidates[roll_no]
        print(f"\n========================================================")
        print(f"           CANDIDATE SCORE CARD : {roll_no}")
        print(f"========================================================")
        print(f"  Candidate Name:     {cand.candidate_name}")
        print(f"  Gender / DOB:       {cand.gender} / {cand.date_of_birth}")
        print(f"  Category / PwD:     {cand.category} / {'Yes' if cand.pwd else 'No'}")
        print(f"  Shift ID:           {sc.shift_id}")
        print(f"--------------------------------------------------------")
        print(f"  Section 1 (Quant):  {sc.sec1_raw:.2f} marks")
        print(f"  Section 2 (Reason): {sc.sec2_raw:.2f} marks (Tie-breaker 1)")
        print(f"  Section 3 (English):{sc.sec3_raw:.2f} marks")
        print(f"  Section 4 (General):{sc.sec4_raw:.2f} marks")
        print(f"--------------------------------------------------------")
        print(f"  Attempted / Tot Qs: {sc.attempted} / {self.exam.total_questions}")
        print(f"  Correct / Wrong:    {sc.correct} / {sc.wrong}")
        print(f"  Raw Total Marks:    {sc.raw_total:.2f}")
        print(f"  Proctor Severity:   {sc.proctor_severity}")
        print(f"  Penalty Applied:    {sc.penalty_pct}%")
        print(f"  Score After Penalty:{sc.raw_after_penalty:.2f}")
        norm_str = f"{sc.normalised:.5f}" if sc.normalised is not None else "N/A"
        print(f"  Normalised Score:   {norm_str}")
        print(f"  Result Status:      {sc.status}")
        if sc.reason:
            print(f"  Failure Reasons:    {sc.reason}")
        print(f"========================================================\n")

    def execute_commands_file(self, commands_path: str):
        """Reads and executes commands strictly in file order."""
        with open(commands_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue

                parts = clean_line.split("|")
                cmd = parts[0].strip().upper()
                args = [p.strip() for p in parts[1:]]

                if cmd == "SCORE_ALL":
                    self.score_all()
                elif cmd == "APPLY_CHALLENGE":
                    if args:
                        self.apply_challenge(args[0])
                elif cmd == "NORMALISE":
                    self.normalise()
                elif cmd == "GENERATE_MERIT":
                    self.generate_merit()
                elif cmd == "REEVALUATE":
                    if args:
                        self.reevaluate(args[0])
                elif cmd == "PRINT_SHIFT_STATS":
                    if args:
                        self.print_shift_stats(args[0])
                elif cmd == "PRINT_MERIT":
                    if args:
                        self.print_merit(args[0])
                elif cmd == "PRINT_SCORECARD":
                    if args:
                        self.print_scorecard(args[0])
                else:
                    print(f"Unknown command on line {line_no}: {cmd}")

    def export_csv_outputs(self, output_dir: str):
        """
        Exports all four evaluation CSV files with exact formats specified in README:
        - scorecards.csv
        - shift_stats.csv
        - merit_list.csv
        - category_cutoffs.csv
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. scorecards.csv
        scorecards_path = os.path.join(output_dir, "scorecards.csv")
        with open(scorecards_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "roll_no", "shift_id", "sec1_raw", "sec2_raw", "sec3_raw", "sec4_raw",
                "attempted", "correct", "wrong", "raw_total", "proctor_severity",
                "penalty_pct", "raw_after_penalty", "normalised", "status", "reason"
            ])
            for roll_no in sorted(self.scorecards.keys()):
                sc = self.scorecards[roll_no]
                norm_str = f"{sc.normalised:.5f}" if sc.normalised is not None else ""
                writer.writerow([
                    sc.roll_no,
                    sc.shift_id,
                    f"{sc.sec1_raw:.2f}",
                    f"{sc.sec2_raw:.2f}",
                    f"{sc.sec3_raw:.2f}",
                    f"{sc.sec4_raw:.2f}",
                    sc.attempted,
                    sc.correct,
                    sc.wrong,
                    f"{sc.raw_total:.2f}",
                    sc.proctor_severity,
                    sc.penalty_pct,
                    f"{sc.raw_after_penalty:.2f}",
                    norm_str,
                    sc.status,
                    sc.reason
                ])

        # 2. shift_stats.csv
        shift_stats_path = os.path.join(output_dir, "shift_stats.csv")
        with open(shift_stats_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "group_id", "shift_ids", "candidates", "mean_raw",
                "top_count", "top_mean", "normalisation_flag"
            ])
            for ss in self.shift_stats:
                writer.writerow([
                    ss.group_id,
                    ss.shift_ids,
                    ss.candidates,
                    f"{ss.mean_raw:.2f}",
                    ss.top_count,
                    f"{ss.top_mean:.2f}",
                    ss.normalisation_flag
                ])

        # 3. merit_list.csv
        merit_path = os.path.join(output_dir, "merit_list.csv")
        with open(merit_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "version", "rank", "roll_no", "category", "normalised",
                "tie_breaker_score", "wrong", "date_of_birth", "candidate_name", "counted_in"
            ])
            # Export all versions generated
            for version_list in self.all_merit_versions:
                for mc in version_list:
                    writer.writerow([
                        mc.version,
                        mc.rank,
                        mc.roll_no,
                        mc.category,
                        f"{mc.normalised:.5f}",
                        f"{mc.tie_breaker_score:.2f}",
                        mc.wrong,
                        mc.date_of_birth,
                        mc.candidate_name,
                        mc.counted_in
                    ])

        # 4. category_cutoffs.csv
        cutoffs_path = os.path.join(output_dir, "category_cutoffs.csv")
        with open(cutoffs_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "version", "category", "vacancies", "list_size", "cutoff_normalised"
            ])
            for version_cutoffs in self.all_cutoff_versions:
                for cc in version_cutoffs:
                    writer.writerow([
                        cc.version,
                        cc.category,
                        cc.vacancies,
                        cc.list_size,
                        f"{cc.cutoff_normalised:.5f}"
                    ])

        print(f"\nSuccessfully exported all 4 evaluation CSV files to: {output_dir}")
