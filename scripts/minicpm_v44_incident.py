"""Read-only V4-4 custody preparation; source rebind requires a fresh release.

No submit, publication, production journal append or model imports in this CLI.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import tempfile
from contextlib import contextmanager
from types import SimpleNamespace

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, sha, safe
from safeshift.pilot.contract import digest
from safeshift.fulltrain import minicpm_incident as incident, minicpm_release as a
from scripts import minicpm_fulltrain_transport as transport


def prefix(events):
    require([e["kind"] for e in events] == ["REGISTERED", "RESERVED", "RESTART_BOUND",
        "PENDING_RESERVED", "PENDING_PUBLISH_INTENT", "PENDING_PUBLISHED"], "MINICPM_V44_EXACT_JOURNAL_PREFIX")
    binding, active = events[2]["payload"], deepcopy(events[3]["payload"])
    require(binding["grant_sha256"] == incident.PREVIOUS_GRANT
        and digest(active["ticket"]) == incident.PREVIOUS_TICKET and digest(active["value"]) == incident.PREVIOUS_VALUE
        and all(e["payload"]["ticket_sha256"] == incident.PREVIOUS_TICKET for e in events[4:]),
        "MINICPM_V44_JOURNAL_BINDING")
    require(active["ticket"]["payload"]["previous_event_sha256"] == events[3]["previous"]
        and active["ticket"]["payload"]["reserved_after"] == incident.RESERVED, "MINICPM_V44_UNCHANGED_HOLD")
    active.update(locator=binding["locator"], journal_head_sha256=digest(events[-1]))
    return active


def output_names(selected):
    import re
    archives = [n for n in selected if re.fullmatch(r"minicpm-fulltrain/supervision/[0-9a-f]{32}\.zip", n)]
    require(len(archives) == 1 and set(selected) == {archives[0], archives[0] + ".sha256.json"},
        "MINICPM_V44_SUPERVISOR_ONLY_INVENTORY_REQUIRED")
    return archives[0]


def inventory(client, value):
    """Reuse the reviewed exhaustive paginator and retain ALL metadata names.

    The shared collector intentionally returns ZIPs only. Incident closure also
    needs to reject any unpacked attempt/native evidence outside that pair.
    """
    from scripts.reconcile_train3763_manual import output_inventory
    names = []
    class RecordingClient:
        @contextmanager
        def build_kaggle_client(self):
            with client.build_kaggle_client() as remote:
                def listing(query):
                    result = remote.kernels.kernels_api_client.list_kernel_session_output(query)
                    names.extend(f.file_name for f in result.files)
                    return result
                yield SimpleNamespace(_http_client=remote._http_client,
                    kernels=SimpleNamespace(kernels_api_client=SimpleNamespace(list_kernel_session_output=listing)))
    selected, log = output_inventory(RecordingClient(), value["job"], 1)
    validate_inventory(names, value, output_names(selected))
    return selected, log, sorted(names)


def validate_inventory(names, value, archive):
    import re
    require(type(names) is list and 1 <= len(names) <= 16384 and len(names) == len(set(names)),
        "MINICPM_V44_EXHAUSTIVE_INVENTORY")
    control = archive.removesuffix(".zip") + "/"
    allowed_control = {"admit-process.json", "admit.log", "admit/failure.json", "capability.json", "checksums.json",
        "claims.json", "failure.json", "final_timing.json", "release.json", "request.json", "retention.json"}
    exact = {archive, archive + ".sha256.json", value["request"]["plan"]["run_id"] + "-release-context.json",
        *(control + n for n in allowed_control),
        "minicpm-fulltrain-claims/mcpm4-restart-v1/4/launch.json",
        "minicpm-fulltrain-claims/mcpm4-restart-v1/4/admit.json"}
    source = "data/processed/fresh_fulltrain_code/" + incident.PREVIOUS_SOURCE + "/"
    for name in names:
        from safeshift.pilot.artifacts import relative
        relative(name)
        require(name in exact or name.startswith(source) and (name.endswith((".py", ".json", ".txt"))
            or re.fullmatch(r"(?:[A-Za-z0-9_]+/)+__pycache__/[A-Za-z0-9_]+\.cpython-313\.pyc", name[len(source):]))
            or re.fullmatch(r"minicpm-fulltrain(?:/supervisor_control|\-claims/mcpm4-restart-v1/4)/attempts/active_[0-9a-f]{64}\.lock", name),
            "MINICPM_V44_UNEXPECTED_OUTPUT_NATIVE_AMBIGUITY")
    require({archive, archive + ".sha256.json"} <= set(names), "MINICPM_V44_REMOTE_PAIR_REQUIRED")


def verify_evidence(directory, previous, *, online=False, client=None):
    from scripts.reconcile_train3763_manual import observe_kernel
    from safeshift.internvl3763_operator import api, code_hash
    directory = Path(directory)
    value, ticket = previous["value"], previous["ticket"]
    require(read(directory / "value.json") == value and read(directory / "ticket.json") == ticket,
        "MINICPM_V44_EVIDENCE_PACKAGE")
    notebook = read(directory / "notebook.ipynb")
    require(code_hash(notebook) == ticket["payload"]["notebook_code_sha256"], "MINICPM_V44_NOTEBOOK_PIN")
    zip_inventory = read(directory / "inventory.json")
    name = output_names(zip_inventory)
    full_inventory = read(directory / "full-inventory.json")
    validate_inventory(full_inventory, value, name)
    archive = safe(directory / "provider", name)
    provider = read(directory / "provider.json")
    result = incident.verify_supervisor(value, ticket, archive, provider)
    result.update(provider_log_sha256=sha(directory / "provider.log"), output_names=sorted(zip_inventory),
        journal_head_sha256=previous["journal_head_sha256"], full_inventory_sha256=digest(full_inventory))
    if online:
        client = api() if client is None else client
        observed = observe_kernel(client, value["job"], 1, notebook, value["input_sources"],
            expected_state=provider["state"], kernel_id=provider["kernel_id"])
        require(observed == provider, "MINICPM_V44_PROVIDER_CHANGED")
        selected, log, names = inventory(client, value)
        require(output_names(selected) == name and log.encode() == (directory / "provider.log").read_bytes(),
            "MINICPM_V44_REMOTE_INVENTORY_OR_LOG_CHANGED")
        require(names == full_inventory, "MINICPM_V44_REMOTE_FULL_INVENTORY_CHANGED")
        with tempfile.TemporaryDirectory() as tmp:
            transport.download_selected(selected, {name: 64 * 2**20, name + ".sha256.json": 4096}, tmp)
            require(sha(Path(tmp) / name) == result["supervisor_sha256"], "MINICPM_V44_REMOTE_ARCHIVE_CHANGED")
            incident.verify_supervisor(value, ticket, Path(tmp) / name, observed)
    return result


def prepare(directory, *, operator=None, client=None, reader=None):
    from scripts.minicpm_fulltrain_recovery import RecoveredSerialJournal
    from scripts.reconcile_train3763_manual import observe_kernel
    from safeshift.internvl3763_operator import api
    from scripts.submit_internvl_v2 import bounded_http
    operator = RecoveredSerialJournal() if operator is None else operator
    previous = prefix(operator.events())
    old = incident.previous_release(a.github_get if reader is None else reader, previous["locator"])
    a.verify_signature(old["public_key"], previous["ticket"]["payload"], previous["ticket"]["signature"])
    package = safe(ROOT, previous["package"])
    client = api() if client is None else client
    with bounded_http():
        state = str(client.kernels_status(incident.JOB + "/1").status).split(".")[-1]
    require(state in ("COMPLETE", "ERROR"), "MINICPM_V44_TERMINAL_REQUIRED")
    notebook = read(package / "notebook.ipynb")
    provider = observe_kernel(client, incident.JOB, 1, notebook, previous["value"]["input_sources"], expected_state=state)
    selected, log, names = inventory(client, previous["value"])
    name = output_names(selected)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write(directory / "provider.json", provider)
    write(directory / "inventory.json", sorted(selected))
    write(directory / "full-inventory.json", names)
    write(directory / "value.json", previous["value"])
    write(directory / "ticket.json", previous["ticket"])
    write(directory / "notebook.ipynb", notebook)
    from safeshift.pilot.artifacts import write_bytes
    write_bytes(directory / "provider.log", log.encode())
    transport.download_selected(selected, {name: 64 * 2**20, name + ".sha256.json": 4096}, directory / "provider")
    report = verify_evidence(directory, previous)
    write(directory / "verification.json", report)
    require(prefix(operator.events()) == previous, "MINICPM_V44_JOURNAL_CHANGED_DURING_READ")
    return report


def repair_template(grant, previous, closure, directive):
    """Unsigned source-transition proposal; no approval/signature is invented."""
    from safeshift.fulltrain.minicpm_recovery import locator
    locator(directive)
    require(directive["comment_id"] == incident.DIRECTIVE, "MINICPM_EXACT_REPAIR_DIRECTIVE")
    grant = deepcopy(grant)
    grant["implementation_pr"] = None  # exact new Draft PR number is filled before review
    grant["repair"] = {"schema": incident.SCHEMA, "directive": directive,
        "previous_release": previous["locator"], "previous_ticket": previous["ticket"],
        "journal_head_sha256": previous["journal_head_sha256"], "closure_sha256": digest(closure),
        "reserved_after": deepcopy(incident.RESERVED)}
    return grant


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = prepare(args.output)
    print(result["disposition"], "reservation retained; no journal append")


if __name__ == "__main__":
    main()
