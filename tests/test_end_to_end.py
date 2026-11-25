"""End-to-end integration test verifying full run and CSV output files."""

import os
import unittest
from src.engine import ExamResultEngine


class TestEndToEnd(unittest.TestCase):
    def test_full_pipeline_run(self):
        base_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "sample_data", "T018-PS-072-sample-data"
        ))
        output_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "output"
        ))
        commands_path = os.path.join(base_dir, "commands.txt")

        engine = ExamResultEngine(data_dir=base_dir)
        engine.load_data()
        engine.execute_commands_file(commands_path)
        engine.export_csv_outputs(output_dir)

        # Assert output files exist and are non-empty
        for fname in ["scorecards.csv", "shift_stats.csv", "merit_list.csv", "category_cutoffs.csv"]:
            fpath = os.path.join(output_dir, fname)
            self.assertTrue(os.path.exists(fpath), f"File {fname} does not exist.")
            self.assertGreater(os.path.getsize(fpath), 0, f"File {fname} is empty.")

        # Check merit list count
        self.assertEqual(len(engine.merit_list), 1483)
        # Check category cut-offs count
        self.assertEqual(len(engine.category_cutoffs), 5)


if __name__ == "__main__":
    unittest.main()
