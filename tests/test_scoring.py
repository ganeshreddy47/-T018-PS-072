"""Unit tests for scoring, proctoring penalties, and qualification rules."""

import unittest
from src.models import (
    Exam, Section, Shift, AnswerKeyQuestion,
    Candidate, CandidateResponse, ProctorFlag
)
from src.scoring import score_single_candidate, compute_category_relaxation, evaluate_response_attempt


class TestScoringRules(unittest.TestCase):
    def setUp(self):
        self.exam = Exam(
            exam_id="EXM-TEST",
            exam_name="Test Exam",
            total_questions=100,
            overall_cutoff_pct=35.0,
            top_fraction_pct=0.10,
            min_attempt_pct=10.0,
            pooling_min_candidates=100
        )
        self.sections = {
            "SEC-1": Section("SEC-1", "Quant", 1, 25, 2, "QUARTER", 0, 1800, 30.0, False),
            "SEC-2": Section("SEC-2", "Reasoning", 26, 50, 2, "THIRD", 1800, 3600, 30.0, True),
            "SEC-3": Section("SEC-3", "English", 51, 75, 1, "THIRD", 3600, 4800, 30.0, False),
            "SEC-4": Section("SEC-4", "General", 76, 100, 1, "QUARTER", 4800, 6000, 25.0, False),
        }
        self.candidate_gen = Candidate("RN-GEN", "Gen User", "M", "2000-01-01", "GEN", False, "SH-1")
        self.candidate_obc = Candidate("RN-OBC", "OBC User", "F", "2000-01-01", "OBC", False, "SH-1")
        self.candidate_sc = Candidate("RN-SC", "SC User", "M", "2000-01-01", "SC", False, "SH-1")
        self.candidate_pwd = Candidate("RN-PWD", "PwD User", "F", "2000-01-01", "GEN", True, "SH-1")

    def test_category_relaxations(self):
        # GEN: 0%
        self.assertEqual(compute_category_relaxation("GEN", False), 0.0)
        # OBC: 5%
        self.assertEqual(compute_category_relaxation("OBC", False), 5.0)
        # EWS: 5%
        self.assertEqual(compute_category_relaxation("EWS", False), 5.0)
        # SC: 10%
        self.assertEqual(compute_category_relaxation("SC", False), 10.0)
        # ST: 10%
        self.assertEqual(compute_category_relaxation("ST", False), 10.0)
        # GEN + PwD: 5%
        self.assertEqual(compute_category_relaxation("GEN", True), 5.0)
        # SC + PwD: 15%
        self.assertEqual(compute_category_relaxation("SC", True), 15.0)

    def test_response_attempt_evaluation(self):
        sec = self.sections["SEC-1"]
        # Inside window
        r1 = CandidateResponse("RN-1", 1, "A", "ANSWERED", 30, 1500)
        self.assertTrue(evaluate_response_attempt(r1, sec))

        # Exactly at boundary
        r2 = CandidateResponse("RN-1", 1, "A", "ANSWERED", 30, 1800)
        self.assertTrue(evaluate_response_attempt(r2, sec))

        # After window
        r3 = CandidateResponse("RN-1", 1, "A", "ANSWERED", 30, 1801)
        self.assertFalse(evaluate_response_attempt(r3, sec))

        # Marked for review without option
        r4 = CandidateResponse("RN-1", 1, "", "MARKED_FOR_REVIEW", 30, 1500)
        self.assertFalse(evaluate_response_attempt(r4, sec))

        # Not attempted
        r5 = CandidateResponse("RN-1", 1, "", "NOT_ATTEMPTED", 30, None)
        self.assertFalse(evaluate_response_attempt(r5, sec))

    def test_negative_marking_schemes(self):
        # SEC-1: marks=2, QUARTER -> wrong deducts 0.5
        # SEC-2: marks=2, THIRD -> wrong deducts 2/3
        paper_key = {
            1: AnswerKeyQuestion("PAPER-01", 1, "SEC-1", "A", False),
            2: AnswerKeyQuestion("PAPER-01", 2, "SEC-1", "B", False),
            26: AnswerKeyQuestion("PAPER-01", 26, "SEC-2", "C", False),
            27: AnswerKeyQuestion("PAPER-01", 27, "SEC-2", "D", False),
        }
        resps = [
            CandidateResponse("RN-1", 1, "A", "ANSWERED", 20, 100),  # +2
            CandidateResponse("RN-1", 2, "C", "ANSWERED", 20, 200),  # -0.5
            CandidateResponse("RN-1", 26, "C", "ANSWERED", 20, 1900), # +2
            CandidateResponse("RN-1", 27, "A", "ANSWERED", 20, 2000), # -2/3
        ]
        # Add 10 attempts to satisfy min attempt
        for q in range(3, 11):
            paper_key[q] = AnswerKeyQuestion("PAPER-01", q, "SEC-1", "A", False)
            resps.append(CandidateResponse("RN-1", q, "A", "ANSWERED", 10, 500))

        sc = score_single_candidate(self.candidate_gen, paper_key, resps, self.sections, self.exam, [])
        # SEC-1: 2 - 0.5 + 8*2 = 17.5
        self.assertAlmostEqual(sc.sec1_raw, 17.5, places=4)
        # SEC-2: 2 - 2/3 = 1.3333
        self.assertAlmostEqual(sc.sec2_raw, 2.0 - 2.0/3.0, places=4)

    def test_proctoring_penalties(self):
        paper_key = {1: AnswerKeyQuestion("PAPER-01", 1, "SEC-1", "A", False)}
        resps = [CandidateResponse("RN-1", 1, "A", "ANSWERED", 20, 100)]
        for q in range(2, 11):
            paper_key[q] = AnswerKeyQuestion("PAPER-01", q, "SEC-1", "A", False)
            resps.append(CandidateResponse("RN-1", q, "A", "ANSWERED", 10, 500))

        # Severity 5 -> 5% deduction
        flags_5 = [ProctorFlag("PF-1", "RN-1", "TAB_SWITCH", 3, "2026-10-10 09:00:00"),
                   ProctorFlag("PF-2", "RN-1", "AUDIO", 2, "2026-10-10 09:01:00")]
        sc_5 = score_single_candidate(self.candidate_gen, paper_key, resps, self.sections, self.exam, flags_5)
        self.assertEqual(sc_5.penalty_pct, 5)
        self.assertAlmostEqual(sc_5.raw_after_penalty, 20.0 * 0.95, places=4)

        # Severity 8 -> 15% deduction
        flags_8 = flags_5 + [ProctorFlag("PF-3", "RN-1", "TAB_SWITCH", 3, "2026-10-10 09:02:00")]
        sc_8 = score_single_candidate(self.candidate_gen, paper_key, resps, self.sections, self.exam, flags_8)
        self.assertEqual(sc_8.penalty_pct, 15)
        self.assertAlmostEqual(sc_8.raw_after_penalty, 20.0 * 0.85, places=4)

        # Severity 10 -> DISQUALIFIED
        flags_10 = flags_8 + [ProctorFlag("PF-4", "RN-1", "TAB_SWITCH", 2, "2026-10-10 09:03:00")]
        sc_10 = score_single_candidate(self.candidate_gen, paper_key, resps, self.sections, self.exam, flags_10)
        self.assertEqual(sc_10.status, "DISQUALIFIED")
        self.assertEqual(sc_10.raw_after_penalty, 0.0)

        # Confirmed malpractice severity 1 -> DISQUALIFIED
        flags_mal = [ProctorFlag("PF-M", "RN-1", "CONFIRMED_MALPRACTICE", 1, "2026-10-10 09:00:00")]
        sc_mal = score_single_candidate(self.candidate_gen, paper_key, resps, self.sections, self.exam, flags_mal)
        self.assertEqual(sc_mal.status, "DISQUALIFIED")


if __name__ == "__main__":
    unittest.main()
