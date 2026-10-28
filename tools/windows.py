"""Build terminal-window SVGs for the profile README: intro, tech stack, menu bar.

Usage: python3 windows.py <site_dir> <out_dir>
<site_dir> is a clone of mazines.github.io. The tech stack is read from its
skills page, so the README and the site list the same skills.
Icons are embedded as data URIs, because an SVG shown through <img> cannot
load outside images. The menu bar's status piece (views, date) is built by
menubar_status.py, which a daily GitHub Action runs.
"""
import base64
import itertools
import os
import re
import sys
import textwrap
from html import escape, unescape

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
PAD = 22
BAR = 34          # title bar height
ICON_GAP = 9
COL_GAP = 20
LIGHT = "#d0d7de"

# Single-color icons with no fill of their own draw black; give them brand colors.
FILLS = {
    "dynamodb": "#4053d6",
    "tableau": "#e97627",
    "excel": "#21a366",
}

# Icons whose own colors vanish on the dark window: (old color, new color).
RECOLOR = {
    "heroku": ('fill="currentColor"', 'fill="#9e7cff"'),
    "mysql": ("#00618A", "#4f9fd4"),
    "aws": ("#252f3e", "#f0f6fc"),
}


def data_uri(path):
    name, ext = os.path.splitext(os.path.basename(path))
    if ext == ".png":
        return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()
    svg = open(path).read()
    if name in RECOLOR:
        svg = svg.replace(*RECOLOR[name])
    elif name in FILLS:
        svg = svg.replace("<svg ", f'<svg fill="{FILLS[name]}" ', 1)
    elif "currentColor" in svg:
        # The site colors these with CSS; match its light text color.
        svg = svg.replace("currentColor", LIGHT)
    elif "fill" not in svg:
        svg = svg.replace("<svg ", f'<svg fill="{LIGHT}" ', 1)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def read_skills(site_dir):
    """Return [(section, [(icon_path, dark_logo, name)])] from the site's skills page."""
    html = open(os.path.join(site_dir, "skills", "index.html")).read()
    html = html[:html.index('<nav class="main-nav">')]
    groups = []
    for chunk in html.split('<div class="skill-group">')[1:]:
        title = unescape(re.search(r"<h2>(.*?)</h2>", chunk).group(1)).lower()
        if 'class="lang-note"' in chunk:
            title += " (by proficiency)"
        # Name: the <span> after the icon, or for flags the alt text before " (".
        icons = [(os.path.join(site_dir, src.lstrip("/")), "dark-logo" in cls,
                  unescape(span or alt.split(" (")[0]))
                 for cls, src, alt, span in re.findall(
                     r'<img class="([^"]*)" src="(/assets/icons/[^"]+)" alt="([^"]*)" />(?:<span>([^<]*)</span>)?', chunk)]
        groups.append((title, icons))
    return groups


def window(width, height, title, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="#0d1117" stroke="#30363d"/>
<circle cx="20" cy="17" r="6" fill="#ff5f56"/>
<circle cx="40" cy="17" r="6" fill="#ffbd2e"/>
<circle cx="60" cy="17" r="6" fill="#27c93f"/>
<text x="{width - 18}" y="21" text-anchor="end" font-family="{MONO}" font-size="12" fill="#8b949e">{escape(title)}</text>
<line x1="0" y1="{BAR}" x2="{width}" y2="{BAR}" stroke="#30363d"/>
{body}
</svg>
'''


def split_name(name, max_chars):
    """One line, or two split at a hyphen or space, like the site's wrapping."""
    if len(name) <= max_chars:
        return [name]
    for sep in ("-", " "):
        if sep in name:
            head, tail = name.split(sep, 1)
            return [head + (sep if sep == "-" else ""), tail]
    return [name]


def tech_stack(site_dir, width=804, cols=3, icon=26, label_font=12, name_font=9.5, cell_w=60):
    # Full README width, under the intro and portrait row. Each skill: icon
    # with its name under it, like the site's skills page. name_font 9.5
    # leaves a gap between 10-letter names (Kubernetes) in 60px cells.
    groups = read_skills(site_dir)
    col_w = (width - 2 * PAD - (cols - 1) * COL_GAP) / cols
    per_row = int(col_w // cell_w)
    name_chars = int(cell_w // (name_font * 0.6))
    line_h = name_font + 2

    def rows_of(icons):
        rows = [icons[i:i + per_row] for i in range(0, len(icons), per_row)]
        # Row height: icon, gap, the most name lines in the row, gap below.
        return [(row, icon + 6 + max(len(split_name(n, name_chars)) for *_, n in row) * line_h + 10)
                for row in rows]

    def group_h(icons):
        return 22 + sum(h for _, h in rows_of(icons)) + 8

    # Keep the site's order, filled top to bottom like CSS columns: try every
    # way to cut the list into `cols` runs, keep the one with the shortest
    # tallest column.
    heights = [group_h(icons) for _, icons in groups]
    best = None
    for cuts in itertools.combinations(range(1, len(groups)), cols - 1):
        bounds = (0, *cuts, len(groups))
        tallest = max(sum(heights[a:b]) for a, b in zip(bounds, bounds[1:]))
        if best is None or tallest < best[0]:
            best = (tallest, bounds)
    tallest, bounds = best

    parts = []
    for col, (a, b) in enumerate(zip(bounds, bounds[1:])):
        x0 = PAD + col * (col_w + COL_GAP)
        y = BAR + PAD
        for title, icons in groups[a:b]:
            parts.append(f'<text x="{x0:.1f}" y="{y + 11}" font-family="{MONO}" font-size="{label_font}" '
                         f'fill="#8b949e">~/{escape(title)}</text>')
            y += 22
            for row, row_h in rows_of(icons):
                for c, (path, dark_logo, name) in enumerate(row):
                    cx = x0 + c * cell_w + cell_w / 2
                    ix = cx - icon / 2
                    if dark_logo:
                        # Same fix as the site: near-black marks get a light tile.
                        parts.append(f'<rect x="{ix:.1f}" y="{y}" width="{icon}" height="{icon}" rx="6" fill="#d4d4d4"/>')
                        parts.append(f'<image x="{ix + 4:.1f}" y="{y + 4}" width="{icon - 8}" height="{icon - 8}" '
                                     f'href="{data_uri(path)}"/>')
                    else:
                        parts.append(f'<image x="{ix:.1f}" y="{y}" width="{icon}" height="{icon}" href="{data_uri(path)}"/>')
                    for k, line in enumerate(split_name(name, name_chars)):
                        parts.append(f'<text x="{cx:.1f}" y="{y + icon + 6 + (k + 1) * line_h - 2}" text-anchor="middle" '
                                     f'font-family="{MONO}" font-size="{name_font}" fill="{LIGHT}">{escape(line)}</text>')
                y += row_h
            y += 8
    height = int(BAR + PAD + tallest - 8 + PAD - 10)
    return window(width, height, "tech-stack.txt", "\n".join(parts))


INTRO = [  # (kind, text); kind picks the markdown-style color
    ("h1", "Hi 👋, I'm Mazine Suliman"),
    ("blank", ""),
    ("text", "Software Engineer focused on data systems, privacy-first data platforms, and product discovery."),
    ("text", "SWE → PM with experience turning ambiguous user signals into shipped features and measurable impact."),
    ("blank", ""),
    ("h2", "What I'm working on"),
    ("li", "LLM-driven clustering, summarization, and evaluation"),
    ("li", "Product discovery using qualitative + quantitative customer signals"),
]


def intro(width=400):
    # Sits beside the portrait; the README sizes both from their aspect
    # ratios so they match in height. Long lines soft-wrap like an editor:
    # only the first visual line of each source line gets a line number.
    font = 12
    char_w = font * 0.6
    line_h = 20
    gutter = PAD + 18  # line numbers sit left of this
    chars = int((width - gutter - PAD) / char_w)
    top = BAR + PAD
    parts = []
    row = 0
    for n, (kind, text) in enumerate(INTRO, start=1):
        row += 1
        y = top + row * line_h - 6
        parts.append(f'<text x="{gutter - 12}" y="{y}" text-anchor="end" fill="#484f58">{n}</text>')
        if kind == "blank":
            continue
        marker, color, weight = {
            "h1": ("# ", "#58a6ff", "700"),
            "h2": ("## ", "#58a6ff", "700"),
            "li": ("- ", LIGHT, "400"),
            "text": ("", LIGHT, "400"),
        }[kind]
        # Marker and text are separate, placed by monospace width, because
        # renderers may drop the space between them.
        if marker:
            parts.append(f'<text x="{gutter}" y="{y}" fill="#8b949e">{escape(marker.strip())}</text>')
        tx = gutter + len(marker) * char_w
        for i, line in enumerate(textwrap.wrap(text, chars - len(marker))):
            if i:
                row += 1
                y = top + row * line_h - 6
            parts.append(f'<text x="{tx:.1f}" y="{y}" fill="{color}" font-weight="{weight}">{escape(line)}</text>')
    height = top + row * line_h + PAD - 8
    body = f'<g font-family="{MONO}" font-size="{font}">\n' + "\n".join(parts) + "\n</g>"
    return window(width, height, "intro.md", body)


# Menu bar pieces, left to right: (file name, link label or None, width).
# Each piece is its own image, so each link item is its own <a>. The README
# lays them side by side with no space between, so they read as one bar.
# The last piece comes from menubar_status.py.
MENUBAR = [
    ("menubar-start.svg", None, 92),
    ("menubar-linkedin.svg", "linkedin", 64),
    ("menubar-medium.svg", "medium", 62),
    ("menubar-goodreads.svg", "goodreads", 74),
    ("menubar-twitter.svg", "twitter", 60),
    ("menubar-website.svg", "website", 64),
    ("menubar-end.svg", None, 304),
]
MENU_SANS = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif"


def menubar_piece(width, body, left, right):
    # macOS-style bar piece, 20px tall. The background rect overhangs any
    # side that joins another piece, so only the bar's two outer ends show
    # rounded corners and side borders.
    height = 20
    x0 = 0.5 if left else -10
    x1 = width - 0.5 if right else width + 10
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect x="{x0}" y="0.5" width="{x1 - x0}" height="{height - 1}" rx="5" fill="#1c1c1e" stroke="#30363d"/>
<g font-family="{MENU_SANS}" font-size="12">
{body}
</g>
</svg>
'''


def menubar(site_dir):
    apple = os.path.join(site_dir, "assets", "icons", "apple.svg")
    apple_svg = open(apple).read().replace("<svg ", '<svg fill="#f0f6fc" ', 1)
    apple_uri = "data:image/svg+xml;base64," + base64.b64encode(apple_svg.encode()).decode()
    pieces = {}
    for i, (fname, label, width) in enumerate(MENUBAR[:-1]):
        if i == 0:
            body = (f'<image x="12" y="4" width="12" height="12" href="{apple_uri}"/>\n'
                    f'<text x="34" y="14" font-weight="700" fill="#f0f6fc">mazines</text>')
        else:
            body = f'<text x="{width / 2}" y="14" text-anchor="middle" fill="{LIGHT}">{escape(label)}</text>'
        pieces[fname] = menubar_piece(width, body, left=(i == 0), right=False)
    return pieces


if __name__ == "__main__":
    site_dir, out = sys.argv[1], sys.argv[2]
    outputs = {
        "intro.svg": intro(),
        "tech-stack.svg": tech_stack(site_dir),
    }
    outputs.update(menubar(site_dir))
    for fname, svg in outputs.items():
        with open(os.path.join(out, fname), "w") as f:
            f.write(svg)
        print(f"{fname}: {len(svg) // 1024} KB")
