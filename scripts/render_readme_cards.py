#!/usr/bin/env python3
"""
Render the animated SVG cards for the GitHub profile README.

Reads data/contributions.json (refreshed daily by fetch_contributions.py)
and writes every card into cards/.

  python scripts/render_readme_cards.py            # animated cards
  STATIC=1 python scripts/render_readme_cards.py   # final frame only (for screenshots)

Everything that can be shown through an <img> tag only: an inline <style>
block with CSS keyframes and fonts embedded as base64 WOFF data URIs.
All motion turns off under prefers-reduced-motion.
"""
import base64
import datetime as dt
import html
import json
import math
import os
from collections import defaultdict
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
CARDS = ROOT / "cards"
DATA = ROOT / "data" / "contributions.json"
STATIC = os.environ.get("STATIC") == "1"

# ─────────────────────────── edit me ───────────────────────────
CONFIG = {
    "first_name": "Ege",
    "last_name": "Efes",                # capital letters in the name are green
    "tag": "COMPUTER SCIENCE & CYBERSECURITY · UCD",
    "about": "Student Leader at UCD College of Science",
    "site": "egeefes.com",
    "monogram": "E",                    # used when there is no portrait.png / portrait.jpg
    "tiles": [
        # stat: repos | total | active_days | streak | longest_streak
        {"file": "build", "num": "01", "word": "Build", "stat": "repos",
         "unit": "public repos", "caption": "WebDrop, SocSync and other things for UCD students"},
        {"file": "learn", "num": "02", "word": "Learn", "stat": "total",
         "unit": "contributions this year", "caption": "Computer Science & Cybersecurity at University College Dublin"},
        {"file": "lead", "num": "03", "word": "Lead", "stat": "longest_streak",
         "unit": "day best streak", "caption": "Student Leader, UCD College of Science · Teaching Assistant"},
    ],
}
# ───────────────────────────────────────────────────────────────

# Palette: paper + ink + green
PAPER = "#fbf9f4"
EDGE = "#e5e0d3"
INK = "#1b1d1a"
MUTED = "#6b6f66"
FAINT = "#d8d3c5"
GREEN = "#1a7f37"
GREEN_BRIGHT = "#2ea043"
GRAPH = ["#ebe7dc", "#c0e3b4", "#7cc768", "#2ea043", "#196c2e"]
TILE_THEMES = [
    {"bg": GREEN_BRIGHT, "fg": "#ffffff", "soft": "rgba(255,255,255,.72)", "ring": "#ffffff"},
    {"bg": "#b9e39c", "fg": INK, "soft": "rgba(27,29,26,.68)", "ring": "#1a7f37"},
    {"bg": "#0f3d24", "fg": "#f3f1ea", "soft": "rgba(243,241,234,.7)", "ring": "#7cc768"},
]

# ─────────────────────────── fonts ───────────────────────────
FONT_FILES = {
    "serif": ("Instrument Serif", "serif-400.woff", "normal", 400),
    "serif-i": ("Instrument Serif", "serif-400-italic.woff", "italic", 400),
    "sans": ("Geist", "geist-400.woff", "normal", 400),
    "sans-m": ("Geist", "geist-500.woff", "normal", 500),
    "mono": ("Geist Mono", "geist-mono-400.woff", "normal", 400),
}
_metrics = {}


def font_css(keys):
    out = []
    for k in keys:
        fam, fn, style, weight = FONT_FILES[k]
        b64 = base64.b64encode((FONTS / fn).read_bytes()).decode()
        out.append(f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
                   f"src:url(data:font/woff;base64,{b64}) format('woff')}}")
    return "".join(out)


def text_width(text, key, size):
    if key not in _metrics:
        f = TTFont(FONTS / FONT_FILES[key][1])
        _metrics[key] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    w = 0
    for ch in text:
        g = cmap.get(ord(ch))
        w += hmtx[g][0] if g in hmtx else upm * 0.5
    return w * size / upm


def wrap(text, key, size, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if text_width(trial, key, size) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return html.escape(str(s), quote=True)


# ─────────────────────────── shared css ───────────────────────────
BASE_CSS = f"""
.serif{{font-family:'Instrument Serif',Georgia,serif}}
.ital{{font-family:'Instrument Serif',Georgia,serif;font-style:italic}}
.sans{{font-family:'Geist',-apple-system,'Segoe UI',sans-serif}}
.med{{font-family:'Geist',-apple-system,'Segoe UI',sans-serif;font-weight:500}}
.mono{{font-family:'Geist Mono',ui-monospace,Menlo,monospace}}
.fb{{transform-box:fill-box}}
.frame{{opacity:0}}
.a-shine{{opacity:0}}
"""

ANIM_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(26px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{0%{opacity:0;transform:scale(0)}70%{opacity:1;transform:scale(1.25)}100%{opacity:1;transform:scale(1)}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes swing{0%{opacity:0;transform:translateY(120px) rotate(-7deg)}60%{opacity:1;transform:translateY(-10px) rotate(1.5deg)}80%{transform:translateY(3px) rotate(-.5deg)}100%{opacity:1;transform:none}}
@keyframes shine{0%{opacity:1;transform:translateX(-160%) skewX(-18deg)}22%,100%{opacity:1;transform:translateX(260%) skewX(-18deg)}}
@keyframes flash{0%,100%{opacity:1}}
@keyframes pulse{0%{opacity:.9;transform:scale(1)}80%,100%{opacity:0;transform:scale(2.6)}}
@keyframes beat{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes nudge{0%,80%,100%{transform:none}88%{transform:translate(4px,-4px)}}
.a-rise{animation:rise .9s cubic-bezier(.2,.8,.2,1) both}
.a-fade{animation:fade .5s ease-out both}
.a-pop{animation:pop .45s cubic-bezier(.2,.8,.2,1) both;transform-origin:center}
.a-grow{animation:grow .8s cubic-bezier(.2,.8,.2,1) both;transform-origin:bottom}
.a-swing{animation:swing 1.15s cubic-bezier(.2,.8,.2,1) both;transform-origin:center bottom}
.a-shine{animation:shine 5s ease-in-out infinite}
.a-pulse{animation:pulse 2.4s ease-out infinite;transform-origin:center}
.a-beat{animation:beat 1.6s ease-in-out infinite}
.a-nudge{animation:nudge 3s ease-in-out infinite}
.frame{animation:flash 70ms linear 1 none}
.final{animation:fade 80ms linear both}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def svg(w, h, fonts, body, extra_css=""):
    css = font_css(fonts) + BASE_CSS + ("" if STATIC else ANIM_CSS) + extra_css
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img"><style>{css}</style>{body}</svg>\n')


def d(sec):
    """inline animation-delay"""
    return f'style="animation-delay:{sec:.3f}s"'


def card_bg(w, h, r=18, fill=PAPER, stroke=EDGE):
    return f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


# ─────────────────────────── stats ───────────────────────────
def load():
    data = json.loads(DATA.read_text())
    days = sorted(data["days"], key=lambda x: x["date"])
    for x in days:
        x["d"] = dt.date.fromisoformat(x["date"])
    total = sum(x["count"] for x in days)
    active = sum(1 for x in days if x["count"] > 0)
    longest = run = 0
    for x in days:
        run = run + 1 if x["count"] > 0 else 0
        longest = max(longest, run)
    cur = 0
    for i, x in enumerate(reversed(days)):
        if x["count"] > 0:
            cur += 1
        elif i == 0:  # today not yet active doesn't break a streak
            continue
        else:
            break
    busiest = max(days, key=lambda x: x["count"])
    months = defaultdict(int)
    for x in days:
        months[(x["d"].year, x["d"].month)] += x["count"]
    stats = {
        "total": total, "active_days": active, "streak": cur, "longest_streak": longest,
        "repos": data.get("public_repos", 0), "busiest": busiest,
    }
    return data, days, stats, months


def count_up(value, x, y, cls, size, fill, start, anchor="start"):
    """Count from 0 to value: 18 frames, each a text element flashed for ~70ms (CSS can't change text)."""
    frames = 18
    out = []
    for i in range(frames):
        t = i / (frames - 1)
        v = round(value * (1 - (1 - t) ** 3))
        delay = start + i * 0.07
        last = i == frames - 1
        out.append(f'<text x="{x}" y="{y}" class="{cls} {"final" if last else "frame"}" font-size="{size}" '
                   f'fill="{fill}" text-anchor="{anchor}" {d(delay)}>{v:,}</text>')
    return "".join(out)


# ─────────────────────────── hero ───────────────────────────
RAMP = " .:-=+*#%@"


def ascii_art(cols=70, rows=50):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    src = next((p for p in (ROOT / "portrait.png", ROOT / "portrait.jpg") if p.exists()), None)
    if src:
        img = ImageOps.grayscale(Image.open(src))
        img = ImageOps.autocontrast(img)
    else:  # monogram: a big italic letter with a soft halo
        img = Image.new("L", (600, 760), 255)
        bg = ImageDraw.Draw(img)  # soft radial halo so the letter sits in a texture
        for r in range(330, 0, -6):
            bg.ellipse((300 - r, 380 - r * 1.15, 300 + r, 380 + r * 1.15), fill=int(255 - 70 * (1 - r / 330) ** 1.6))
        dr = ImageDraw.Draw(img)
        ttf = Path("/tmp/_mono.ttf")
        f = TTFont(FONTS / FONT_FILES["serif-i"][1]); f.flavor = None; f.save(ttf)
        font = ImageFont.truetype(str(ttf), 900)
        bbox = dr.textbbox((0, 0), CONFIG["monogram"], font=font)
        dr.text(((600 - (bbox[2] - bbox[0])) / 2 - bbox[0], (760 - (bbox[3] - bbox[1])) / 2 - bbox[1]),
                CONFIG["monogram"], font=font, fill=0)
    img = img.resize((cols, rows))
    px = img.load()
    lines = []
    for yy in range(rows):
        lines.append("".join(RAMP[min(len(RAMP) - 1, int((255 - px[xx, yy]) / 256 * len(RAMP)))] for xx in range(cols)))
    return lines


def hero(stats):
    W, H = 840, 350
    first, last = CONFIG["first_name"], CONFIG["last_name"]
    size = 104
    while max(text_width(first, "serif", size), text_width(last, "serif-i", size)) > 450:
        size -= 2
    y1, y2 = 70 + size * 0.86, 70 + size * 1.78
    b = [card_bg(W, H)]
    # tag
    b.append(f'<g class="a-fade" {d(0.0)}><circle cx="46" cy="44" r="4" fill="{GREEN_BRIGHT}" class="a-beat"/>'
             f'<text x="58" y="48" class="mono" font-size="11.5" letter-spacing="1.6" fill="{MUTED}">{esc(CONFIG["tag"])}</text></g>')
    # name: capital letters in green (with a shine), the rest in ink
    clip = []

    def name_line(text, key, cls, y, delay):
        parts, x = [], 38.0
        for ch in text:
            col = GREEN if ch.isupper() else INK
            if parts and parts[-1][1] == col:
                parts[-1][0] += ch
            else:
                parts.append([ch, col, x])
            x += text_width(ch, key, size)
        out = [f'<g class="a-rise" {d(delay)}>']
        for seg, col, sx in parts:
            out.append(f'<text x="{sx:.1f}" y="{y:.0f}" class="{cls}" font-size="{size}" fill="{col}">{esc(seg)}</text>')
            if col == GREEN:
                w = text_width(seg, key, size)
                clip.append(f'<text x="{sx:.1f}" y="{y:.0f}" class="{cls}" font-size="{size}">{esc(seg)}</text>')
                out.append(f'<g clip-path="url(#capclip)"><rect class="a-shine" x="{sx:.1f}" y="{y - size:.0f}" '
                           f'width="{max(w * 0.6, 30):.0f}" height="{size * 1.2:.0f}" fill="url(#sh)" '
                           f'style="animation-delay:{2.2 + delay:.2f}s"/></g>')
        out.append('</g>')
        return "".join(out)

    b.append(name_line(first, "serif", "serif", y1, 0.15))
    b.append(name_line(last, "serif-i", "ital", y2, 0.4))
    # about + link
    lines = wrap(CONFIG["about"], "sans", 15, 440)
    for i, ln in enumerate(lines[:2]):
        b.append(f'<text x="40" y="{y2 + 46 + i * 22:.0f}" class="sans a-fade" font-size="15" fill="{MUTED}" {d(0.8 + i * .1)}>{esc(ln)}</text>')
    link_y = y2 + 46 + len(lines[:2]) * 22 + 6
    b.append(f'<text x="40" y="{link_y:.0f}" class="med a-fade" font-size="13.5" fill="{GREEN}" {d(1.1)}>{esc(CONFIG["site"])} ↗</text>')
    # ascii portrait
    art = ascii_art()
    fs, lh = 6.4, 6.55
    ax, ay = W - 40 - len(art[0]) * fs * 0.6, 28
    rows = []
    for i, row in enumerate(art):
        if not row.strip():
            continue
        rows.append(f'<text x="{ax:.1f}" y="{ay + i * lh:.1f}" xml:space="preserve" class="a-fade" '
                    f'style="animation-delay:{0.3 + i * 0.018:.3f}s;animation-duration:.25s">{esc(row)}</text>')
    b.append(f'<g class="mono" font-size="{fs}" fill="{INK}" fill-opacity=".82">{"".join(rows)}</g>')
    defs = (f'<defs><linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="#e9ffe0" stop-opacity=".95"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="capclip">{"".join(clip)}</clipPath></defs>')
    return svg(W, H, ["serif", "serif-i", "sans", "sans-m", "mono"], defs + "".join(b))


# ─────────────────────────── contribution graph ───────────────────────────
def graph(days, stats):
    W, H = 840, 210
    cell, gap = 11, 3
    step = cell + gap
    last = days[-1]["d"]
    start = last - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    counts = {x["d"]: x["count"] for x in days}
    nz = sorted(c for c in counts.values() if c > 0) or [1]
    q = [nz[int(len(nz) * p)] for p in (0.25, 0.5, 0.75)]

    def level(c):
        if c <= 0:
            return 0
        return 1 + sum(c > t for t in q)

    gx, gy = 48, 86
    b = [card_bg(W, H)]
    b.append(f'<text x="40" y="44" class="serif a-rise" font-size="28" fill="{INK}" {d(0.9)}>'
             f'{stats["total"]:,} <tspan class="ital" fill="{GREEN}">contributions</tspan> in the last year</text>')
    b.append(f'<text x="{W - 40}" y="42" class="mono a-fade" font-size="11" letter-spacing="1.4" fill="{MUTED}" text-anchor="end" {d(1.0)}>'
             f'UPDATED {last.strftime("%d %b %Y").upper()}</text>')
    cells, months_seen = [], set()
    day = start
    week = 0
    while day <= last:
        wd = (day.weekday() + 1) % 7
        if wd == 0 and day.day <= 7 and (day.year, day.month) not in months_seen:
            months_seen.add((day.year, day.month))
            b.append(f'<text x="{gx + week * step}" y="{gy - 10}" class="mono" font-size="10" fill="{MUTED}">{day.strftime("%b")}</text>')
        c = counts.get(day, 0)
        cells.append(f'<rect x="{gx + week * step}" y="{gy + wd * step}" width="{cell}" height="{cell}" rx="2.5" '
                     f'fill="{GRAPH[level(c)]}" class="fb a-pop" {d(1.2 + week * 0.03 + wd * 0.006)}/>')
        if wd == 6:
            week += 1
        day += dt.timedelta(days=1)
    b.append("".join(cells))
    lx = W - 40 - 5 * step - 34
    leg = [f'<text x="{lx - 8}" y="{H - 18}" class="mono" font-size="10" fill="{MUTED}" text-anchor="end">less</text>']
    for i, col in enumerate(GRAPH):
        leg.append(f'<rect x="{lx + i * step}" y="{H - 27}" width="{cell}" height="{cell}" rx="2.5" fill="{col}"/>')
    leg.append(f'<text x="{lx + 5 * step + 4}" y="{H - 18}" class="mono" font-size="10" fill="{MUTED}">more</text>')
    b.append(f'<g class="a-fade" {d(2.6)}>{"".join(leg)}</g>')
    return svg(W, H, ["serif", "serif-i", "mono"], "".join(b))


# ─────────────────────────── monthly bars ───────────────────────────
def months_card(days, stats, months):
    W, H = 840, 260
    last = days[-1]["d"]
    keys = []
    y, m = last.year, last.month
    for _ in range(12):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    vals = [months.get(k, 0) for k in keys]
    best = max(range(12), key=lambda i: vals[i])
    top = max(vals) or 1
    b = [card_bg(W, H)]
    # stats column
    busiest = stats["busiest"]
    rows = [
        ("CURRENT STREAK", f'{stats["streak"]} days'),
        ("ACTIVE DAYS", f'{stats["active_days"]} / 365'),
        ("BUSIEST DAY", f'{busiest["count"]} on {busiest["d"].strftime("%-d %b")}'),
    ]
    for i, (k, v) in enumerate(rows):
        yy = 58 + i * 66
        b.append(f'<g class="a-rise" {d(2.3 + i * 0.12)}>'
                 f'<text x="40" y="{yy}" class="mono" font-size="10.5" letter-spacing="1.5" fill="{MUTED}">{k}</text>'
                 f'<text x="40" y="{yy + 32}" class="serif" font-size="32" fill="{INK}">{esc(v)}</text></g>')
    b.append(f'<line x1="268" y1="34" x2="268" y2="{H - 34}" stroke="{EDGE}" stroke-width="1.5"/>')
    # bars
    bx0, bx1, base, maxh = 300, W - 40, H - 46, 150
    slot = (bx1 - bx0) / 12
    bw = slot * 0.56
    for i, (k, v) in enumerate(zip(keys, vals)):
        h = max(3, v / top * maxh)
        x = bx0 + i * slot + (slot - bw) / 2
        col = GREEN_BRIGHT if i == best else FAINT
        b.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="4" fill="{col}" '
                 f'class="fb a-grow" {d(2.5 + i * 0.07)}/>')
        lab = dt.date(k[0], k[1], 1).strftime("%b")
        b.append(f'<text x="{x + bw / 2:.1f}" y="{base + 20}" class="mono" font-size="10" fill="{GREEN if i == best else MUTED}" '
                 f'text-anchor="middle">{lab}</text>')
        if i == best:
            b.append(f'<text x="{x + bw / 2:.1f}" y="{base - h - 10:.1f}" class="serif fb a-pop" font-size="22" fill="{GREEN}" '
                     f'text-anchor="middle" {d(3.5)}>{v:,}</text>')
    b.append(f'<line x1="{bx0}" y1="{base + .5}" x2="{bx1}" y2="{base + .5}" stroke="{EDGE}" stroke-width="1.5"/>')
    return svg(W, H, ["serif", "mono"], "".join(b))


# ─────────────────────────── tiles ───────────────────────────
def tile(cfg, theme, stats, idx):
    W, H = 400, 330
    start = 3.2 + idx * 0.18
    fg, soft = theme["fg"], theme["soft"]
    value = stats[cfg["stat"]]
    b = [f'<g class="a-swing fb" {d(start)}>',
         f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="22" fill="{theme["bg"]}"/>',
         f'<g clip-path="url(#tc)"><rect class="a-shine" x="8" y="0" width="120" height="{H}" fill="url(#ts)" '
         f'style="animation-delay:{start + 2.2:.2f}s;animation-duration:6s"/></g>',
         f'<text x="36" y="52" class="mono" font-size="12" letter-spacing="1.8" fill="{soft}">{cfg["num"]} / {cfg["word"].upper()}</text>',
         f'<g class="a-nudge" style="animation-delay:{start + 1.4:.2f}s"><text x="{W - 36}" y="56" class="sans" font-size="24" '
         f'fill="{fg}" text-anchor="end">↗</text></g>',
         f'<text x="34" y="138" class="ital" font-size="68" fill="{fg}">{cfg["word"]}</text>',
         count_up(value, 34, 220, "serif", 64, fg, start + 0.7),
         f'<text x="36" y="246" class="mono" font-size="11" letter-spacing="1.2" fill="{soft}">{esc(cfg["unit"].upper())}</text>']
    for i, ln in enumerate(wrap(cfg["caption"], "sans", 14, W - 80)[:2]):
        b.append(f'<text x="36" y="{280 + i * 20}" class="sans" font-size="14" fill="{fg}">{esc(ln)}</text>')
    b.append("</g>")
    defs = (f'<defs><clipPath id="tc"><rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="22"/></clipPath>'
            f'<linearGradient id="ts" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>')
    return svg(W, H, ["serif", "serif-i", "sans", "mono"], defs + "".join(b))


# ─────────────────────────── repos ───────────────────────────
def repo_card(repo, idx):
    W, H = 412, 176
    start = 4.2 + idx * 0.15
    b = [f'<g class="a-rise" {d(start)}>', card_bg(W, H),
         f'<text x="28" y="40" class="mono" font-size="10.5" letter-spacing="1.6" fill="{MUTED}">NOW CODING</text>',
         f'<text x="{W - 28}" y="44" class="sans" font-size="20" fill="{GREEN}" text-anchor="end">↗</text>']
    name = repo["name"]
    size = 32
    while text_width(name, "serif", size) > W - 80 and size > 18:
        size -= 1
    b.append(f'<text x="26" y="82" class="serif" font-size="{size}" fill="{INK}">{esc(name)}</text>')
    for i, ln in enumerate(wrap(repo.get("description") or "No description yet.", "sans", 13.5, W - 56)[:2]):
        b.append(f'<text x="28" y="{110 + i * 19}" class="sans" font-size="13.5" fill="{MUTED}">{esc(ln)}</text>')
    lang = repo.get("language")
    meta_x = 28
    if lang:
        b.append(f'<circle cx="{meta_x + 5}" cy="{H - 28}" r="5" fill="{repo.get("language_color") or GREEN_BRIGHT}"/>')
        b.append(f'<text x="{meta_x + 16}" y="{H - 24}" class="mono" font-size="11.5" fill="{INK}">{esc(lang)}</text>')
        meta_x += 16 + text_width(lang, "mono", 11.5) + 22
    b.append(f'<text x="{meta_x}" y="{H - 24}" class="mono" font-size="11.5" fill="{INK}">★ {repo.get("stars", 0)}</text>')
    b.append("</g>")
    return svg(W, H, ["serif", "sans", "mono"], "".join(b))


# ─────────────────────────── main ───────────────────────────
def main():
    CARDS.mkdir(exist_ok=True)
    data, days, stats, months = load()
    out = {
        "hero.svg": hero(stats),
        "graph.svg": graph(days, stats),
        "activity.svg": months_card(days, stats, months),
    }
    for i, t in enumerate(CONFIG["tiles"]):
        out[f'{t["file"]}.svg'] = tile(t, TILE_THEMES[i % 3], stats, i)
    for old in CARDS.glob("repo-*.svg"):
        old.unlink()
    for i, r in enumerate(data.get("repos", [])[:4]):
        out[f"repo-{i + 1}.svg"] = repo_card(r, i)
    for fn, s in out.items():
        (CARDS / fn).write_text(s, encoding="utf-8")
        print(f"cards/{fn}  {len(s) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
