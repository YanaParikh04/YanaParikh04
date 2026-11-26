#!/usr/bin/env python3
"""Builds assets/{light,dark}/contributions.svg and languages.svg from real GitHub data.
Usage: python profile_cards.py            (needs GH_TOKEN; GH_USER defaults to YanaParikh04)
       python profile_cards.py --empty    (writes placeholder cards, no network)
"""
import json, os, sys, math, html, urllib.request, datetime

USER = os.environ.get("GH_USER", "YanaParikh04")
ROOT = os.environ.get("ASSETS_DIR", "assets")
SANS = "font-family:'Segoe UI',Helvetica,Arial,sans-serif"
NS = 'xmlns="http://www.w3.org/2000/svg"'
RM = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"

THEMES = {
    "dark":  dict(card="#151B28", line="#2A3347", text="#EEF1FA", mid="#B6BDD6", muted="#8089A8", accent="#5EEAD4",
                  levels=["#1A2233", "#1F4A4A", "#238276", "#3DB9A8", "#5EEAD4"]),
    "light": dict(card="#F7F8FC", line="#DADFEE", text="#181B34", mid="#454A6E", muted="#6F7599", accent="#0B8579",
                  levels=["#E7EAF6", "#BDE6DF", "#73CFC1", "#2DA898", "#0B8579"]),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
esc = lambda s: html.escape(str(s), quote=False)

QUERY = """
query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount contributionLevel weekday } } } }
  repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){ totalCount nodes{
    languages(first:8, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name color } } } } }
} }"""

def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json", "User-Agent": "profile-cards"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "errors" in d: raise SystemExit(json.dumps(d["errors"]))
    u = d["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]; langs.setdefault(n["name"], [0, n["color"] or "#8089A8"])[0] += e["size"]
    return cal, langs, u["repositories"]["totalCount"]

def contributions_svg(cal, T):
    W, H, gx, gy, cs, step = 1000, 226, 72, 82, 13, 16
    weeks = cal["weeks"] if cal else []
    total = f'{cal["totalContributions"]:,}' if cal else "-"
    foot = "Last 52 weeks of activity." if cal else "Your data appears after the first workflow run."
    cells, months, last_m = "", "", None
    for ci in range(53):
        days = weeks[ci]["contributionDays"] if ci < len(weeks) else []
        by = {d["weekday"]: d for d in days}
        if days:
            m = datetime.date.fromisoformat(days[0]["date"]).strftime("%b")
            if m != last_m and ci < 51:
                months += f'<text x="{gx+ci*step}" y="{gy-10}" class="mo">{m}</text>'
            last_m = m
        for r in range(7):
            d = by.get(r)
            if cal and d is None: continue
            lvl = LEVEL.get(d["contributionLevel"], 0) if d else 0
            tip = f'<title>{d["contributionCount"]} contributions on {d["date"]}</title>' if d else ""
            cells += f'<rect x="{gx+ci*step}" y="{gy+r*step}" width="{cs}" height="{cs}" rx="3" fill="{T["levels"][lvl]}" class="c" style="animation-delay:{ci*0.018:.2f}s">{tip}</rect>'
    labels = "".join(f'<text x="30" y="{gy+r*step+cs-2}" class="dl">{n}</text>' for r, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    legend = "".join(f'<rect x="{800+i*17}" y="{H-26}" width="12" height="12" rx="3" fill="{c}"/>' for i, c in enumerate(T["levels"]))
    return f'''<svg {NS} viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub contributions over the last 52 weeks: {total} total">
<style>.t{{font-weight:700;font-size:17px;fill:{T["text"]};{SANS}}}.tt{{font-size:14px;fill:{T["mid"]};text-anchor:end;{SANS}}}.mo,.dl{{font-size:11px;fill:{T["muted"]};{SANS}}}.f{{font-size:12px;fill:{T["muted"]};{SANS}}}
.c{{animation:in .5s ease-out both}}@keyframes in{{from{{opacity:0;transform:scale(.4)}}to{{opacity:1;transform:none}}}}.c{{transform-box:fill-box;transform-origin:center}}{RM}</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{T["card"]}" stroke="{T["line"]}"/>
<text x="28" y="40" class="t">Contributions</text><text x="972" y="40" class="tt" style="font-weight:700;fill:{T["text"]}">{total}</text><text x="{972-len(total)*9-10}" y="40" class="tt">Total Contributions:</text>
{months}{labels}{cells}
<text x="28" y="{H-15}" class="f">{foot}</text><text x="788" y="{H-15}" class="f" text-anchor="end">Less</text>{legend}<text x="888" y="{H-15}" class="f">More</text></svg>'''

def languages_svg(langs, repo_count, T):
    W, H = 1000, 200
    items = sorted(langs.items(), key=lambda kv: -kv[1][0])
    tot = sum(v[0] for _, v in items) or 0
    top = items[:5]; rest = tot - sum(v[0] for _, v in top)
    rows = [(n, v[0], v[1]) for n, v in top] + ([("other", rest, "#8089A8")] if rest > 0 and tot else [])
    cx, cy, R, sw = 118, 100, 46, 20
    circ = 2 * math.pi * R
    seg, kf, off = "", "", 0.0
    if tot:
        for i, (n, sz, col) in enumerate(rows):
            ln = sz / tot * circ
            kf += f'@keyframes s{i}{{from{{stroke-dasharray:0 {circ:.2f}}}to{{stroke-dasharray:{max(ln-1.5,0):.2f} {circ:.2f}}}}}'
            seg += f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{col}" stroke-width="{sw}" transform="rotate(-90 {cx} {cy})" stroke-dashoffset="{-off:.2f}" stroke-dasharray="{max(ln-1.5,0):.2f} {circ:.2f}" style="animation:s{i} 1.1s ease-out {i*.12:.2f}s both"/>'
            off += ln
    else:
        seg = f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{T["line"]}" stroke-width="{sw}"/>'
    legend = ""
    for i, (n, sz, col) in enumerate(rows):
        y = 58 + i * 25; pct = sz / tot * 100 if tot else 0
        legend += (f'<circle cx="262" cy="{y-4}" r="5" fill="{col}"/><text x="278" y="{y}" class="n">{esc(n)}</text>'
                   f'<rect x="440" y="{y-9}" width="420" height="6" rx="3" fill="{T["line"]}"/>'
                   f'<rect x="440" y="{y-9}" width="{420*pct/100:.1f}" height="6" rx="3" fill="{col}" class="b" style="animation-delay:{.3+i*.1:.1f}s"/>'
                   f'<text x="972" y="{y}" class="p">{pct:.0f}%</text>')
    if not tot: legend = f'<text x="262" y="104" class="n">Languages appear after the first workflow run.</text>'
    foot = f"Based on {repo_count} public repositories" if tot else ""
    return f'''<svg {NS} viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Top languages across public repositories">
<style>.t{{font-weight:700;font-size:17px;fill:{T["text"]};{SANS}}}.n{{font-size:14px;fill:{T["text"]};{SANS}}}.p{{font-size:13px;fill:{T["mid"]};text-anchor:end;{SANS}}}.f,.m{{font-size:12px;fill:{T["muted"]};{SANS}}}.m{{text-anchor:middle}}
.b{{transform-box:fill-box;transform-origin:left;animation:g .9s ease-out both}}@keyframes g{{from{{transform:scaleX(0)}}to{{transform:none}}}}{kf}{RM}</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{T["card"]}" stroke="{T["line"]}"/>
<text x="28" y="40" class="t">Top languages</text>{seg}<text x="{cx}" y="{cy+4}" class="m">{len(rows) if tot else 0} langs</text>{legend}<text x="28" y="{H-16}" class="f">{foot}</text></svg>'''

def write(cal, langs, repos):
    for name, T in THEMES.items():
        os.makedirs(f"{ROOT}/{name}", exist_ok=True)
        open(f"{ROOT}/{name}/contributions.svg", "w", encoding="utf-8").write(contributions_svg(cal, T))
        open(f"{ROOT}/{name}/languages.svg", "w", encoding="utf-8").write(languages_svg(langs, repos, T))

if __name__ == "__main__":
    if "--empty" in sys.argv: write(None, {}, 0)
    else: write(*fetch())
    print("done")
