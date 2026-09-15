"""Plot verified W1 audit figures using Pillow without heavy dependencies."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]

# Verified counts from W1 Dataset Audit
DOMAIN_COUNTS = {
    "coal_conveyor": {"Normal": 865, "Anomaly": 256, "Total": 1121},
    "metallurgy": {"Normal": 711, "Anomaly": 9, "Total": 720},
    "oil_chemical": {"Normal": 662, "Anomaly": 361, "Total": 1023},
    "power": {"Normal": 767, "Anomaly": 102, "Total": 869},
    "tunnel": {"Normal": 1008, "Anomaly": 272, "Total": 1280},
}

SAFETY_COUNTS = {
    "Level01\n(High Risk)": {"count": 659, "pct": 13.15, "color": (220, 38, 38)},     # Red
    "Level02\n(Moderate)": {"count": 326, "pct": 6.50, "color": (234, 88, 12)},      # Orange
    "Level03\n(Minor)": {"count": 15, "pct": 0.30, "color": (217, 119, 6)},          # Amber
    "Level04\n(Normal)": {"count": 4013, "pct": 80.05, "color": (16, 185, 129)},     # Green
}

PLATFORM_BY_DOMAIN = {
    "coal_conveyor": {"SuspendedRail": 1121, "Wheeled": 0, "Rail_pct": 100.0},
    "metallurgy": {"SuspendedRail": 59, "Wheeled": 661, "Rail_pct": 8.2},
    "oil_chemical": {"SuspendedRail": 100, "Wheeled": 923, "Rail_pct": 9.8},
    "power": {"SuspendedRail": 106, "Wheeled": 763, "Rail_pct": 12.2},
    "tunnel": {"SuspendedRail": 1256, "Wheeled": 24, "Rail_pct": 98.1},
}


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load system font if available, fallback to default."""
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def plot_domain_distribution(output_path: Path) -> None:
    """Plot Normal vs Anomaly distribution across 5 industrial domains."""
    width, height = 960, 580
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = get_font(20, bold=True)
    sub_font = get_font(13)
    axis_font = get_font(13, bold=True)
    tick_font = get_font(12)
    val_font = get_font(11, bold=True)
    note_font = get_font(10)

    # Title & Subtitle
    draw.text((40, 25), "InspecSafe-V1: Sample Distribution by Industrial Domain", fill=(17, 24, 39), font=title_font)
    draw.text((40, 52), "Breakdown of Normal (N=4,013) vs. Anomaly (N=1,000) across 5 domains (Total N=5,013)", fill=(75, 85, 99), font=sub_font)

    # Plot area
    margin_left, margin_right = 90, 50
    margin_top, margin_bottom = 110, 100
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    max_val = 1400  # Ceiling above max tunnel=1280
    y_ticks = [0, 200, 400, 600, 800, 1000, 1200, 1400]

    # Grid & Y axis ticks
    for tick in y_ticks:
        y = margin_top + plot_h - int(tick / max_val * plot_h)
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=(243, 244, 246), width=1)
        draw.text((margin_left - 45, y - 7), f"{tick:,}", fill=(107, 114, 128), font=tick_font)

    # Axes
    draw.line([(margin_left, margin_top + plot_h), (margin_left + plot_w, margin_top + plot_h)], fill=(156, 163, 175), width=2)
    draw.line([(margin_left, margin_top), (margin_left, margin_top + plot_h)], fill=(156, 163, 175), width=2)

    # Bars (Grouped: Normal vs Anomaly)
    domains = list(DOMAIN_COUNTS.keys())
    group_width = plot_w / len(domains)
    bar_w = 40
    gap = 8

    c_normal = (37, 99, 235)    # Blue
    c_anomaly = (220, 38, 38)   # Red

    for i, dom in enumerate(domains):
        group_center = margin_left + (i + 0.5) * group_width
        norm_val = DOMAIN_COUNTS[dom]["Normal"]
        anom_val = DOMAIN_COUNTS[dom]["Anomaly"]
        tot_val = DOMAIN_COUNTS[dom]["Total"]

        # Normal bar
        norm_h = int(norm_val / max_val * plot_h)
        x_norm = group_center - bar_w - gap / 2
        y_norm = margin_top + plot_h - norm_h
        draw.rectangle([(x_norm, y_norm), (x_norm + bar_w, margin_top + plot_h)], fill=c_normal)
        draw.text((x_norm + 4, y_norm - 16), f"{norm_val}", fill=c_normal, font=val_font)

        # Anomaly bar
        anom_h = int(anom_val / max_val * plot_h)
        x_anom = group_center + gap / 2
        y_anom = margin_top + plot_h - anom_h
        draw.rectangle([(x_anom, y_anom), (x_anom + bar_w, margin_top + plot_h)], fill=c_anomaly)
        draw.text((x_anom + 6, y_anom - 16), f"{anom_val}", fill=c_anomaly, font=val_font)

        # Domain label & total
        dom_display = dom.replace("_", " ")
        draw.text((group_center - 35, margin_top + plot_h + 10), dom_display, fill=(17, 24, 39), font=axis_font)
        draw.text((group_center - 25, margin_top + plot_h + 30), f"Total: {tot_val:,}", fill=(107, 114, 128), font=tick_font)

        # Metallurgy alert badge
        if dom == "metallurgy":
            draw.text((x_anom - 15, y_anom - 32), "(Test Anom=0)", fill=(185, 28, 28), font=val_font)

    # Legend
    leg_x, leg_y = width - 260, 45
    draw.rectangle([(leg_x, leg_y), (leg_x + 16, leg_y + 16)], fill=c_normal)
    draw.text((leg_x + 22, leg_y + 1), "Normal_data (80.05%)", fill=(31, 41, 55), font=tick_font)
    draw.rectangle([(leg_x, leg_y + 24), (leg_x + 16, leg_y + 40)], fill=c_anomaly)
    draw.text((leg_x + 22, leg_y + 25), "Anomaly_data (19.95%)", fill=(31, 41, 55), font=tick_font)

    # Footer / Source
    footer_text = "SafeShift Week 1 Dataset Audit — Verified counts from InspecSafe-V1 local census (5,013 samples). Non-causal summary."
    draw.text((margin_left, height - 25), footer_text, fill=(156, 163, 175), font=note_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


def plot_safety_distribution(output_path: Path) -> None:
    """Plot Safety Level distribution showing severe class imbalance (Level01 to Level04)."""
    width, height = 960, 580
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = get_font(20, bold=True)
    sub_font = get_font(13)
    axis_font = get_font(13, bold=True)
    tick_font = get_font(12)
    val_font = get_font(12, bold=True)
    note_font = get_font(10)
    alert_font = get_font(11, bold=True)

    # Title & Subtitle
    draw.text((40, 25), "InspecSafe-V1: Safety Level Class Imbalance", fill=(17, 24, 39), font=title_font)
    draw.text((40, 52), "Distribution across 4 official safety levels (Extreme ratio Level04 : Level03 = 267.5 : 1)", fill=(75, 85, 99), font=sub_font)

    margin_left, margin_right = 90, 50
    margin_top, margin_bottom = 110, 110
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    max_val = 4500
    y_ticks = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500]

    for tick in y_ticks:
        y = margin_top + plot_h - int(tick / max_val * plot_h)
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=(243, 244, 246), width=1)
        draw.text((margin_left - 45, y - 7), f"{tick:,}", fill=(107, 114, 128), font=tick_font)

    draw.line([(margin_left, margin_top + plot_h), (margin_left + plot_w, margin_top + plot_h)], fill=(156, 163, 175), width=2)
    draw.line([(margin_left, margin_top), (margin_left, margin_top + plot_h)], fill=(156, 163, 175), width=2)

    levels = list(SAFETY_COUNTS.keys())
    group_width = plot_w / len(levels)
    bar_w = 90

    for i, lvl in enumerate(levels):
        center_x = margin_left + (i + 0.5) * group_width
        data = SAFETY_COUNTS[lvl]
        count = data["count"]
        pct = data["pct"]
        color = data["color"]

        bar_h = max(3, int(count / max_val * plot_h))
        x0 = center_x - bar_w / 2
        y0 = margin_top + plot_h - bar_h

        draw.rectangle([(x0, y0), (x0 + bar_w, margin_top + plot_h)], fill=color)

        # Label on top of bar
        draw.text((center_x - 30, y0 - 32), f"{count:,}", fill=color, font=val_font)
        draw.text((center_x - 24, y0 - 16), f"({pct:.2f}%)", fill=(75, 85, 99), font=tick_font)

        # Category label
        lbl_lines = lvl.split("\n")
        draw.text((center_x - 28, margin_top + plot_h + 10), lbl_lines[0], fill=(17, 24, 39), font=axis_font)
        if len(lbl_lines) > 1:
            draw.text((center_x - 35, margin_top + plot_h + 28), lbl_lines[1], fill=(107, 114, 128), font=tick_font)

        # Callout for Level03 rare class
        if "Level03" in lvl:
            callout_x = center_x
            callout_y = y0 - 70
            draw.rectangle([(callout_x - 70, callout_y), (callout_x + 70, callout_y + 28)], fill=(254, 243, 199), outline=(217, 119, 6), width=1)
            draw.text((callout_x - 62, callout_y + 6), "Rare Class: 15 samples", fill=(180, 83, 9), font=alert_font)
            draw.line([(callout_x, callout_y + 28), (callout_x, y0 - 36)], fill=(217, 119, 6), width=1)

    footer_text = "SafeShift Week 1 Dataset Audit — Level04 accounts for 80.05% of dataset. Plain accuracy will hide minority class performance."
    draw.text((margin_left, height - 25), footer_text, fill=(156, 163, 175), font=note_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


def plot_platform_by_domain(output_path: Path) -> None:
    """Plot Robot Platform distribution by Domain demonstrating severe platform confounding."""
    width, height = 960, 580
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = get_font(20, bold=True)
    sub_font = get_font(13)
    axis_font = get_font(13, bold=True)
    tick_font = get_font(12)
    val_font = get_font(11, bold=True)
    note_font = get_font(10)

    draw.text((40, 25), "InspecSafe-V1: Platform Confounding Across Domains", fill=(17, 24, 39), font=title_font)
    draw.text((40, 52), "SuspendedRail (Suspended) vs. Wheeled (Ground) across 5 industrial domains", fill=(75, 85, 99), font=sub_font)

    margin_left, margin_right = 90, 50
    margin_top, margin_bottom = 110, 100
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    max_val = 1400
    y_ticks = [0, 200, 400, 600, 800, 1000, 1200, 1400]

    for tick in y_ticks:
        y = margin_top + plot_h - int(tick / max_val * plot_h)
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=(243, 244, 246), width=1)
        draw.text((margin_left - 45, y - 7), f"{tick:,}", fill=(107, 114, 128), font=tick_font)

    draw.line([(margin_left, margin_top + plot_h), (margin_left + plot_w, margin_top + plot_h)], fill=(156, 163, 175), width=2)
    draw.line([(margin_left, margin_top), (margin_left, margin_top + plot_h)], fill=(156, 163, 175), width=2)

    domains = list(PLATFORM_BY_DOMAIN.keys())
    group_width = plot_w / len(domains)
    bar_w = 40
    gap = 8

    c_rail = (99, 102, 241)     # Indigo
    c_wheel = (20, 184, 166)    # Teal

    for i, dom in enumerate(domains):
        group_center = margin_left + (i + 0.5) * group_width
        rail_cnt = PLATFORM_BY_DOMAIN[dom]["SuspendedRail"]
        wheel_cnt = PLATFORM_BY_DOMAIN[dom]["Wheeled"]
        tot = rail_cnt + wheel_cnt
        rail_pct = PLATFORM_BY_DOMAIN[dom]["Rail_pct"]

        # SuspendedRail bar
        rail_h = int(rail_cnt / max_val * plot_h)
        x_rail = group_center - bar_w - gap / 2
        y_rail = margin_top + plot_h - rail_h
        draw.rectangle([(x_rail, y_rail), (x_rail + bar_w, margin_top + plot_h)], fill=c_rail)
        if rail_cnt > 0:
            draw.text((x_rail + 4, y_rail - 16), f"{rail_cnt}", fill=c_rail, font=val_font)

        # Wheeled bar
        wheel_h = int(wheel_cnt / max_val * plot_h)
        x_wheel = group_center + gap / 2
        y_wheel = margin_top + plot_h - wheel_h
        draw.rectangle([(x_wheel, y_wheel), (x_wheel + bar_w, margin_top + plot_h)], fill=c_wheel)
        if wheel_cnt > 0:
            draw.text((x_wheel + 6, y_wheel - 16), f"{wheel_cnt}", fill=c_wheel, font=val_font)

        dom_display = dom.replace("_", " ")
        draw.text((group_center - 35, margin_top + plot_h + 10), dom_display, fill=(17, 24, 39), font=axis_font)
        draw.text((group_center - 42, margin_top + plot_h + 28), f"Rail: {rail_pct:.1f}%", fill=(79, 70, 229), font=val_font)

    # Legend
    leg_x, leg_y = width - 260, 45
    draw.rectangle([(leg_x, leg_y), (leg_x + 16, leg_y + 16)], fill=c_rail)
    draw.text((leg_x + 22, leg_y + 1), "SuspendedRail (2,642, 52.7%)", fill=(31, 41, 55), font=tick_font)
    draw.rectangle([(leg_x, leg_y + 24), (leg_x + 16, leg_y + 40)], fill=c_wheel)
    draw.text((leg_x + 22, leg_y + 25), "Wheeled (2,371, 47.3%)", fill=(31, 41, 55), font=tick_font)

    footer_text = "SafeShift Week 1 Dataset Audit — Domain effects cannot be cleanly separated from robot platform / camera viewpoint."
    draw.text((margin_left, height - 25), footer_text, fill=(156, 163, 175), font=note_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/figures"))
    args = parser.parse_args(argv)

    out_dir = args.output_dir
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir

    p1 = out_dir / "w1_domain_distribution.png"
    p2 = out_dir / "w1_safety_distribution.png"
    p3 = out_dir / "w1_platform_by_domain.png"

    plot_domain_distribution(p1)
    plot_safety_distribution(p2)
    plot_platform_by_domain(p3)

    def format_path(p: Path) -> str:
        try:
            return p.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return p.as_posix()

    print(f"Generated: {format_path(p1)}")
    print(f"Generated: {format_path(p2)}")
    print(f"Generated: {format_path(p3)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
