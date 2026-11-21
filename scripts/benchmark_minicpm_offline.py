"""Profile V5 and the fast companion against identical synthetic V5 snapshots.

Run from repo root with python -B -m scripts.benchmark_minicpm_offline.
Fixture generation (including the scripted backend) and snapshot copies are
outside the timers. No provider, real inputs, inference or production paths.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from unittest.mock import patch
import zipfile

from safeshift.pilot import artifacts
from safeshift.pilot.contract import digest
from scripts import minicpm_offline_fast as fast

v5 = fast.v5
BATCHES = (100, 361, 347, 400, 400, 392, 450, 450, 450, 413)
CASES = (808, 2000, 3763)


def is_zip(path):
    return isinstance(path, (str, os.PathLike)) and (
        str(path).endswith(".zip") or (Path(path).name.startswith("ancestor-") and str(path).endswith(".bin")))


class MeasuredFile:
    def __init__(self, stream, key, counts):
        self.stream, self.key, self.counts = stream, key, counts

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def read(self, *args):
        result = self.stream.read(*args)
        self.counts[self.key] += len(result)
        return result

    def readinto(self, buffer):
        count = self.stream.readinto(buffer)
        self.counts[self.key] += count or 0
        return count


def timed(operation, new_plan=None, expected_error=None):
    counters = Counter({name: 0 for name in ("zip_opens", "zip_file_bytes", "zip_member_bytes",
        "sha256", "file_sha256", "historical_replays", "incoming_replays")})
    sha256, file_sha = hashlib.sha256, artifacts.sha
    io_open = io.open
    zip_init, member_read, recover = zipfile.ZipFile.__init__, zipfile.ZipExtFile.read, fast.runtime.recover

    def count_hash(*args, **kwargs):
        counters["sha256"] += 1
        return sha256(*args, **kwargs)

    def count_file_hash(path):
        counters["file_sha256"] += 1
        return file_sha(path)

    def wrap(stream, path, mode):
        return MeasuredFile(stream, "zip_file_bytes", counters) if "r" in mode and is_zip(path) else stream

    def instrument_io(path, mode="r", *args, **kwargs):
        # Path.open and ZipFile both call io.open.
        return wrap(io_open(path, mode, *args, **kwargs), path, mode)

    def init_zip(self, file, mode="r", *args, **kwargs):
        if mode == "r":
            counters["zip_opens"] += 1
        return zip_init(self, file, mode, *args, **kwargs)

    def read_member(self, *args):
        data = member_read(self, *args)
        counters["zip_member_bytes"] += len(data)
        return data

    def replay(root, cohort, plan_sha):
        counters["incoming_replays" if plan_sha == new_plan else "historical_replays"] += 1
        return recover(root, cohort, plan_sha)

    with ExitStack() as stack:
        # Both hashlib and its file helper are counted. The latter is a subset.
        for module in tuple(sys.modules.values()):
            if module and getattr(module, "__name__", "").startswith(("safeshift.", "scripts.")):
                if getattr(module, "sha", None) is file_sha:
                    stack.enter_context(patch.object(module, "sha", count_file_hash))
        stack.enter_context(patch.object(hashlib, "sha256", count_hash))
        stack.enter_context(patch.object(io, "open", instrument_io))
        stack.enter_context(patch.object(zipfile.ZipFile, "__init__", init_zip))
        stack.enter_context(patch.object(zipfile.ZipExtFile, "read", read_member))
        stack.enter_context(patch.object(fast.runtime, "recover", replay))
        started = time.perf_counter()
        try:
            result = operation()
        except ValueError as error:
            if str(error) != expected_error:
                raise
            result = {"status": "EXPECTED_FINISHED_STOP"}
        else:
            if expected_error is not None:
                raise AssertionError("Completed campaign did not stop")
        counters["seconds"] = round(time.perf_counter() - started, 4)
    return result, dict(counters)


def snapshot(route, location):
    location.mkdir()
    for source, name in ((route.root, "primary"), (route.mirror, "mirror")):
        shutil.copytree(source, location / name)


def compare(fixture, route, new, total, measured_gate, assertion):
    scratch = fixture.root / ("snapshot-" + str(total))
    snapshot(route, scratch)
    clocks, observations = {}, {}
    plan_sha = digest(route.state()["active"]["value"]["request"]["plan"])
    for mode in ("v5", "fast"):
        saved = []
        for folder, name in ((route.root, "primary"), (route.mirror, "mirror")):
            parked = scratch / ("parked-" + name)
            folder.rename(parked)
            shutil.copytree(scratch / name, folder)
            saved.append((folder, parked, name))
        try:
            make_route = (lambda: v5.Continuation(route.root)) if mode == "v5" else fixture.released_route
            result, startup = timed(make_route)
            variant = result
            accept = (lambda: variant.accept(*new, fixture.proof)) if mode == "v5" else (
                lambda: fixture.accept_fast(variant, new))
            observations[mode], clocks[mode] = {}, {"open": startup}
            operations = {"state": variant.state, "accept": accept, "forecast": variant.forecast,
                "stage": lambda: variant.stage(
                    fixture.key, measured_gate | {"observed_unix": int(time.time())}, fixture.proof), "export-active": variant.export_active}
            terminal_errors = {
                "forecast": "MINICPM_FORECAST_ACTIVE_STOP_FINAL_OR_FINISHED",
                "stage": "MINICPM_ACTIVE_STOP_FINAL_OR_FINISHED",
                "export-active": "MINICPM_NO_RECOVERABLE_ACTIVE_JOB",
            } if total == 3763 else {}
            for label, operation in operations.items():
                if mode == "v5" and label == "export-active":
                    def operation():
                        with v5.lock(variant.root):
                            return variant.export_active()
                result, counters = timed(operation, new_plan=plan_sha if label == "accept" else None,
                    expected_error=terminal_errors.get(label))
                clocks[mode][label] = counters
                if label == "state":
                    result = {key: result[key] for key in ("counts", "reserved", "next_ordinal", "status")}
                if label == "accept":
                    event = artifacts.read(sorted(variant.root.glob("event-*.json"))[-1])
                    result = result | {"verification": event["payload"]["verification"]}
                if label == "forecast" and "grant_capacity" in result:
                    result = {key: value for key, value in result.items() if key != "grant_capacity"}
                observations[mode][label] = result
                print(f"{total:4d} {mode:4s} {label:13s} {json.dumps(counters)}", flush=True, file=sys.stderr)
        finally:
            for folder, parked, name in saved:
                folder.rename(scratch / (mode + "-" + name))
                parked.rename(folder)
    assertion(observations["v5"], observations["fast"])
    return clocks


def compare_completed(fixture, count):
    """Time a completed snapshot independently of the five-command profile."""
    original = v5.Continuation(fixture.route.root)
    expected, before = timed(original.state)
    actual, after = timed(fixture.released_route().state)
    fixture.assertEqual(actual, expected)
    fixture.assertEqual(actual["next_ordinal"], count)
    for label, values in (("v5", before), ("fast", after)):
        print(f"{count:4d} {label:4s} completed-state {json.dumps(values)}", flush=True, file=sys.stderr)
    return {"v5": {"completed-state": before}, "fast": {"completed-state": after}}


def prepare_outputs(fixture):
    """Reuse fixed request digests while building the untimed synthetic input."""
    state = fixture.route.state()
    value, ticket = state["active"]["value"], state["active"]["ticket"]
    request = value["request"]
    fixed = [(item, digest(item)) for item in (value, ticket, request, request["plan"])]

    def fixture_digest(item):
        for original, checksum in fixed:
            if item is original:
                return checksum
        return digest(item)

    with patch.object(fixture.route, "state", return_value=state), \
            patch.object(fast.runtime, "digest", fixture_digest), \
            patch.object(v5.a, "digest", fixture_digest):
        outputs = fixture.outputs(invalid=False)
    fixture.assertEqual([digest(item) for item, _ in fixed], [checksum for _, checksum in fixed])
    return outputs


def run(case, *, completed_only=False):
    # Test fixtures are local and keep their own ignored temporary custody.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from test_minicpm_offline_fast import FastTests

    fixture = FastTests()
    clocks = {}
    FastTests.setUpClass()
    try:
        # Skip the subclass's two-call convenience reservation. The benchmark
        # signs V5 tickets at the desired sample counts.
        super(FastTests, fixture).setUp()
        fixture.grant["sizing"]["first_call_seconds"] = 1
        fixture.initialize_serial9()
        fixture.legacy_route = fixture.route
        propose = v5.policy.proposal
        total = 0
        batches = (BATCHES[0], case - BATCHES[0]) if completed_only else BATCHES
        for calls in batches:
            def bounded(*args):
                envelope = propose(*args)
                assert calls <= envelope["calls"], (calls, envelope)
                return envelope | {"calls": calls}
            with patch.object(v5.policy, "proposal", bounded):
                fixture.stage()
            if total == 0:
                fixture.route = fixture.released_route()
            next_total = total + calls
            # Outputs have a full 3763-ID cohort, valid sealed ZIPs, real RSA
            # signatures and raw parser checks. The stock test backend is CPU.
            print(f"preparing {next_total} completed synthetic IDs", flush=True, file=sys.stderr)
            outputs = prepare_outputs(fixture)
            if not completed_only and next_total in CASES and case in (0, next_total):
                active_state = fixture.route.state()
                sample = active_state["active"]["ticket"]["payload"]["owner_gate"]
                gate = deepcopy(sample)
                name = fixture.grant["campaign_id"] + "-" + str(active_state["reserved"]["jobs"] + 1)
                gate.update(observed_unix=int(time.time()), job="nguynanhtn/safeshift-minicpm-" + name)
                gate["inputs"]["dataset_sources"][-1] = "nguynanhtn/safeshift-minicpm-capsule-" + name + "/1"
                clocks[next_total] = compare(fixture, fixture.route, outputs, next_total, gate, fixture.assertEqual)
            if not completed_only and (case == next_total or next_total == CASES[-1]):
                break
            try:
                receipt = fixture.accept_fast(fixture.route, outputs)
            except ValueError as error:
                # Fixtures contain only generated, non-sensitive data.
                if error.__context__ is not None:
                    raise RuntimeError("Synthetic fixture preparation failed") from error.__context__
                raise
            expected = {"SUCCESS": next_total}
            if next_total < 3763:
                expected["NOT_ATTEMPTED"] = 3763 - next_total
            fixture.assertEqual(receipt["counts"], expected)
            total = next_total
        if completed_only:
            clocks[case] = compare_completed(fixture, case)
    finally:
        fixture.doCleanups()
        FastTests.tearDownClass()
    return clocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=int, choices=(0, *CASES), default=0, help="0 profiles all milestones")
    parser.add_argument("--completed-only", action="store_true",
        help="profile the exact same completed journal with two serials, without the additional command timings")
    args = parser.parse_args()
    if args.completed_only and args.case == 0:
        parser.error("--completed-only requires a nonzero --case")
    print(json.dumps({"platform": platform.platform(), "python": platform.python_version(),
        "fixture": "SYNTHETIC_ONLY", "batches": (BATCHES[0], args.case - BATCHES[0]) if args.completed_only else BATCHES,
        "results": run(args.case, completed_only=args.completed_only)}, indent=2))


if __name__ == "__main__":
    main()
