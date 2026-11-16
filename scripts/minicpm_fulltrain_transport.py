"""First MiniCPM collection using the existing reviewed SDK/URL/HTTP guards."""
import os
from pathlib import Path
import re
import shutil
import time

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import read, write_bytes, safe, sha
from scripts import reconcile_train3763_manual as manual


def fetch_outputs(client, value, destination, archive_limit):
    """Discover both unique ZIP pairs after COMPLETE; retain every partial byte."""
    selected, log = manual.output_inventory(client, value["job"], 1)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    write_bytes(destination / "provider.log", log.encode())
    attempt = "minicpm-fulltrain/" + value["request"]["plan"]["run_id"] + ".zip"
    candidates = [n for n in selected if re.fullmatch(r"minicpm-fulltrain/supervision/[0-9a-f]{32}\.zip", n)]
    require(len(candidates) == 1, "MINICPM_ONE_SUPERVISOR_ZIP")
    supervisor = candidates[0]
    expected = {attempt: archive_limit, supervisor: archive_limit, attempt + ".sha256.json": 4096,
        supervisor + ".sha256.json": 4096}
    require(set(selected) == set(expected), "MINICPM_EXACT_TWO_OUTPUT_PAIRS")
    for name in expected:
        manual.validate_output_url(selected[name].url, name)
    require(shutil.disk_usage(destination).free > sum(expected.values()) + 2**20, "MINICPM_DOWNLOAD_SPACE")
    deadline = time.monotonic() + 240
    for name, limit in expected.items():
        remaining = deadline - time.monotonic()
        require(remaining > 0, "MINICPM_DOWNLOAD_DEADLINE")
        with manual.private_transport_logs(), manual.anonymous_output_session(deadline) as http:
            with http.get(selected[name].url, stream=True, allow_redirects=False,
                    timeout=(min(10, remaining / 2), min(30, remaining / 2)), headers={"Accept-Encoding": "identity"}) as response:
                require(response.status_code == 200 and response.headers.get("Content-Encoding", "identity") == "identity",
                    "MINICPM_DOWNLOAD_STATUS_ENCODING")
                length = response.headers.get("Content-Length")
                require(length is None or re.fullmatch(r"[0-9]+", length) and int(length) <= limit, "MINICPM_DOWNLOAD_SIZE")
                target = safe(destination, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    total = 0
                    try:
                        for chunk in response.iter_content(65536):
                            total += len(chunk)
                            require(total <= limit and time.monotonic() < deadline, "MINICPM_DOWNLOAD_DEADLINE_SIZE")
                            stream.write(chunk)
                        require(time.monotonic() < deadline and (length is None or int(length) == total), "MINICPM_DOWNLOAD_INCOMPLETE")
                    finally:
                        stream.flush(); os.fsync(stream.fileno())
    for name in (attempt, supervisor):
        require(sha(destination / name) == read(destination / (name + ".sha256.json"))["sha256"], "MINICPM_PROVIDER_ZIP_SHA")
    return destination / attempt, destination / supervisor
