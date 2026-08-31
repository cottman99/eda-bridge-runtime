from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "evals" / "public-readme-data-v1.json"
OUTPUT = ROOT / "docs" / "assets" / "readme"

WIDTH = 1600
HEIGHT = 900
WHITE = "#ffffff"
INK = "#171717"
MUTED = "#6d6d6d"
GRID = "#e7e7e7"
RED = "#ea2218"
PALE_RED = "#f8b9b5"


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    raise FileNotFoundError("No supported public chart font was found")


TITLE = _font(58, bold=True)
SUBTITLE = _font(28)
LABEL = _font(27, bold=True)
BODY = _font(23)
SMALL = _font(20)
VALUE = _font(25, bold=True)


def _canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)
    draw.text((90, 58), title, font=TITLE, fill=INK)
    draw.text((92, 132), subtitle, font=SUBTITLE, fill=MUTED)
    return image, draw


def _save(image: Image.Image, name: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / name, optimize=True)


def render_complete_workflows(data: dict) -> None:
    section = data["complete_workflows"]
    image, draw = _canvas(
        "Where complete-workflow time was spent",
        f"{section['sample']}  |  frozen baseline {section['date']}",
    )
    rows = section["rows"]
    left, top, right, bottom = 170, 245, 1510, 735
    maximum = max(row["total_seconds"] for row in rows) * 1.08
    for tick in range(0, 251, 50):
        y = bottom - (tick / maximum) * (bottom - top)
        draw.line((left, y, right, y), fill=GRID, width=2)
        draw.text((98, y - 13), str(tick), font=SMALL, fill=MUTED)
    draw.line((left, top, left, bottom), fill=INK, width=4)
    draw.line((left, bottom, right, bottom), fill=INK, width=4)

    centers = [300, 590, 1000, 1290]
    bar_width = 180
    for center, row in zip(centers, rows, strict=True):
        total = row["total_seconds"]
        bridge = row["bridge_eda_seconds"]
        bridge_h = bridge / maximum * (bottom - top)
        total_h = total / maximum * (bottom - top)
        x0, x1 = center - bar_width // 2, center + bar_width // 2
        draw.rounded_rectangle((x0, bottom - bridge_h, x1, bottom), radius=16, fill=RED)
        draw.rounded_rectangle((x0, bottom - total_h, x1, bottom - bridge_h), radius=16, fill=INK)
        text = f"{total:.1f}s"
        box = draw.textbbox((0, 0), text, font=VALUE)
        draw.text(
            (center - (box[2] - box[0]) / 2, bottom - total_h - 42), text, font=VALUE, fill=INK
        )
        label_lines = row["label"].split("\n")
        draw.text((center, 765), label_lines[0], font=LABEL, fill=INK, anchor="ma")
        draw.text((center, 802), label_lines[1], font=BODY, fill=MUTED, anchor="ma")

    draw.rectangle((1040, 188, 1070, 218), fill=RED)
    draw.text((1085, 188), "Bridge + EDA", font=BODY, fill=INK)
    draw.rectangle((1270, 188, 1300, 218), fill=INK)
    draw.text((1315, 188), "Agent overhead", font=BODY, fill=INK)
    draw.text(
        (92, 858),
        "Seconds. ADS stays interactive; the HFSS solve dominates the long journey.",
        font=BODY,
        fill=INK,
    )
    _save(image, "runtime-complete-workflow-time.png")


def render_bounded_agent_tests(data: dict) -> None:
    section = data["bounded_agent_tests"]
    image, draw = _canvas(
        "One Runtime. Two Agents. Real EDA work.",
        f"{section['sample']}  |  frozen baseline {section['date']}  |  lower is faster",
    )
    rows = section["rows"]
    chart_left, chart_right = 560, 1450
    top, row_gap = 235, 93
    maximum = max(max(row["codex_seconds"], row["pi_seconds"]) for row in rows) * 1.12

    for index, row in enumerate(rows):
        y = top + index * row_gap
        draw.text((92, y + 16), row["label"], font=LABEL, fill=INK)
        for offset, key, color in ((0, "codex_seconds", INK), (37, "pi_seconds", RED)):
            value = row[key]
            x1 = chart_left + value / maximum * (chart_right - chart_left)
            draw.rounded_rectangle(
                (chart_left, y + offset, x1, y + offset + 25), radius=12, fill=color
            )
            draw.text((x1 + 14, y + offset - 2), f"{value:.1f}s", font=VALUE, fill=color)

    draw.ellipse((90, 807, 116, 833), fill=INK)
    draw.text((129, 805), "Codex", font=BODY, fill=INK)
    draw.ellipse((245, 807, 271, 833), fill=RED)
    draw.text((284, 805), "Pi Agent", font=BODY, fill=INK)
    draw.text((560, 805), "Same typed Runtime / Bridge path", font=BODY, fill=MUTED)
    draw.text(
        (92, 858),
        "Agent-heavy work shows the largest gap; EDA-lifecycle-heavy work converges.",
        font=BODY,
        fill=INK,
    )
    _save(image, "codex-pi-bounded-tests.png")


def _log_x(value_ms: float, left: int, right: int) -> float:
    return left + math.log10(value_ms) / 3 * (right - left)


def render_supervised_live_edit(data: dict) -> None:
    section = data["supervised_live_edit"]
    image, draw = _canvas(
        "Sub-second edits in the open EDA session",
        f"Bounded supervised acceptance  |  {section['date']}  |  "
        "no restart or project copy per patch",
    )
    axis_left, axis_right = 490, 1480
    plot_top, plot_bottom = 245, 750
    for tick, text in ((1, "1 ms"), (10, "10 ms"), (100, "100 ms"), (1000, "1 s")):
        x = _log_x(tick, axis_left, axis_right)
        draw.line((x, plot_top, x, plot_bottom), fill=GRID, width=2)
        draw.text((x, 770), text, font=SMALL, fill=MUTED, anchor="ma")

    panel_tops = [230, 500]
    for panel_top, vendor in zip(panel_tops, section["vendors"], strict=True):
        draw.text((92, panel_top), vendor["name"], font=LABEL, fill=INK)
        draw.text((92, panel_top + 38), vendor["accepted_version"], font=SMALL, fill=MUTED)
        for index, metric in enumerate(vendor["metrics"]):
            y = panel_top + 88 + index * 42
            draw.text((245, y - 12), metric["label"], font=BODY, fill=INK)
            if "value_ms" in metric:
                value = metric["value_ms"]
                x = _log_x(value, axis_left, axis_right)
                draw.line((axis_left, y, x, y), fill=GRID, width=5)
                draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=RED)
                draw.text((x + 18, y - 14), f"{value} ms", font=VALUE, fill=INK)
            else:
                low, high = metric["low_ms"], metric["high_ms"]
                x0, x1 = _log_x(low, axis_left, axis_right), _log_x(high, axis_left, axis_right)
                draw.line((x0, y, x1, y), fill=PALE_RED, width=12)
                draw.ellipse((x0 - 8, y - 8, x0 + 8, y + 8), fill=RED)
                draw.ellipse((x1 - 8, y - 8, x1 + 8, y + 8), fill=RED)
                draw.text((x1 + 18, y - 14), f"{low}–{high} ms", font=VALUE, fill=INK)

    draw.text(
        (92, 824),
        "Shared result: immediate readback · zero duplicate objects on exact replay · "
        "patch-local rollback · Codex and Pi passed",
        font=BODY,
        fill=INK,
    )
    draw.text(
        (92, 860),
        "Log scale. Vendor timing boundaries differ; each panel is a workflow "
        "baseline, not a vendor ranking.",
        font=SMALL,
        fill=MUTED,
    )
    _save(image, "supervised-live-edit-latency.png")


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    render_complete_workflows(data)
    render_bounded_agent_tests(data)
    render_supervised_live_edit(data)


if __name__ == "__main__":
    main()
