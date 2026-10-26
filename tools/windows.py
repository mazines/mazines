"""Build terminal-window SVGs for the profile README: tech stack, connect cards.

Usage: python3 windows.py <icons_dir> <extra_icons_dir> <out_dir>
Icons are embedded as data URIs, because an SVG shown through <img> cannot
load outside images.
"""
import base64
import os
import sys
from html import escape

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
WIDTH = 548       # same width as portrait.svg
PAD = 22
BAR = 34          # title bar height
ICON = 32
ICON_GAP = 9
COL_GAP = 20

# Single-color icons with no fill of their own draw black; give them brand colors.
FILLS = {
    "dynamodb": "#4053d6",
    "tableau": "#e97627",
    "excel": "#21a366",
    "confluence": "#2684ff",
    "linkedin": "#0a66c2",
    "medium": "#f0f6fc",
}

# Icons whose own colors vanish on the dark window: (old color, new color).
RECOLOR = {
    "heroku": ('fill="currentColor"', 'fill="#9e7cff"'),
    "apachekafka": ("#231f20", "#f0f6fc"),
    "mysql": ("#00618A", "#4f9fd4"),
    "aws": ("#252f3e", "#f0f6fc"),
}

STACK = [  # (column, section, icons)
    (0, "back-end", ["python", "ruby", "java", "graphql"]),
    (0, "databases", ["postgresql", "mysql", "mongodb", "redis", "apachecassandra", "dynamodb"]),
    (0, "analytics & observability", ["tableau", "splunk", "grafana"]),
    (0, "data science & ml", ["tensorflow", "pytorch", "matlab", "excel"]),
    (0, "mobile", ["swift"]),
    (1, "front-end", ["rubyonrails", "angular", "react", "javascript", "html5", "css3", "bootstrap", "sass"]),
    (1, "devops", ["aws", "docker", "kubernetes", "jenkins", "heroku", "apachekafka"]),
    (1, "product management", ["miro", "figma", "confluence", "jira", "trello", "firebase", "googleanalytics"]),
    (1, "version control", ["git"]),
]


def icon_uri(name, dirs):
    for d in dirs:
        path = os.path.join(d, name + ".svg")
        if os.path.exists(path):
            svg = open(path).read()
            if name in RECOLOR:
                svg = svg.replace(*RECOLOR[name])
            if name in FILLS:
                svg = svg.replace("<svg ", f'<svg fill="{FILLS[name]}" ', 1)
            return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    raise FileNotFoundError(name)


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


def tech_stack(dirs, width=420, icon=28):
    # 420 wide: sits beside the portrait column in the README, about as tall.
    col_w = (width - 2 * PAD - COL_GAP) / 2
    per_row = int((col_w + ICON_GAP) // (icon + ICON_GAP))
    y = [BAR + PAD, BAR + PAD]
    parts = []
    for col, section, icons in STACK:
        x0 = PAD + col * (col_w + COL_GAP)
        parts.append(f'<text x="{x0}" y="{y[col] + 10}" font-family="{MONO}" font-size="12" '
                     f'fill="#8b949e">~/{escape(section)}</text>')
        y[col] += 20
        for i, name in enumerate(icons):
            r, c = divmod(i, per_row)
            parts.append(f'<image x="{x0 + c * (icon + ICON_GAP):.1f}" y="{y[col] + r * (icon + ICON_GAP)}" '
                         f'width="{icon}" height="{icon}" href="{icon_uri(name, dirs)}"/>')
        rows = (len(icons) + per_row - 1) // per_row
        y[col] += rows * (icon + ICON_GAP) + 14
    height = int(max(y) - 14 + PAD)
    return window(width, height, "tech-stack.txt", "\n".join(parts))


def connect_card(name, label, dirs):
    width = (WIDTH - 8) // 2  # two cards side by side, with a small gap
    height = BAR + 2 * 18 + ICON
    top = BAR + 18
    body = (f'<image x="{PAD}" y="{top}" width="{ICON}" height="{ICON}" href="{icon_uri(name, dirs)}"/>\n'
            f'<text x="{PAD + ICON + 12}" y="{top + ICON / 2 + 4}" font-family="{MONO}" font-size="13" '
            f'fill="#d0d7de">{escape(label)}</text>')
    return window(width, height, name, body)


FULL_WIDTH = 804  # both README columns: 400 + gap + 400

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


def intro():
    font = 12
    line_h = 20
    gutter = PAD + 18  # line numbers sit left of this
    top = BAR + PAD
    parts = []
    for n, (kind, text) in enumerate(INTRO, start=1):
        y = top + n * line_h - 6
        parts.append(f'<text x="{gutter - 12}" y="{y}" text-anchor="end" fill="#484f58">{n}</text>')
        if kind == "blank":
            continue
        marker, color, weight = {
            "h1": ("# ", "#58a6ff", "700"),
            "h2": ("## ", "#58a6ff", "700"),
            "li": ("- ", "#d0d7de", "400"),
            "text": ("", "#d0d7de", "400"),
        }[kind]
        # Marker and text are separate, placed by monospace width, because
        # renderers may drop the space between them.
        if marker:
            parts.append(f'<text x="{gutter}" y="{y}" fill="#8b949e">{escape(marker.strip())}</text>')
        tx = gutter + len(marker) * font * 0.6
        parts.append(f'<text x="{tx:.1f}" y="{y}" fill="{color}" font-weight="{weight}">{escape(text)}</text>')
    height = top + len(INTRO) * line_h + PAD - 8
    body = f'<g font-family="{MONO}" font-size="{font}">\n' + "\n".join(parts) + "\n</g>"
    return window(FULL_WIDTH, height, "intro.md", body)


# Menu bar pieces, left to right: (file name, link label or None, width).
# Each piece is its own image, so each link item is its own <a>. The README
# lays them side by side with no space between, so they read as one bar.
MENUBAR = [
    ("menubar-start.svg", None, 92),
    ("menubar-linkedin.svg", "linkedin ↗", 78),
    ("menubar-medium.svg", "medium ↗", 76),
    ("menubar-website.svg", "website ↗", 78),
    ("menubar-end.svg", None, 396),
]
MENU_SANS = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif"


def menubar_piece(width, body, left, right):
    # macOS-style bar piece, 20px tall to match the profile-views badge.
    # The background rect overhangs any side that joins another piece, so
    # only the bar's two outer ends show rounded corners and side borders.
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


def menubar(dirs):
    apple = open(os.path.join(dirs[0], "apple.svg")).read().replace("<svg ", '<svg fill="#f0f6fc" ', 1)
    apple_uri = "data:image/svg+xml;base64," + base64.b64encode(apple.encode()).decode()
    pieces = {}
    last = len(MENUBAR) - 1
    for i, (fname, label, width) in enumerate(MENUBAR):
        if i == 0:
            body = (f'<image x="12" y="4" width="12" height="12" href="{apple_uri}"/>\n'
                    f'<text x="34" y="14" font-weight="700" fill="#f0f6fc">mazines</text>')
        elif i == last:
            # Wi-Fi, battery at the right end, like menu bar status items.
            bx = width - 34
            wx, wy = bx - 18, 15
            body = (f'<rect x="{bx}" y="5.5" width="19" height="9" rx="2.5" fill="none" stroke="#d0d7de"/>'
                    f'<rect x="{bx + 2}" y="7.5" width="12" height="5" rx="1" fill="#d0d7de"/>'
                    f'<rect x="{bx + 20}" y="8.5" width="1.6" height="3" rx="0.8" fill="#d0d7de"/>\n'
                    f'<g fill="none" stroke="#d0d7de" stroke-width="1.5" stroke-linecap="round">'
                    f'<path d="M{wx - 7} {wy - 6} A9.5 9.5 0 0 1 {wx + 7} {wy - 6}"/>'
                    f'<path d="M{wx - 4.2} {wy - 3.4} A6 6 0 0 1 {wx + 4.2} {wy - 3.4}"/></g>'
                    f'<circle cx="{wx}" cy="{wy - 1}" r="1.4" fill="#d0d7de"/>')
        else:
            body = f'<text x="{width / 2}" y="14" text-anchor="middle" fill="#d0d7de">{escape(label)}</text>'
        pieces[fname] = menubar_piece(width, body, left=(i == 0), right=(i == last))
    return pieces


if __name__ == "__main__":
    icons_dir, extra_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    dirs = [icons_dir, extra_dir]
    outputs = {
        "intro.svg": intro(),
        "tech-stack.svg": tech_stack(dirs),
        "connect-linkedin.svg": connect_card("linkedin", "in/mazines", dirs),
        "connect-medium.svg": connect_card("medium", "@mazines", dirs),
    }
    outputs.update(menubar(dirs))
    for fname, svg in outputs.items():
        with open(os.path.join(out, fname), "w") as f:
            f.write(svg)
        print(f"{fname}: {len(svg) // 1024} KB")
