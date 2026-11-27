"""Local CT1 preparation. Outputs separate runner inputs from private scoring custody."""

from argparse import ArgumentParser
from collections import Counter
from io import BytesIO
from pathlib import Path
import re
from secrets import token_bytes
import subprocess
from zipfile import ZipFile

from safeshift.data.saved_reports import checked, confined, git, json_bytes, sha256, strict_json
from safeshift.evaluation.ct1_pilot import EXCLUSIONS_SHA256, validate_plan
from safeshift.fulltrain import ct1_native, ct1_run
from safeshift.pilot.artifacts import sha, write, write_bytes
from safeshift.pilot.manifest import validate_master
from scripts.build_qwen3_composite import CONFIG, MASTER

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ("DATA_PATH", "train", "Annotations")
QUOTAS = {"Level01": 20, "Level02": 12, "Level04": 16}
SEED = "safeshift-ct1-development-48-v1"
NOTEBOOK = "notebooks/SafeShift_CT1_EVIDENCE_PILOT_KAGGLE.ipynb"


def opaque(salt, sid):
    import hmac
    return "p-" + hmac.digest(salt, sid.encode(), "sha256").hex()[:12]


def fingerprint(image):
    from PIL import Image
    values = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
    return sum((values[i] > values[i + 1]) << k
               for k, i in enumerate(row * 9 + col for row in range(8) for col in range(8)))


def clean_png(raw):
    from PIL import Image, ImageOps
    with Image.open(BytesIO(raw), formats=("JPEG", "PNG")) as source:
        if getattr(source, "n_frames", 1) != 1 or not ct1_native.image_size_allowed(source.size):
            return None
        with ImageOps.exif_transpose(source).convert("RGB") as rgb:
            image = Image.frombytes("RGB", rgb.size, rgb.tobytes())
            with image, BytesIO() as stream:
                image.save(stream, "PNG", compress_level=3)
                payload = stream.getvalue()
                require_image = len(payload) <= ct1_run.IMAGE_BYTES
                if not require_image:
                    return None
                with ct1_native.image_from_bytes(payload) as admitted:
                    return payload, fingerprint(admitted)


def prepare_images(train, audit_images, exclusions_file, output):
    from PIL import Image
    cfg = strict_json(git(ROOT, "show", f"HEAD:{CONFIG}"))
    master = checked(git(ROOT, "show", f"{cfg['history_commit']}:{MASTER}"),
                     cfg["historical_files_sha256"][MASTER])
    rows = validate_master(strict_json(master))
    exclusions_raw = checked(exclusions_file.read_bytes(), EXCLUSIONS_SHA256)
    excluded = set(strict_json(exclusions_raw))
    counts = Counter(row["image_sha256"] for row in rows)
    with_dir = []
    for i in range(1, 17):
        p = confined(audit_images, f"{i:02}.png")
        if sha(p) not in excluded:
            raise ValueError("audit PNG must be one of the exact excluded hashes")
        with Image.open(p, formats=("PNG",)) as image:
            with_dir.append(fingerprint(image))
    if len(set(with_dir)) != len(with_dir):
        raise ValueError("audited images are not a distinct fingerprint set")
    salt = token_bytes(32)
    prepared, groups, rejects = [], set(), Counter()
    for level, n in QUOTAS.items():
        pending = [r for r in rows if r["level"] == level]
        pending.sort(key=lambda r: sha256(f"{SEED}/{r['sample_id']}".encode()))
        per_domain = Counter()
        for _ in range(n):
            while pending:
                least = min(per_domain[row["domain"]] for row in pending)
                choice = next(i for i, row in enumerate(pending) if per_domain[row["domain"]] == least)
                row = pending.pop(choice)
                if (row["image_sha256"] in excluded or counts[row["image_sha256"]] != 1
                        or row["test_exact_pairs_historical"] or Path(row["image_locator"]).parent.name in groups):
                    rejects["whole_train_exact_or_waypoint_exclusions"] += 1
                    continue
                p = confined(train, row["image_locator"], PREFIX)
                raw = checked(p.read_bytes(), row["image_sha256"], row["image_size_bytes"])
                clean = clean_png(raw)
                if clean is None:
                    rejects["image_envelope"] += 1
                    continue
                png, dhash = clean
                if sha256(png) in excluded or any((dhash ^ prev).bit_count() <= 5 for prev in with_dir):
                    rejects["audit_or_within_pilot_image_similarity"] += 1
                    continue
                with_dir.append(dhash)
                groups.add(Path(row["image_locator"]).parent.name)
                per_domain[row["domain"]] += 1
                prepared.append((opaque(salt, row["sample_id"]), row, png))
                break
            else:
                raise ValueError(f"insufficient independent image candidates for {level}")
    # Cohort selection uses GT only for local stratification. Random aliases and
    # mixed order make neither class nor source available to the notebook.
    prepared.sort(key=lambda item: item[0])
    cases = [{"case_id": key, "image_sha256": sha256(png)} for key, _, png in prepared]
    plan = {"kind": "TRAIN_DEVELOPMENT", "arms": ["A", "E", "S"], "cases": cases}
    validate_plan(plan, sorted(excluded))
    plan_bytes = json_bytes(plan)
    plan_sha = sha256(plan_bytes)
    output.mkdir(exist_ok=False)
    pilot, private = output / "pilot-input", output / "private-scoring"
    write_bytes(pilot / "plan.json", plan_bytes)
    write_bytes(pilot / "exclusions.json", exclusions_raw)
    for case, _, png in prepared:
        write_bytes(pilot / "images" / (case + ".png"), png)
    write(private / "truth.json", {"plan_sha256": plan_sha, "cases": [
        {"case_id": case, "true_level": row["level"]} for case, row, _ in prepared]})
    write(private / "custody.json", {"master_sha256": sha256(master), "historical_ref": cfg["history_commit"],
        "seed": SEED, "plan_sha256": plan_sha, "not_for_kaggle": True, "rejects": dict(rejects),
        "samples": [{"case_id": case, **{k: row[k] for k in
                    ("sample_id", "image_sha256", "image_locator", "domain", "group", "level")}}
                    for case, row, _ in prepared]})
    ct1_run.admit(pilot, plan_sha)
    write(output / "receipt.json", {"plan_sha256": plan_sha, "images": ct1_run.N_IMAGES,
          "planned_calls": ct1_run.N_CALLS, "subset": QUOTAS, "audit_images_excluded": 16,
          "confirmation": False, "test_files_opened": 0, "annot_files_opened": 0})
    print(plan_sha)


def software_bundle(output):
    """Acquire known public software bytes only. Does not install or access Kaggle."""
    from scripts.prepare_qwen173_software import download
    from scripts.qualify_kaggle173_software import wheel_location
    from safeshift.fulltrain import provision, qwen
    ref = qwen.reference(ROOT)
    candidate = strict_json((ROOT / "configs/issue173/qwen_linux_cp312_wheels.json").read_bytes())
    output.mkdir(exist_ok=False)
    (output / "wheels").mkdir()
    marker = {"schema": "fresh-qwen-software-v1", "runtime_lock": {"versions": {}, "wheels": []}}
    for component in ("python_source", "zlib_source"):
        row = ref[component]
        info = download(row["url"], output / row["url"].rsplit("/", 1)[1], row["sha256"])
        marker[component] = {k: info[k] for k in ("file", "size", "sha256")}
    total = 0
    for item in candidate["packages"]:
        package, name = wheel_location(item)
        info = download(item["url"], output / "wheels" / name, item["sha256"],
                        max_bytes=min(4 * 2**30, 16 * 2**30 - total), seconds=600)
        total += info["size"]
        lock = marker["runtime_lock"]
        lock["versions"][package] = item["version"]
        lock["wheels"].append({"file": name, "name": package, "version": item["version"],
                               "size": info["size"], "sha256": info["sha256"]})
    path = output / "fresh_qwen_software.json"
    digest = write(path, marker)
    provision.software_input(output, digest, marker["runtime_lock"], ROOT)
    print(digest)


def checkpoint_bundle(output):
    """Prepare the exact public checkpoint as a byte-verified mount, without loading weights."""
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import quote
    from safeshift.fulltrain import qwen
    from scripts.prepare_qwen173_software import download
    ref = qwen.reference(ROOT)
    model = ref["model"]
    output.mkdir(exist_ok=False)
    snapshot = output / model["revision"]
    snapshot.mkdir()

    def acquire(row):
        file = row["path"]
        expected = row.get("sha256") if row["hash_algorithm"] == "git_blob_sha1" else row["expected_hash"]
        url = f"https://huggingface.co/{model['id']}/resolve/{model['revision']}/{quote(file)}"
        info = download(url, snapshot / file, expected, max_bytes=row["size_bytes"], seconds=2400)
        if info["size"] != row["size_bytes"]:
            raise ValueError(f"unexpected checkpoint length: {file}")
        return file

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(acquire, ref["snapshot_files"]):
            print(f"Verified {name}", flush=True)
    verified = qwen.verify_snapshot(snapshot, repo=ROOT)
    write(output / "checkpoint-receipt.json", verified)

def source_payload(commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("supply exact commit SHA")
    code_path = ("safeshift", "scripts/run_ct1_native_pilot.py", "configs/fulltrain/qwen3.json",
                 "configs/pilot/classification_c1.txt", "configs/pilot/pip_bootstrap.json")
    payload = subprocess.check_output(["git", "archive", "--format=zip", commit, *code_path], cwd=ROOT)
    if len(payload) > 8 * 2**20:
        raise ValueError("CT1 source capsule too large")
    with ZipFile(BytesIO(payload)) as archive:
        if any(not (n.startswith("safeshift/") or n in code_path) for n in archive.namelist() if not n.endswith("/")):
            raise ValueError("unexpected source capsule entries")
    return payload


def source_bundle(commit, output):
    payload = source_payload(commit)
    notebook = git(ROOT, "show", commit + ":" + NOTEBOOK)
    output.mkdir(exist_ok=False)
    write_bytes(output / "ct1-source.zip", payload)
    write(output / "ct1-source.json", {"commit": commit, "sha256": sha256(payload)})
    write(output.parent / "notebook-sha256.json", {"commit": commit, "path": NOTEBOOK,
                                                  "sha256": sha256(notebook)})
    print(sha256(payload))


def main():
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    source = sub.add_parser("source")
    source.add_argument("--commit", required=True)
    stage = sub.add_parser("images")
    stage.add_argument("--train", type=Path, required=True)
    stage.add_argument("--audit-images", type=Path, required=True)
    stage.add_argument("--exclusions", type=Path, required=True)
    sw = sub.add_parser("software")
    for p in (source, stage, sw, sub.add_parser("checkpoint")):
        p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "images":
        prepare_images(args.train, args.audit_images, args.exclusions, args.output)
    elif args.command == "source":
        source_bundle(args.commit, args.output)
    elif args.command == "software":
        software_bundle(args.output)
    else:
        checkpoint_bundle(args.output)


if __name__ == "__main__":
    main()
