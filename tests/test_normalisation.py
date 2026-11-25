"""Unit tests for normalisation formula, pooling, and guards."""

import unittest
from src.models import Shift, ScoreCard
from src.normalisation import form_normalisation_groups, compute_shift_normalisation


class TestNormalisation(unittest.TestCase):
    def test_shift_pooling(self):
        shifts = [
            Shift("SH-1", "2026-10-10", "MORNING", "09:00:00", "PAPER-01"),
            Shift("SH-2", "2026-10-10", "AFTERNOON", "12:30:00", "PAPER-02"),
            Shift("SH-3", "2026-10-10", "EVENING", "16:00:00", "PAPER-03"),
            Shift("SH-4", "2026-10-11", "MORNING", "09:00:00", "PAPER-04"),
            Shift("SH-5", "2026-10-11", "AFTERNOON", "12:30:00", "PAPER-05"),
            Shift("SH-6", "2026-10-11", "EVENING", "16:00:00", "PAPER-06"),
        ]
        counts = {
            "SH-1": 1500,
            "SH-2": 100,  # Exactly 100 -> standalone
            "SH-3": 600,
            "SH-4": 99,   # 99 -> pooled with SH-5 (same day)
            "SH-5": 400,
            "SH-6": 301,
        }
        groups = form_normalisation_groups(shifts, counts, min_candidates=100)
        self.assertEqual(len(groups), 5)
        self.assertEqual(groups[1]["shift_ids"], ["SH-2"])
        self.assertEqual(groups[3]["shift_ids"], ["SH-4", "SH-5"])

    def test_normalisation_guard(self):
        shifts = [Shift("SH-1", "2026-10-10", "MORNING", "09:00:00", "PAPER-01")]
        groups = [{"group_id": "GRP-1", "shift_ids": ["SH-1"]}]

        # All candidates identical score -> denom = 0 -> guard NO_NORMALISATION
        scorecards = {
            f"RN-{i}": ScoreCard(f"RN-{i}", "SH-1", 10.0, 10.0, 10.0, 10.0, 50, 40, 10,
                                 40.0, 0, 0, 40.0, None, "QUALIFIED", "")
            for i in range(10)
        }
        stats, _ = compute_shift_normalisation(scorecards, shifts, groups, top_fraction_pct=0.10)
        self.assertEqual(stats[0].normalisation_flag, "NO_NORMALISATION")
        for sc in scorecards.values():
            self.assertEqual(sc.normalised, 40.0)


if __name__ == "__main__":
    unittest.main()
