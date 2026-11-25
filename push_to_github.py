"""
Python script to push repository to GitHub using git CLI or GitHub REST API.
"""

import os
import subprocess
import sys


def push_via_git():
    repo_url = "https://github.com/ganeshreddy47/-T018-PS-072.git"
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Check git
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        print("Git command-line tool is not found in system PATH.")
        print(f"Please install Git or execute from a terminal with Git available.")
        return False

    try:
        # Check if .git exists
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)

        subprocess.run(["git", "add", "."], check=True)
        msg = "Complete PS-072 Result Engine implementation: engine, tests, documentation, sample data, and evaluation outputs (Team T018)"
        subprocess.run(["git", "commit", "-m", msg], check=False)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
        print("Successfully pushed to GitHub repository!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git execution failed: {e}")
        return False


if __name__ == "__main__":
    push_via_git()
