"""Deterministic geometric RGB fixtures; no fonts, media, randomness or model."""

import argparse
import struct
import zlib

from safeshift.qualification.classification import (
    ROOT, MANIFEST, FIXTURES, SUITE, SOURCE_KIND, MARKERS, POLICY, digest, json_bytes,
)


def fixture(index):
    marker = index // 2
    cx, cy = ((128, 128) if index % 2 == 0 else (150, 110))
    colors = ((230, 25, 25), (20, 65, 235), (250, 215, 15), (20, 170, 55))
    pixels = bytearray()
    for y in range(256):
        pixels.append(0)  # PNG filter: none
        for x in range(256):
            dx, dy = x - cx, y - cy
            inside = ((-50 <= dy <= 50 and abs(dx) * 2 <= dy + 50),
                      abs(dx) + abs(dy) <= 58,
                      dx * dx + dy * dy <= 50 * 50,
                      abs(dx) <= 48 and abs(dy) <= 48)[marker]
            color = colors[marker] if inside else (245, 245, 245)
            if index % 2 and 22 <= x <= 50 and 192 <= y <= 220:
                color = (140, 140, 140)
            pixels.extend(color)
    def chunk(kind, content):
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(pixels), 9)) + chunk(b"IEND", b""))


def generate(repo=ROOT, check=False):
    cases = []
    for index in range(8):
        case_id = f"cq_{index + 1:02d}"
        path = f"{FIXTURES}/{case_id}.png"
        raw = fixture(index)
        if check:
            if (repo / path).read_bytes() != raw:
                raise ValueError("FIXTURE_NOT_REPRODUCIBLE")
        else:
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_bytes(raw)
        marker = list(MARKERS)[index // 2]
        cases.append({"case_id": case_id, "image_path": path, "image_sha256": digest(raw),
                      "expected_safety_level": MARKERS[marker], "marker": marker})
    manifest = {"suite": SUITE, "version": 1, "source_kind": SOURCE_KIND,
                "NOT_INSPECSAFE": True, "NOT_ACCURACY_BENCHMARK": True,
                "policy_text": POLICY, "policy_sha256": digest(POLICY.encode()),
                "generator": "scripts/generate_classification_qualification_cases.py",
                "seed": None, "cases": cases}
    raw = json_bytes(manifest)
    if check:
        if (repo / MANIFEST).read_bytes().replace(b"\r\n", b"\n") != raw:
            raise ValueError("MANIFEST_NOT_REPRODUCIBLE")
    else:
        (repo / MANIFEST).write_bytes(raw)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    generate(check=parser.parse_args().check)
