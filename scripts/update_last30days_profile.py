#!/usr/bin/env python3
"""Generate the Last30Days profile SVG from the upstream skill output."""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = (ROOT / os.environ.get("LAST30DAYS_SKILL_DIR", ".agents/skills/last30days")).resolve()
ENGINE = SKILL_DIR / "scripts" / "last30days.py"
DATA_PATH = ROOT / "data" / "last30days.md"
SVG_PATH = ROOT / "assets" / "last30days.svg"


def run_last30days() -> str:
    if not ENGINE.exists():
        raise SystemExit(f"Last30Days engine not found at {ENGINE}")

    topic = os.environ.get("LAST30DAYS_TOPIC", "DIGITALGORITHMS")
    search = os.environ.get("LAST30DAYS_SEARCH", "github,hn,reddit")
    github_user = os.environ.get("LAST30DAYS_GITHUB_USER", "")

    cmd = [
        sys.executable,
        str(ENGINE),
        topic,
        "--search",
        search,
        "--quick",
        "--lookback-days",
        "30",
        "--emit",
        "md",
        "--output",
        str(DATA_PATH),
    ]
    if github_user:
        cmd.extend(["--github-user", github_user])

    env = os.environ.copy()
    env.setdefault("LAST30DAYS_MEMORY_DIR", str(ROOT / "data"))
    env.setdefault("LAST30DAYS_CONFIG_DIR", "")
    env.setdefault("SETUP_COMPLETE", "true")
    env.setdefault("FROM_BROWSER", "off")

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout)

    if DATA_PATH.exists():
        return DATA_PATH.read_text(encoding="utf-8")
    DATA_PATH.write_text(result.stdout, encoding="utf-8")
    return result.stdout


def strip_markdown(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[*_`#>]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def summarize(markdown: str) -> list[str]:
    if "Limited recent data" in markdown or "Evidence is thin" in markdown:
        return [
            "No strong public Last30Days signal was found for DIGITALGORITHMS in the latest run.",
            "The workflow refreshes weekly and will surface GitHub, HN, and Reddit evidence when available.",
            "Raw output is stored in data/last30days.md for review.",
        ]

    lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = strip_markdown(raw_line)
        if not line:
            continue
        if line.startswith(("last30days", "What I learned:", "KEY PATTERNS", "Safety note")):
            continue
        if line.startswith(("---", "✅", "📎", "Raw results saved", "Date range", "Sources", "Freshness", "Warnings")):
            continue
        lines.append(line)

    joined = " ".join(lines)
    if not joined:
        joined = "Last30Days generated a fresh profile research snapshot."

    wrapped = textwrap.wrap(joined, width=88, max_lines=5, placeholder="...")
    return wrapped or ["Last30Days generated a fresh profile research snapshot."]


def write_svg(markdown: str) -> None:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary_lines = summarize(markdown)

    width = 860
    height = 310
    title = "Last 30 Days"
    subtitle = "DIGITALGORITHMS profile research snapshot"

    text_nodes = []
    y = 130
    for line in summary_lines:
        text_nodes.append(
            f'<text x="42" y="{y}" class="body">{html.escape(line)}</text>'
        )
        y += 24

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(title)} - {html.escape(subtitle)}</title>
  <desc id="desc">A weekly Last30Days research summary card generated for the DIGITALGORITHMS GitHub profile.</desc>
  <defs>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#101827"/>
      <stop offset="55%" stop-color="#172235"/>
      <stop offset="100%" stop-color="#1f2937"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" rx="18" fill="url(#card)"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="17" fill="none" stroke="#374151"/>
  <style>
    .eyebrow {{ fill: #93c5fd; font: 700 13px ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: 1.8px; }}
    .title {{ fill: #f9fafb; font: 800 34px ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .meta {{ fill: #cbd5e1; font: 500 15px ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .body {{ fill: #e5e7eb; font: 500 16px ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .footer {{ fill: #94a3b8; font: 500 13px ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  </style>
  <text x="42" y="48" class="eyebrow">LAST30DAYS</text>
  <text x="42" y="86" class="title">What changed recently</text>
  <text x="42" y="110" class="meta">Generated from mvanhorn/last30days-skill · updated {html.escape(updated)}</text>
  {chr(10).join(text_nodes)}
  <text x="42" y="{height - 34}" class="footer">Source: https://github.com/mvanhorn/last30days-skill</text>
</svg>
'''
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(svg, encoding="utf-8")


def main() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    markdown = run_last30days()
    write_svg(markdown)


if __name__ == "__main__":
    main()
