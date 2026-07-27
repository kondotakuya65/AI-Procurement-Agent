"""CLI: python -m app.eval.cli"""

from __future__ import annotations

import json
import sys

from app.config import clear_settings_cache
from app.eval.runner import run_all_golden


def main() -> int:
    clear_settings_cache()
    reports = run_all_golden()
    passed = sum(1 for r in reports if r["passed"])
    failed = len(reports) - passed
    print(json.dumps({"passed": passed, "failed": failed, "reports": reports}, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
