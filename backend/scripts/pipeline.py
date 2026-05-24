"""
Lumen Pipeline - One command to run them all.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

STEPS = [
    ("quick_indexer.py",      "Index agents from IdentityRegistry"),
    ("decode_agents.py",      "Decode agent metadata"),
    ("cluster_detector.py",   "Detect sybil clusters"),
    ("reputation_indexer.py", "Index feedback from ReputationRegistry"),
    ("inspect_safe_agents.py","Inspect SAFE agents"),
]


def run_step(script: str, description: str, index: int, total: int) -> bool:
    print(f"\n{'=' * 70}")
    print(f"[{index}/{total}] {description}")
    print(f"    Running: {script}")
    print(f"{'=' * 70}\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)],
        cwd=SCRIPTS_DIR.parent,
    )
    if result.returncode != 0:
        print(f"\n[FAIL] {script} exited with code {result.returncode}")
        return False
    return True


def main():
    print("=" * 70)
    print("Lumen Pipeline - Full Indexing Run")
    print("=" * 70)

    for i, (script, desc) in enumerate(STEPS, 1):
        if not run_step(script, desc, i, len(STEPS)):
            print("\nPipeline stopped due to error.")
            sys.exit(1)

    print("\n" + "=" * 70)
    print("Pipeline complete - all 5 steps succeeded")
    print("=" * 70)


if __name__ == "__main__":
    main()