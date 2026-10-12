"""Pending PA3 execution authority. Checksums never grant research rights.

A later Research Lead decision and audited implementation must replace these
closed gates with exact source/run/cohort/owner checks. There is deliberately
no receipt, environment variable, callable injection or boolean unlock.
"""

def require(operation, settings=None):
    if operation == "test":
        raise PermissionError("PA3_TEST_LOCKED")
    if operation not in {"technical", "metadata", "images", "train-dev", "train-holdout", "statistics"}:
        raise PermissionError("PA3_UNKNOWN_RIGHT")
    raise PermissionError("PA3_" + operation.upper().replace("-", "_") +
                          "_LOCKED_PENDING_RESEARCH_LEAD_AND_AUDITED_AUTHORITY")
