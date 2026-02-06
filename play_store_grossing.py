#!/usr/bin/env python3
"""Fetch Google Play top grossing ranking (collection) via HTML scraping."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from html import unescape
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://play.google.com/store/apps/collection/topgrossing"
APP_LINK_RE = re.compile(
    r"<a[^>]+href=\"/store/apps/details\?id=([^&\"]+)[^\"]*\"[^>]*>"
    r"[^<]*",
    re.IGNORECASE,
)
ARIA_LABEL_RE = re.compile(r"aria-label=\"([^\"]+)\"")


@dataclass
class AppEntry:
    rank: int
    app_id: str
    title: str


def build_url(language: str, region: str, category: str | None) -> str:
    params = {
        "hl": language,
        "gl": region,
    }
    if category:
        params["category"] = category
    return f"{BASE_URL}?{urlencode(params)}"


def fetch_html(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_apps(html: str) -> list[AppEntry]:
    entries: list[AppEntry] = []
    seen: set[str] = set()

    for match in APP_LINK_RE.finditer(html):
        app_id = match.group(1)
        if app_id in seen:
            continue
        anchor_tag = match.group(0)
        label_match = ARIA_LABEL_RE.search(anchor_tag)
        title = unescape(label_match.group(1)).strip() if label_match else ""
        entries.append(AppEntry(rank=len(entries) + 1, app_id=app_id, title=title))
        seen.add(app_id)

    return entries


def trim_entries(entries: list[AppEntry], limit: int | None) -> list[AppEntry]:
    if limit is None:
        return entries
    return entries[:limit]


def output_csv(entries: Iterable[AppEntry]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(["rank", "app_id", "title"])
    for entry in entries:
        writer.writerow([entry.rank, entry.app_id, entry.title])


def output_json(entries: Iterable[AppEntry]) -> None:
    payload = [
        {"rank": entry.rank, "app_id": entry.app_id, "title": entry.title}
        for entry in entries
    ]
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Google Play top grossing ranking (collection).",
    )
    parser.add_argument("--hl", default="ko", help="Language code (default: ko)")
    parser.add_argument("--gl", default="KR", help="Region code (default: KR)")
    parser.add_argument(
        "--category",
        default=None,
        help="Optional category (e.g. GAME, BUSINESS)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Limit results (default: 50)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of CSV",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = build_url(args.hl, args.gl, args.category)
    html = fetch_html(url)
    entries = trim_entries(extract_apps(html), args.limit)

    if args.json:
        output_json(entries)
    else:
        output_csv(entries)

    if not entries:
        sys.stderr.write("No entries found. HTML structure may have changed.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
