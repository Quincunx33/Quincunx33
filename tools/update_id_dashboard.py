#!/usr/bin/env python3
"""Refresh the GitHub-derived metrics in profile-dashboard.svg."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = os.environ.get("GITHUB_USERNAME", "Quincunx33")
API_BASE = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
SVG_PATH = "profile-dashboard.svg"
README_PATH = "README.md"


def get_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-dashboard-updater",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"GitHub API request failed for {url}: {exc}") from exc


def fetch_profile_data() -> tuple[dict, list[dict]]:
    user = get_json(f"{API_BASE}/users/{USERNAME}")
    if not isinstance(user, dict):
        raise RuntimeError("GitHub API returned an unexpected user profile response")

    repos: list[dict] = []
    page = 1
    while True:
        query = urlencode({"type": "owner", "per_page": 100, "page": page, "sort": "updated"})
        batch = get_json(f"{API_BASE}/users/{USERNAME}/repos?{query}")
        if not isinstance(batch, list):
            raise RuntimeError("GitHub API returned an unexpected repositories response")
        repos.extend(repo for repo in batch if isinstance(repo, dict) and not repo.get("private", False))
        if len(batch) < 100:
            break
        page += 1
    return user, repos


def update_metric(svg: str, x: str, value: int) -> str:
    pattern = re.compile(
        rf'<text class="sg" x="{re.escape(x)}" y="188"[^>]*>.*?</text>', re.DOTALL
    )
    matches = list(pattern.finditer(svg))
    if not matches:
        raise RuntimeError(f"Could not find SVG metric at x={x}")
    replacement = (
        f'<text class="sg" x="{x}" y="188" font-size="36" '
        f'fill="#eceef6">{value}</text>'
    )
    pieces = []
    cursor = 0
    for index, match in enumerate(matches):
        pieces.append(svg[cursor : match.start()])
        pieces.append(replacement if index == 0 else "")
        cursor = match.end()
    pieces.append(svg[cursor:])
    return "".join(pieces)


def update_repo_rows(svg: str, repos: list[dict]) -> str:
    top = sorted(repos, key=lambda repo: (repo.get("stargazers_count", 0), repo.get("name", "").lower()), reverse=True)[:5]
    row_y = [311, 345, 379, 413, 447]
    max_stars = max((int(repo.get("stargazers_count", 0)) for repo in top), default=0)
    for index, y in enumerate(row_y):
        if index < len(top):
            name = str(top[index].get("name", "—"))
            # Keep unusually long repository names from overrunning the fixed-width card.
            if len(name) > 23:
                name = name[:20] + "…"
            stars = int(top[index].get("stargazers_count", 0))
        else:
            name, stars = "—", 0
        name_pattern = re.compile(
            rf'(<text class="jb" x="442" y="{y}" font-size="12" fill="#8d93ab">).*?(</text>)',
            re.DOTALL,
        )
        svg, count = name_pattern.subn(lambda m: m.group(1) + escape(name) + m.group(2), svg, count=1)
        if count != 1:
            raise RuntimeError(f"Could not find repository-name row at y={y}")
        star_pattern = re.compile(
            rf'(<text class="jbb" x="[^"]+" y="{y}" font-size="12" fill="#eceef6"[^>]*>).*?(</text>)',
            re.DOTALL,
        )
        svg, count = star_pattern.subn(lambda m: m.group(1) + str(stars) + m.group(2), svg, count=1)
        if count != 1:
            raise RuntimeError(f"Could not find star-count row at y={y}")
        bar_y = y - 11
        bar_width = round(210 * stars / max_stars, 1) if max_stars else 0
        bar_pattern = re.compile(
            rf'(<rect x="592" y="{bar_y}" )width="[^"]+"([^>]*fill="url\(#barG\)")>.*?</rect>',
            re.DOTALL,
        )
        svg, count = bar_pattern.subn(
            lambda m: f'{m.group(1)}width="{bar_width}"{m.group(2)}></rect>', svg, count=1
        )
        if count != 1:
            raise RuntimeError(f"Could not find star bar at y={bar_y}")
    return svg


def main() -> None:
    user, repos = fetch_profile_data()
    required = ("public_repos", "followers", "following")
    missing = [key for key in required if key not in user]
    if missing:
        raise RuntimeError(f"GitHub API response is missing expected fields: {', '.join(missing)}")

    total_stars = sum(int(repo.get("stargazers_count", 0)) for repo in repos)
    metrics = {
        "438.0": int(user["public_repos"]),
        "646.5": total_stars,
        "855.0": int(user["followers"]),
        "1063.5": int(user["following"]),
    }

    with open(SVG_PATH, encoding="utf-8") as source:
        svg = source.read()
    original_svg = svg
    for x, value in metrics.items():
        svg = update_metric(svg, x, value)
    svg = update_repo_rows(svg, repos)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    svg, count = re.subn(
        r'<text class="jb" x="442" y="494" font-size="10" fill="#8d93ab" opacity="\.75">.*?</text>',
        f'<text class="jb" x="442" y="494" font-size="10" fill="#8d93ab" opacity=".75">Live GitHub data · updated {updated}</text>',
        svg,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not find dashboard update timestamp label")
    if svg != original_svg:
        with open(SVG_PATH, "w", encoding="utf-8", newline="\n") as destination:
            destination.write(svg)

    # Change the image URL on every run to bypass GitHub's rendered-image cache.
    cache_buster = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    with open(README_PATH, encoding="utf-8") as source:
        readme = source.read()
    readme, count = re.subn(
        r'src="\./profile-dashboard\.svg(?:\?v=[^"]*)?"',
        f'src="./profile-dashboard.svg?v={cache_buster}"',
        readme,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not find profile-dashboard.svg image reference in README.md")
    with open(README_PATH, "w", encoding="utf-8", newline="\n") as destination:
        destination.write(readme)

    print(
        "Updated GitHub dashboard: "
        f"public repos={metrics['438.0']}, total stars={total_stars}, "
        f"followers={metrics['855.0']}, following={metrics['1063.5']}; "
        f"top repos={min(len(repos), 5)}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
