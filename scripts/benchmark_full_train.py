"""Offline, versioned CPU reporting for the selected Full-TRAIN label products."""

import argparse
from html import escape
import json
from pathlib import Path
import platform
import sys

from safeshift.data.saved_reports import checked, confined, git, json_bytes, sha256, strict_json
from safeshift.data.schema import SAFETY_LEVELS as LEVELS
from safeshift.evaluation.full_train_benchmark import PRODUCTS, SCHEMA, compare, is_sha256
from safeshift.evaluation.qwen_composite import require
from scripts.build_qwen3_composite import csv_bytes


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = "configs/analysis/full_train_benchmark.v1.json"
MEMBERS = ("cohort", *PRODUCTS)
LIMIT_BYTES = 16 * 1024 * 1024
SOURCE_FILES = (
    "scripts/benchmark_full_train.py",
    "scripts/build_qwen3_composite.py",
    "safeshift/data/saved_reports.py",
    "safeshift/evaluation/full_train_benchmark.py",
    "safeshift/evaluation/qwen_composite.py",
)


def read_config(root):
    # Read repository-published admission only. No untracked or CLI override.
    config = strict_json(git(root, "show", f"HEAD:{CONFIG_PATH}"))
    require(config["schema"] == SCHEMA and config["planned_n"] == 3763,
            "unexpected benchmark configuration or cohort size")
    return config


def load_inputs(root, input_dir, config):
    release = config["release"]
    require(isinstance(release, dict),
            "BLOCKED: exact TRAIN evaluation rights and reviewed input admission absent")
    members = release.get("members")
    require(all(isinstance(release.get(key), str) and release[key].strip()
                for key in ("rights_ref", "custody_ref", "source_review_ref")) and
            isinstance(members, dict) and set(members) == set(MEMBERS),
            "incomplete TRAIN rights, custody, source review or members")
    require(set(config["products"]) == set(PRODUCTS) and
            all(is_sha256(config["products"][key]["source_seal_sha256"]) for key in PRODUCTS),
            "all selected products require authenticated source seals")
    for pin in members.values():
        require(isinstance(pin, dict) and type(pin.get("size_bytes")) is int and
                0 < pin["size_bytes"] <= LIMIT_BYTES and
                is_sha256(pin["sha256"]), "invalid member size or SHA256 pin")
    loaded = {}
    for key in MEMBERS:
        pin = members[key]
        path = confined(root, f"{input_dir}/{key}.json", ("data", "processed"))
        require(path.is_file() and path.stat().st_size == pin["size_bytes"],
                f"{key}: expected exact admitted file size")
        with path.open("rb") as stream:
            data = stream.read(pin["size_bytes"] + 1)
        obj = strict_json(checked(data, pin["sha256"], pin["size_bytes"]))
        require(obj["schema"] == f"{SCHEMA}-{'cohort' if key == 'cohort' else 'product'}",
                f"{key}: wrong projection schema")
        loaded[key] = obj
    return loaded.pop("cohort"), loaded


def metric_rows(value, path=""):
    if isinstance(value, dict):
        for key in sorted(value):
            segment = key.replace("~", "~0").replace("/", "~1")
            yield from metric_rows(value[key], f"{path}/{segment}")
    else:
        yield {"metric_path": path, "value": json.dumps(value, ensure_ascii=False)
               if isinstance(value, list) else value}


def confusion_html(models, notice):
    headings = (*LEVELS, "INVALID")
    columns = "".join(f"<th scope='col'>{label}</th>" for label in headings)
    tables = []
    for name, model in models.items():
        confusion = model["overall"]["confusion_4x5"]
        rows = []
        for truth in LEVELS:
            support = sum(confusion[truth].values())
            cells = []
            for predicted in headings:
                n = confusion[truth][predicted]
                pct = round(100 * n / support) if support else 0
                shade = 100 - pct * 0.61
                cells.append(f"<td style='background:hsl(199, 65%, {shade:.1f}%);"
                             f"color:{'#fff' if pct >= 75 else '#162d3d'}' "
                             f"title='{pct}% of this true class'>{n}</td>")
            rows.append(f"<tr><th scope='row'>{truth} ({support})</th>{''.join(cells)}</tr>")
        tables.append(f"<table><caption>{escape(name)}</caption>"
                      f"<thead><tr><th scope='col'>GT (n)</th>{columns}</tr></thead>"
                      f"<tbody>{''.join(rows)}</tbody></table>")
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>SafeShift TRAIN confusion matrices</title>"
            "<style>body{font:16px system-ui;color:#162d3d;margin:2rem;}"
            ".panels{display:flex;gap:2rem;flex-wrap:wrap;overflow-x:auto}"
            "table{border-collapse:collapse}caption{text-align:left;font-weight:700;margin-bottom:.5rem}"
            "th,td{text-align:right;padding:.45rem .7rem;border:1px solid #c4d4dc}</style>"
            f"<h1>SafeShift TRAIN confusion matrices</h1><p>{escape(notice)}</p>"
            "<p>Cells show counts. Darker cells indicate a larger share of each true class.</p>"
            f"<div class='panels'>{''.join(tables)}</div></html>\n").encode("utf-8")


def export(root, output_dir, result, config, command):
    output = confined(root, output_dir, ("data", "processed"))
    result_data = json_bytes(result)
    files = {
        "benchmark.json": result_data,
        "metrics.csv": csv_bytes(list(metric_rows({"models": result["models"],
                                                   "paired": result["paired"],
                                                   "scores": result["scores"]}))),
        "confusion.html": confusion_html(result["models"], "Retrospective comparison on exposed TRAIN."),
    }
    receipt = {"schema": f"{SCHEMA}-receipt", "source_sha": git(root, "rev-parse", "HEAD").decode().strip(),
               "source_dirty": bool(git(root, "status", "--porcelain", "--untracked-files=no")),
               "python": platform.python_version(), "config_sha256": sha256(
                   git(root, "show", f"HEAD:{CONFIG_PATH}")),
               "source_files": {name: sha256(confined(root, name).read_bytes()) for name in SOURCE_FILES},
               "command": command,
               "cohort_identity_sha256": result["cohort_identity_sha256"],
               "authority_and_inputs": config["release"], "seed": None,
               "outputs": {name: sha256(data) for name, data in files.items()}}
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (output / name).write_bytes(data)
    (output / "receipt.json").write_bytes(json_bytes(receipt))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, help="admitted Git-ignored projection directory")
    parser.add_argument("--output-dir", required=True, help="fresh Git-ignored output directory")
    command = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(command)
    try:
        config = read_config(ROOT)
        cohort, products = load_inputs(ROOT, args.input_dir, config)
        export(ROOT, args.output_dir, compare(cohort, products, config), config,
               ["python", "-B", "-m", "scripts.benchmark_full_train", *command])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
