"""Windows/VS Code handoff entrypoint. All private state is Git ignored."""
import argparse
import json
from pathlib import Path
from safeshift.kaggle_handoff import Session, Train3763Operator, prepare, operate, invoke_agy, accept_report
from safeshift.pilot.artifacts import read


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "handoff", "resume", "step", "report"))
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--request", type=Path)
    p.add_argument("--action", choices=("start", "collect"))
    p.add_argument("--recover", action="store_true")
    p.add_argument("--synthetic", action="store_true")
    a = p.parse_args(argv)
    if a.command == "prepare":
        if not a.request:
            p.error("--request required")
        session = prepare(a.directory, read(a.request))
        result = {"status": "PREPARED", "binding": session.binding}
    else:
        session = Session(a.directory)
        if a.command in ("handoff", "resume"):
            result = invoke_agy(session, resume=a.command == "resume", recover=a.recover)
        elif a.command == "step":
            if not a.action:
                p.error("--action required")
            operator = Train3763Operator()
            if a.synthetic:
                from scripts.rehearse_kaggle_handoff import SyntheticOperator
                if session.request["scope"] != "SYNTHETIC_ONLY":
                    p.error("synthetic operator requires SYNTHETIC_ONLY request")
                operator = SyntheticOperator(session.root)
            elif session.request["scope"] == "SYNTHETIC_ONLY":
                p.error("synthetic scope cannot use real Kaggle")
            result = operate(session, operator, a.action)
        else:
            result = accept_report(session)
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] in ("FAIL", "BLOCKED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
