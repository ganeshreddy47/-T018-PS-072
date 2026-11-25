"""
Main entry point for PS-072 Online Exam Proctoring Result Engine.
Executes the command-driven result engine and exports official evaluation files.
"""

import argparse
import os
import sys

# Ensure src is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.engine import ExamResultEngine


def main():
    parser = argparse.ArgumentParser(
        description="PS-072 Online Exam Proctoring Result Engine (Team T018)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "sample_data", "T018-PS-072-sample-data"),
        help="Path to the directory containing input CSV files"
    )
    parser.add_argument(
        "--commands",
        type=str,
        default=None,
        help="Path to commands.txt file (defaults to commands.txt inside data-dir)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "output"),
        help="Directory to export the 4 official evaluation CSV files"
    )

    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    commands_path = os.path.abspath(args.commands) if args.commands else os.path.join(data_dir, "commands.txt")
    output_dir = os.path.abspath(args.output_dir)

    print("=" * 70)
    print("  PS-072 ONLINE EXAM PROCTORING RESULT ENGINE")
    print("  Team ID: T018 | Section: CSDS A")
    print("  Members: K GANESH REDDY (1AT24CD036), KATTE SHREYAS (1AT24CD037)")
    print("=" * 70)
    print(f"Data Directory:    {data_dir}")
    print(f"Commands File:     {commands_path}")
    print(f"Output Directory:  {output_dir}")
    print("=" * 70)

    engine = ExamResultEngine(data_dir=data_dir)
    print("\n[Step 1/3] Ingesting exam structure, candidates, and responses...")
    engine.load_data()
    print(f"  Loaded {len(engine.candidates)} candidates across {len(engine.shifts)} shifts.")
    print(f"  Formed {len(engine.shift_groups)} normalisation groups.")

    print("\n[Step 2/3] Executing commands in sequence...")
    engine.execute_commands_file(commands_path)

    print("\n[Step 3/3] Exporting evaluation CSV files...")
    engine.export_csv_outputs(output_dir)

    print("\nExecution completed successfully!")


if __name__ == "__main__":
    main()
