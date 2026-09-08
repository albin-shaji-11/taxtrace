"""Generate the TaxTrace dataset.

    python scripts/generate_data.py                 # 50,000 rows
    python scripts/generate_data.py --rows 20000    # smaller, faster
    python scripts/generate_data.py --seed 42       # a different universe

Re-running with the same seed reproduces exactly the same data. That property
is called determinism and it is what makes a test suite trustworthy.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from taxtrace.datagen.build import generate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=20260908)
    ap.add_argument("--out", default=str(ROOT / "data"))
    a = ap.parse_args()

    summary = generate(Path(a.out), n_rows=a.rows, seed=a.seed)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
