"""Unit tests verifying all 8 planted edge cases and extra traps from PS-072 brief."""

import os
import unittest
from src.engine import ExamResultEngine


class TestEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "sample_data", "T018-PS-072-sample-data"
        ))
        cls.engine = ExamResultEngine(data_dir=base_dir)
        cls.engine.load_data()
        # Execute complete command sequence
        commands_path = os.path.join(base_dir, "commands.txt")
        cls.engine.execute_commands_file(commands_path)

    def test_ec01_raw_section_score_exactly_equal_cutoff_relaxed(self):
        # RN-001729 (OBC, SH-3): SEC-1 has 7 correct (x2) and 3 wrong (QUARTER: -0.5) = 12.50
        # Cutoff = (30 - 5)% of 50 = 12.50 exactly -> passes cut-off (>=)
        sc = self.engine.scorecards["RN-001729"]
        self.assertAlmostEqual(sc.sec1_raw, 12.50, places=2)
        self.assertEqual(sc.status, "QUALIFIED")

    def test_ec02_dropped_question_attempted_vs_unattempted(self):
        # CHL-012 drops PAPER-05 Q46 (SEC-2).
        # RN-002639: MARKED_FOR_REVIEW without option -> unattempted -> 0
        # RN-002467: answered wrongly -> attempted -> full 2 marks and no negative
        sc_unattempted = self.engine.scorecards["RN-002639"]
        sc_attempted = self.engine.scorecards["RN-002467"]
        # Candidate 2467 received full marks (+2) for Q46
        self.assertGreater(sc_attempted.sec2_raw, sc_unattempted.sec2_raw)

    def test_ec03_shift_pooling_100_vs_99(self):
        # SH-2 has 100 -> standalone group (GRP-2)
        # SH-4 has 99 -> pooled with SH-5 (GRP-4) with 499 candidates
        stats_grp2 = next(s for s in self.engine.shift_stats if "SH-2" in s.shift_ids)
        stats_grp4 = next(s for s in self.engine.shift_stats if "SH-4" in s.shift_ids)
        self.assertEqual(stats_grp2.candidates, 100)
        self.assertEqual(stats_grp2.shift_ids, "SH-2")
        self.assertEqual(stats_grp4.candidates, 499)
        self.assertEqual(stats_grp4.shift_ids, "SH-4;SH-5")

    def test_ec04_top_fraction_calculation(self):
        # SH-1 has 1,500 candidates: ceil(1500 * 0.001) = 2
        stats_grp1 = next(s for s in self.engine.shift_stats if "SH-1" in s.shift_ids)
        self.assertEqual(stats_grp1.top_count, 2)

    def test_ec05_proctoring_penalties_boundary_6_and_7(self):
        # RN-000188: severity 6 -> 5% deduction
        # RN-000985: severity 7 -> 15% deduction
        sc_188 = self.engine.scorecards["RN-000188"]
        sc_985 = self.engine.scorecards["RN-000985"]
        self.assertEqual(sc_188.proctor_severity, 6)
        self.assertEqual(sc_188.penalty_pct, 5)
        self.assertAlmostEqual(sc_188.raw_after_penalty, sc_188.raw_total * 0.95, places=2)

        self.assertEqual(sc_985.proctor_severity, 7)
        self.assertEqual(sc_985.penalty_pct, 15)
        self.assertAlmostEqual(sc_985.raw_after_penalty, sc_985.raw_total * 0.85, places=2)

    def test_ec06_full_tie_breaking(self):
        # RN-000031 and RN-000541: identical normalised score, tie-breaker score, wrong=0, DOB=1999-06-15
        # Ordered alphabetically: 'Shruthi Acharya' before 'Shruthi Bhat'
        merit = self.engine.merit_list
        rank_31 = next(m.rank for m in merit if m.roll_no == "RN-000031")
        rank_541 = next(m.rank for m in merit if m.roll_no == "RN-000541")
        self.assertLess(rank_31, rank_541)

    def test_ec07_minimum_attempt_boundary(self):
        # RN-002714 attempts exactly 10 questions (10% of 100)
        # NOT_QUALIFIED_MIN_ATTEMPT must NOT fire; fails sectional cut-offs
        sc = self.engine.scorecards["RN-002714"]
        self.assertEqual(sc.attempted, 10)
        self.assertEqual(sc.status, "NOT_QUALIFIED_SECTIONAL")

    def test_ec08_sc_above_gen_cutoff(self):
        # RN-001688 (SC) answers 100 correctly -> raw 150 -> counted in GEN
        merit = self.engine.merit_list
        mc_1688 = next(m for m in merit if m.roll_no == "RN-001688")
        self.assertEqual(mc_1688.counted_in, "GEN")
        self.assertLessEqual(mc_1688.rank, 1200)

    def test_extra_trap_disqualified_malpractice(self):
        # RN-001636 has single CONFIRMED_MALPRACTICE flag with severity 1 -> DISQUALIFIED, score 0
        sc = self.engine.scorecards["RN-001636"]
        self.assertEqual(sc.status, "DISQUALIFIED")
        self.assertEqual(sc.raw_after_penalty, 0.0)
        self.assertIsNone(sc.normalised)

    def test_extra_trap_disqualified_severity_10(self):
        # RN-002905 cumulative severity = 10 -> DISQUALIFIED, score 0
        sc = self.engine.scorecards["RN-002905"]
        self.assertEqual(sc.status, "DISQUALIFIED")
        self.assertEqual(sc.raw_after_penalty, 0.0)
        self.assertIsNone(sc.normalised)

    def test_extra_trap_skipped_section(self):
        # RN-001816: all SEC-4 answers after window -> 0 attempts -> SECTION_SKIPPED
        sc = self.engine.scorecards["RN-001816"]
        self.assertEqual(sc.status, "NOT_QUALIFIED_SECTIONAL")
        self.assertIn("SECTION_SKIPPED", sc.reason)

    def test_extra_trap_window_boundary(self):
        # RN-002730: Q70 at 4800s counts; Q95 at 6001s is after window close
        sc = self.engine.scorecards["RN-002730"]
        self.assertTrue(sc.attempted > 0)

    def test_extra_trap_reevaluation_version_stability(self):
        # REEVALUATE for RN-001729 and RN-000031: score unchanged -> version stays 1
        self.assertEqual(self.engine.current_version, 1)


if __name__ == "__main__":
    unittest.main()
