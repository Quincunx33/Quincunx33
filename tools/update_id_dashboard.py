#!/usr/bin/env python3
"""Refresh live GitHub profile graphics from the public GitHub REST API."""

from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = os.environ.get("GITHUB_USERNAME", "Quincunx33")
API_BASE = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
SVG = f"{{{SVG_NS}}}"
PALETTE = ["#ff7a59", "#7db8ff", "#c084fc", "#fde047", "#4ade80", "#22d3ee"]


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


def calculate_metrics(user: dict, repos: list[dict]) -> dict:
    originals = [repo for repo in repos if not repo.get("fork", False)]
    return {
        "public_repos": int(user["public_repos"]),
        "stars": sum(int(repo.get("stargazers_count", 0)) for repo in originals),
        "followers": int(user["followers"]),
        "following": int(user["following"]),
        "original_repos": originals,
        "fork_count": len(repos) - len(originals),
    }


def aggregate_language_bytes(repos: list[dict], get_languages=get_json) -> Counter:
    totals: Counter = Counter()
    for repo in repos:
        if repo.get("fork", False):
            continue
        url = f"{API_BASE}/repos/{USERNAME}/{repo['name']}/languages"
        languages = get_languages(url)
        if isinstance(languages, dict):
            for language, byte_count in languages.items():
                totals[str(language)] += int(byte_count)
    return totals


def parse_svg(path: str) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise RuntimeError(f"Could not parse SVG {path}: {exc}") from exc


def write_svg(path: str, root: ET.Element) -> None:
    ET.ElementTree(root).write(path, encoding="unicode", xml_declaration=True)


def text_nodes(root: ET.Element):
    return [node for node in root.iter(f"{SVG}text")]


def find_text(root: ET.Element, value: str) -> ET.Element:
    matches = [node for node in text_nodes(root) if "".join(node.itertext()).strip() == value]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one SVG text node containing {value!r}; found {len(matches)}")
    return matches[0]


def find_text_prefix(root: ET.Element, prefix: str) -> ET.Element:
    matches = [
        node for node in text_nodes(root)
        if "".join(node.itertext()).strip().startswith(prefix)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one SVG text node beginning with {prefix!r}; found {len(matches)}")
    return matches[0]


def find_node(root: ET.Element, tag: str, **attrs: str) -> ET.Element:
    matches = [
        node for node in root.iter(f"{SVG}{tag}")
        if all(node.get(key) == value for key, value in attrs.items())
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one SVG <{tag}> with {attrs}; found {len(matches)}")
    return matches[0]


def update_dashboard(metrics: dict, updated: str) -> None:
    root = parse_svg("profile-dashboard.svg")
    for x, value in {
        "438.0": metrics["public_repos"],
        "646.5": metrics["stars"],
        "855.0": metrics["followers"],
        "1063.5": metrics["following"],
    }.items():
        find_node(root, "text", **{"class": "sg", "x": x, "y": "188"}).text = str(value)

    originals = sorted(
        metrics["original_repos"],
        key=lambda repo: (int(repo.get("stargazers_count", 0)), repo.get("name", "").lower()),
        reverse=True,
    )[:5]
    max_stars = max((int(repo.get("stargazers_count", 0)) for repo in originals), default=0)
    for index, y in enumerate((311, 345, 379, 413, 447)):
        repo = originals[index] if index < len(originals) else None
        name = str(repo.get("name", "—")) if repo else "—"
        if len(name) > 23:
            name = name[:20] + "…"
        stars = int(repo.get("stargazers_count", 0)) if repo else 0
        find_node(root, "text", **{"class": "jb", "x": "442", "y": str(y)}).text = name
        star_nodes = [
            node for node in text_nodes(root)
            if node.get("class") == "jbb" and node.get("y") == str(y)
        ]
        if len(star_nodes) != 1:
            raise RuntimeError(f"Expected one star-count text at y={y}")
        star_nodes[0].text = str(stars)
        bar_y = str(y - 11)
        bar = find_node(root, "rect", x="592", y=bar_y, fill="url(#barG)")
        bar.set("width", str(round(210 * stars / max_stars, 1) if max_stars else 0))

    find_node(root, "text", **{"class": "sg", "x": "936", "y": "322"}).text = str(metrics["followers"])
    find_node(root, "text", **{"class": "sg", "x": "1074", "y": "322"}).text = str(metrics["following"])
    find_node(root, "text", **{"class": "jb", "x": "936", "y": "342"}).text = "GITHUB FOLLOWERS"
    find_node(root, "text", **{"class": "jb", "x": "1074", "y": "342"}).text = "GITHUB FOLLOWING"
    find_node(root, "text", **{"class": "jb", "x": "442", "y": "494"}).text = f"Live GitHub data · updated {updated}"
    write_svg("profile-dashboard.svg", root)


def update_hero_and_banners(metrics: dict) -> None:
    hero = parse_svg("hero.svg")
    find_node(hero, "text", **{"class": "jb", "x": "408", "y": "458"}).text = (
        f"{metrics['stars']} stars · {metrics['public_repos']} repos"
    )
    write_svg("hero.svg", hero)

    for path in ("tasfiya-banner.svg", "tasfiya-banner-light.svg"):
        root = parse_svg(path)
        for x, value in {
            "118": metrics["public_repos"],
            "258": metrics["following"],
            "398": metrics["stars"],
            "538": metrics["followers"],
        }.items():
            find_node(root, "text", **{"class": "st", "x": x, "y": "640"}).text = str(value)
        write_svg(path, root)


def update_secondary_stats(metrics: dict) -> None:
    root = parse_svg("tasfiya-stats.svg")
    values = {
        "Total Stars Earned:": ("Total Stars Earned:", metrics["stars"]),
        "Following:": ("Following:", metrics["following"]),
        "Public Repos:": ("Public Repos:", metrics["public_repos"]),
        "Followers:": ("Followers:", metrics["followers"]),
    }
    for old_label, (new_label, value) in values.items():
        if old_label == "Following:":
            try:
                label_node = find_text(root, "Following:")
            except RuntimeError:
                label_node = find_text(root, "Total Commits:")
        else:
            label_node = find_text(root, old_label)
        label_node.text = new_label
        value_node = find_node(
            root, "text", x="316", y=label_node.get("y", "")
        )
        value_node.text = str(value)
    write_svg("tasfiya-stats.svg", root)

    trophy = parse_svg("tasfiya-trophies.svg")
    trophy_values = (
        ("Stars ", f"Stars {metrics['stars']}"),
        ("Followers ", f"Followers {metrics['followers']}"),
        ("Following ", f"Following {metrics['following']}"),
        ("Commits ", f"Following {metrics['following']}"),
        ("Repos ", f"Repos {metrics['public_repos']}"),
    )
    updated_categories = set()
    for prefix, new in trophy_values:
        category = "Following" if prefix in ("Following ", "Commits ") else prefix.strip()
        if category in updated_categories:
            continue
        try:
            node = find_text_prefix(trophy, prefix)
        except RuntimeError:
            continue
        node.text = new
        updated_categories.add(category)
    if not {"Stars", "Followers", "Following", "Repos"}.issubset(updated_categories):
        raise RuntimeError("Could not update every live trophy metric")
    write_svg("tasfiya-trophies.svg", trophy)


def render_languages_svg(language_bytes: Counter) -> str:
    total = sum(language_bytes.values())
    top = language_bytes.most_common(4)
    if not top or total <= 0:
        top = [("No language data", 1)]
        total = 1
    rows = []
    stack = []
    x = 20.0
    for index, (name, amount) in enumerate(top):
        color = PALETTE[index % len(PALETTE)]
        percent = amount * 100 / total
        width = 268 * percent / 100
        y = 96 + index * 42
        rows.append(
            f'<g class="row" style="animation-delay:{0.45 + index * 0.2:.2f}s">'
            f'<circle cx="26" cy="{y - 5}" r="5" fill="{color}"/>'
            f'<text x="40" y="{y}" font-size="13" fill="#e6edf3" font-weight="bold">{escape(name)}</text>'
            f'<text x="396" y="{y}" text-anchor="end" font-size="13" fill="{color}" font-weight="bold">{percent:.1f}%</text>'
            f'<rect x="40" y="{y + 8}" width="268" height="9" rx="4.5" fill="#241740"/>'
            f'<rect class="bar" x="40" y="{y + 8}" width="{width:.1f}" height="9" rx="4.5" fill="{color}"/>'
            f'</g>'
        )
        stack.append(f'<rect x="{x:.1f}" y="58" width="{380 * percent / 100:.1f}" height="11" fill="{color}"/>')
        x += 380 * percent / 100
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 282" width="420" height="282" role="img" aria-label="Top languages by source bytes across original public repositories">'
        '<defs><style>text{font-family:SFMono-Regular,Consolas,monospace}.row{opacity:0;animation:fadeUp .5s ease forwards}@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}</style>'
        '<linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#ff7eb6"/><stop offset="100%" stop-color="#c084fc"/></linearGradient></defs>'
        '<rect x="1" y="1" width="418" height="280" rx="14" fill="#170e28" stroke="url(#tg)" stroke-width="1.5"/>'
        '<text x="20" y="34" font-size="16" font-weight="bold" fill="url(#tg)">📊 Top Languages · live</text>'
        '<g>' + ''.join(stack) + '</g>' + ''.join(rows) + '</svg>'
    )


def render_project_atlas(metrics: dict) -> str:
    counts = Counter(repo.get("language") or "Other" for repo in metrics["original_repos"])
    top = counts.most_common(6)
    max_count = max((count for _, count in top), default=1)
    rows = []
    colors = ["#3178C6", "#F7DF1E", "#3776AB", "#E34F26", "#8B5CF6", "#00599C"]
    for index, (language, count) in enumerate(top):
        y = 192 + index * 28
        color = colors[index % len(colors)]
        rows.append(
            f'<circle cx="52" cy="{y - 5}" r="6" fill="{color}"/>'
            f'<text x="70" y="{y}" fill="#CBD5E1" font-family="Inter,Arial,sans-serif" font-size="15px" font-weight="600">{escape(language)}</text>'
            f'<text x="180" y="{y}" fill="#8EA3BF" font-family="Inter,Arial,sans-serif" font-size="13px">{count} repos</text>'
            f'<rect x="285" y="{y - 17}" width="330" height="12" rx="6" fill="#1C2B45"/>'
            f'<rect x="285" y="{y - 17}" width="{330 * count / max_count:.1f}" height="12" rx="6" fill="{color}"/>'
        )
    total = len(metrics["original_repos"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="360" viewBox="0 0 760 360">'
        '<rect width="100%" height="100%" rx="20" fill="#0B1220"/><rect x="20" y="20" width="720" height="320" rx="16" fill="#111C31" stroke="#243653"/>'
        '<text x="48" y="70" fill="#00D9FF" font-family="Inter,Arial,sans-serif" font-size="14px" font-weight="700">PUBLIC PROJECT ATLAS · LIVE</text>'
        f'<text x="48" y="112" fill="#CBD5E1" font-family="Inter,Arial,sans-serif" font-size="27px" font-weight="700">{total} original public repositories</text>'
        '<text x="48" y="140" fill="#8EA3BF" font-family="Inter,Arial,sans-serif" font-size="15px">Language distribution by repository metadata · forks excluded</text>'
        f'<circle cx="620" cy="100" r="48" fill="none" stroke="#243653" stroke-width="12"/><circle cx="620" cy="100" r="48" fill="none" stroke="#00D9FF" stroke-width="12" stroke-dasharray="{min(302, total * 8)} 302" transform="rotate(-90 620 100)"/>'
        f'<text x="620" y="107" fill="#CBD5E1" font-family="Inter,Arial,sans-serif" font-size="22px" font-weight="700" text-anchor="middle">{total}</text>'
        + ''.join(rows) + '</svg>'
    )


def update_lanyard_handle() -> None:
    path = "tasfiya-lanyard.svg"
    with open(path, encoding="utf-8") as source:
        svg = source.read()
    old = "@Tasfiyamittal0920"
    new = "@tasfiya__tabassum__"
    if old in svg:
        svg = svg.replace(old, new, 1)
    elif new not in svg:
        raise RuntimeError("Neither the old nor current lanyard handle was found")
    with open(path, "w", encoding="utf-8", newline="\\n") as destination:
        destination.write(svg)


def update_readme_cache_buster() -> None:
    path = "README.md"
    with open(path, encoding="utf-8") as source:
        readme = source.read()
    cache_buster = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    for filename in ("profile-dashboard.svg", "hero.svg"):
        pattern = rf'src="\./{re.escape(filename)}(?:\?v=[^"]*)?"'
        readme, count = re.subn(pattern, f'src="./{filename}?v={cache_buster}"', readme, count=1)
        if count != 1:
            raise RuntimeError(f"Could not find {filename} image reference in README.md")
    with open(path, "w", encoding="utf-8", newline="\n") as destination:
        destination.write(readme)


def main() -> None:
    user, repos = fetch_profile_data()
    required = ("public_repos", "followers", "following")
    missing = [key for key in required if key not in user]
    if missing:
        raise RuntimeError(f"GitHub API response is missing expected fields: {', '.join(missing)}")
    metrics = calculate_metrics(user, repos)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    update_dashboard(metrics, updated)
    update_hero_and_banners(metrics)
    update_secondary_stats(metrics)
    languages = aggregate_language_bytes(metrics["original_repos"])
    with open("tasfiya-langs.svg", "w", encoding="utf-8", newline="\n") as output:
        output.write(render_languages_svg(languages))
    with open("assets/public-project-atlas.svg", "w", encoding="utf-8", newline="\n") as output:
        output.write(render_project_atlas(metrics))
    update_lanyard_handle()
    update_readme_cache_buster()
    print(
        "Updated live profile assets: "
        f"public repos={metrics['public_repos']}, stars={metrics['stars']}, "
        f"followers={metrics['followers']}, following={metrics['following']}, "
        f"original repos={len(metrics['original_repos'])}, forks excluded={metrics['fork_count']}, "
        f"languages={len(languages)}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
