"""Validate pinned Qwen configuration offline; report statuses without env values."""

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from safeshift.protocol.qwen_config import resolve_qwen_configuration
from safeshift.protocol.schema import strict_json


class _StatusOnlyParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "QWEN_CONFIG_INVALID: use environment variables; no CLI configuration accepted\n")


def main(argv=None, *, repo=REPO):
    parser = _StatusOnlyParser(description=__doc__)
    parser.parse_args(argv)
    try:
        config = strict_json((repo / "configs/pre_freeze/providers.json").read_bytes())
        resolved = resolve_qwen_configuration(config["providers"]["qwen_dashscope"])
    except (ValueError, OSError, TypeError, KeyError):
        # JSON errors and malicious config values must never reach stderr.
        print("QWEN_CONFIG_INVALID: check pinned policy and workspace environment configuration",
              file=sys.stderr)
        return 2
    print(json.dumps(resolved.report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
