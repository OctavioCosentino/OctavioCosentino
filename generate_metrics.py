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


def build_streak(current, longest, total):
    items = [
        (157, f"{current}", "Current Streak (days)"),
        (470, f"{total}", "Contributions (last year)"),
        (783, f"{longest}", "Longest Streak (days)"),
    ]
    body = f'<text x="24" y="40" font-size="18" font-weight="700" fill="{TITLE}">Contribution Streak</text>'
    for x, value, label in items:
        body += (f'<text x="{x}" y="120" text-anchor="middle" font-size="40" font-weight="700" '
                 f'fill="{ACC}">{value}</text>'
                 f'<text x="{x}" y="150" text-anchor="middle" fill="{MUTED}">{esc(label)}</text>')
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
