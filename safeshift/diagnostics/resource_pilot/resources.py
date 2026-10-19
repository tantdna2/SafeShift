"""Sample process-tree RSS and filesystem occupancy; expose sampling limitations."""
from pathlib import Path
import shutil
import statistics
import subprocess
import threading
import time


def tree_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file() and not p.is_symlink())


def process_tree_rss():
    # Linux /proc fields, no psutil/package dependency and no model/data reads.
    import os
    records = {}
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            fields = (p / "stat").read_text().rsplit(")", 1)[1].split()
            records[int(p.name)] = (int(fields[1]), int(fields[21]) * os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, IndexError):
            continue  # process exit race; sampling coverage is explicitly partial
    family = {os.getpid()}
    while True:
        expanded = family | {pid for pid, (parent, _) in records.items() if parent in family}
        if expanded == family:
            break
        family = expanded
    return sum(records[p][1] for p in family if p in records)


def gpu_memory():
    raw = subprocess.check_output(["nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader,nounits"],
                                  text=True, timeout=5, stderr=subprocess.DEVNULL)
    return {int(i.strip()): int(m.strip()) * 2**20 for i, m in
            (line.split(",") for line in raw.strip().splitlines())}


class Sampler:
    def __init__(self, roots, interval=0.5, observe_rss=process_tree_rss, observe_gpu=lambda: {}):
        self.roots = {k: Path(v) for k, v in roots.items()}
        self.interval, self.observe_rss = interval, observe_rss
        self.observe_gpu, self.gpu_peaks = observe_gpu, {}
        self.peak_rss, self.samples, self.errors = 0, 0, []
        self.disks = {}
        self.stop_event = threading.Event()
        self.thread = None

    def sample(self):
        try:
            self.peak_rss = max(self.peak_rss, self.observe_rss())
            for name, path in self.roots.items():
                d = shutil.disk_usage(path)
                row = self.disks.setdefault(name, {"initial_used_bytes": d.used, "peak_used_bytes": d.used,
                                                   "min_free_bytes": d.free, "total_bytes": d.total})
                row["peak_used_bytes"] = max(row["peak_used_bytes"], d.used)
                row["min_free_bytes"] = min(row["min_free_bytes"], d.free)
            for device, used in self.observe_gpu().items():
                key = str(device)
                self.gpu_peaks[key] = max(self.gpu_peaks.get(key, 0), used)
            self.samples += 1
        except Exception as e:
            if type(e).__name__ not in self.errors:
                self.errors.append(type(e).__name__)

    def start(self):
        self.sample()
        def loop():
            while not self.stop_event.wait(self.interval):
                self.sample()
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def finish(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.sample()
        return {"process_tree_peak_rss_bytes": self.peak_rss if self.samples else None,
                "sampled_device_peak_used_bytes": self.gpu_peaks,
                "disks": self.disks, "samples": self.samples, "sampling_seconds": self.interval,
                "errors": self.errors, "coverage": "PARTIAL_SAMPLED",
                "limitations": "Short spikes, exited children and other filesystem users are not attributable; filesystem roots may share a device."}


def projection(rows, setup_seconds=0):
    complete = [r["seconds"] for r in rows if r["status"] == "SUCCESS" and r.get("seconds") is not None]
    attempted = [r["seconds"] for r in rows if r.get("seconds") is not None]
    mean = statistics.mean(complete) if complete else None
    median = statistics.median(complete) if complete else None
    return {"planned": 8, "attempted": len(attempted), "successful": len(complete),
        "observed_attempt_seconds": sum(attempted), "success_mean_seconds_per_image": mean,
        "success_median_seconds_per_image": median,
        "mean_images_per_second": 1 / mean if mean and mean > 0 else None,
        "median_images_per_second": 1 / median if median and median > 0 else None,
        "estimate_941_seconds": setup_seconds + 941 * mean if mean is not None else None,
        "observed_range_scenario_941_seconds": [setup_seconds + 941 * min(complete), setup_seconds + 941 * max(complete)] if complete else None,
        "sample_stdev_seconds": statistics.stdev(complete) if len(complete) > 1 else None,
        "estimate_status": "ILLUSTRATIVE_COMPLETE_PILOT" if len(complete) == 8 else "CENSORED_PARTIAL_NOT_FEASIBILITY",
        "uncertainty": "Fixed first eight are nonrandom; range is not a confidence/prediction interval. Failure censoring, image complexity, warmup, thermal drift, disk growth and venue limits invalidate guarantees. CPU replay/export must be added separately; no worst-case bound."}


def timed(path, callback, clock=time.monotonic):
    from ..one_click.artifacts import write
    start, status = clock(), "FAILED"
    try:
        value = callback()
        status = "RETURNED"
        return value
    finally:
        write(path, {"seconds": clock() - start, "status": status})
