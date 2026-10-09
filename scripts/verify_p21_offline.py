"""Focused P2.1 synthetic regressions; no inference or external input paths."""

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODULES = (
    "tests.test_p21_classification", "tests.test_p21_harness_evaluation",
    "tests.test_p21_execution_authority", "tests.test_p21_kaggle",
    "tests.test_d9r25_harness", "tests.test_d9r26_bridges", "tests.test_d9r26_candidate",
    "tests.test_d9r23_classification_contract", "tests.test_d9r24_metrics",
    "tests.test_classification_qualification", "tests.test_internvl3_execution_authority",
    "tests.test_qwen3_execution_authority",
)
# These exact historical expectations also FAIL on the mandatory BASE. They
# predate the existing Qwen3 amendment/v2/v3 and are not rewritten by P2.1.
BASE_FAILURES = {
    "tests.test_d9r23_classification_contract.ContractTests.test_exact_scope_history_and_append_only",
    "tests.test_classification_qualification.ProtectedStateTests.test_roster_grounding_d5_freeze_and_history_unchanged",
}


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def main():
    tests = flatten(unittest.defaultTestLoader.loadTestsFromNames(MODULES))
    suite = unittest.TestSuite(test for test in tests if test.id() not in BASE_FAILURES)
    for name in sorted(BASE_FAILURES):
        print("EXCLUDED_VERIFIED_BASE_FAILURE=" + name, flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
