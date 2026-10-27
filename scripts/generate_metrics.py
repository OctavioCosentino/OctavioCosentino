#!/usr/bin/env python3
"""Genera assets/stats.svg, assets/langs.svg y assets/streak.svg con datos reales de GitHub."""
import datetime
import html
import json
import os
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("GH_LOGIN", "OctavioCosentino")
TOKEN = os.environ["GH_TOKEN"]
OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(exist_ok=True)

BG = "#0d0420"
BORDER = "#8a2be2"
TITLE = "#c084fc"
TEXT = "#ede9fe"
ACC = "#c4b5fd"
MUTED = "#a78bfa"
PAL = ["#e9d5ff", "#c4b5fd", "#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9"]
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def card(w, h, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'<style>text{{font-family:{FONT};font-size:14px;fill:{TEXT}}}</style>\n'
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" '
        f'stroke="{BORDER}" stroke-opacity="0.8"/>\n'
        f'{body}\n</svg>\n'
    )


def esc(s):
    return html.escape(str(s))


def build_stats(u, stars, commits):
    rows = [
        ("Total Stars Earned", stars),
        ("Total Commits (last year)", commits),
        ("Total PRs", u["pullRequests"]["totalCount"]),
        ("Total Issues", u["issues"]["totalCount"]),
        ("Repos with contributions (last year)",
         u["contributionsCollection"]["totalRepositoriesWithContributedCommits"]),
    ]
    body = f'<text x="24" y="40" font-size="18" font-weight="700" fill="{TITLE}">GitHub Stats</text>'
    for i, (label, value) in enumerate(rows):
        y = 72 + i * 26
        body += (f'<text x="24" y="{y}">{esc(label)}</text>'
                 f'<text x="421" y="{y}" text-anchor="end" font-weight="700" fill="{ACC}">{value}</text>')
    return card(445, 200, body)


def build_langs(top, total):
    body = f'<text x="24" y="40" font-size="18" font-weight="700" fill="{TITLE}">Most Used Languages</text>'
    body += '<clipPath id="bar"><rect x="24" y="58" width="397" height="10" rx="5"/></clipPath>'
    body += '<g clip-path="url(#bar)"><rect x="24" y="58" width="397" height="10" fill="#1e1538"/>'
    x = 24.0
    for i, (_, size) in enumerate(top):
        w = 397 * size / total
        body += f'<rect x="{x:.2f}" y="58" width="{w:.2f}" height="10" fill="{PAL[i]}"/>'
        x += w
    body += '</g>'
    for i, (name, size) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 205, 90 + row * 30
        pct = 100 * size / total
        body += (f'<rect x="{lx}" y="{ly}" width="10" height="10" rx="2" fill="{PAL[i]}"/>'
                 f'<text x="{lx + 18}" y="{ly + 10}">{esc(name)}</text>'
                 f'<text x="{lx + 185}" y="{ly + 10}" text-anchor="end" fill="{MUTED}">{pct:.2f}%</text>')
    return card(445, 200, body)


def streak_stats(days):
    counts = [d["contributionCount"] for d in days]
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    i = len(counts) - 1
    if counts and counts[-1] == 0:
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest, sum(counts)


def icon(kind, cx, cy):
    shapes = {
        "fire": '<path d="M12 2C12 2 17 7 17 12.5A5 5 0 0 1 7 12.5C7 9 9 7.5 10 5.5C10.8 7.6 12 8.5 12 8.5C12 8.5 11 5.5 12 2Z" fill="#fff"/>',
        "bars": ('<rect x="4" y="12" width="4" height="8" rx="1" fill="#fff"/>'
                 '<rect x="10" y="7" width="4" height="13" rx="1" fill="#fff"/>'
                 '<rect x="16" y="3" width="4" height="17" rx="1" fill="#fff"/>'),
        "star": '<polygon points="12,2 15,9 22,9 16.5,13.5 18.5,21 12,16.8 5.5,21 7.5,13.5 2,9 9,9" fill="#fff"/>',
    }
    return f'<g transform="translate({cx - 12} {cy - 12})">{shapes[kind]}</g>'


def build_streak(current, longest, total):
    cols = [
        (157, f"{current}", "Current Streak (days)", "fire"),
        (470, f"{total}", "Contributions (last year)", "bars"),
        (783, f"{longest}", "Longest Streak (days)", "star"),
    ]
    defs = (
        '<defs>'
        '<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#a78bfa"/><stop offset="1" stop-color="#4c1d95"/></linearGradient>'
        '<linearGradient id="sep" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#8b5cf6" stop-opacity="0"/>'
        '<stop offset="0.5" stop-color="#a78bfa"/>'
        '<stop offset="1" stop-color="#8b5cf6" stop-opacity="0"/></linearGradient>'
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>'
    )
    body = defs
    body += f'<text x="28" y="40" font-size="18" font-weight="700" fill="{TITLE}">Contribution Streak</text>'
    body += '<rect x="28" y="54" width="884" height="1" fill="url(#sep)"/>'
    body += '<line x1="310" y1="78" x2="310" y2="186" stroke="#4c1d95" stroke-opacity="0.6"/>'
    body += '<line x1="630" y1="78" x2="630" y2="186" stroke="#4c1d95" stroke-opacity="0.6"/>'
    for cx, value, label, kind in cols:
        body += (
            f'<circle cx="{cx}" cy="100" r="36" fill="none" stroke="#6d28d9" stroke-opacity="0.35"/>'
            f'<circle cx="{cx}" cy="100" r="29" fill="url(#ring)" filter="url(#glow)"/>'
            + icon(kind, cx, 100)
            + f'<text x="{cx}" y="162" text-anchor="middle" font-size="28" font-weight="700" fill="{ACC}">{value}</text>'
            + f'<text x="{cx}" y="184" text-anchor="middle" font-size="13" fill="{MUTED}">{esc(label)}</text>'
        )
    return card(940, 200, body)


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    since = now - datetime.timedelta(days=365)
    u = gql(QUERY, {"login": LOGIN, "from": since.isoformat(), "to": now.isoformat()})

    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    sizes = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:6]

    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest, year_total = streak_stats(days)
    commits = u["contributionsCollection"]["totalCommitContributions"]

    (OUT / "stats.svg").write_text(build_stats(u, stars, commits), encoding="utf-8")
    (OUT / "langs.svg").write_text(build_langs(top, total), encoding="utf-8")
    (OUT / "streak.svg").write_text(build_streak(current, longest, year_total), encoding="utf-8")
    print("Métricas actualizadas en", OUT)


if __name__ == "__main__":
    main()
