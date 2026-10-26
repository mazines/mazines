"""Build the menu bar's status piece: profile views, Wi-Fi, battery, date.

Usage: python3 menubar_status.py <out.svg> [--views N]
A daily GitHub Action (.github/workflows/menubar.yml) runs this and pushes
the result to the `stats` branch, which the README links to. Without
--views, it reads the count from the profile-view counter. That read counts
as one view, so it runs once a day. The date is US Pacific time.
"""
import re
import sys
import urllib.request
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from windows import LIGHT, MENUBAR, menubar_piece

COUNTER = "https://komarev.com/ghpvc/?username=mazzaleen"


def read_views():
    req = urllib.request.Request(COUNTER, headers={"User-Agent": "mazines-menubar"})
    svg = urllib.request.urlopen(req, timeout=30).read().decode()
    # The counter badge's last text element is the count, e.g. "938".
    counts = re.findall(r">\s*([\d,]+)\s*</text>", svg)
    if not counts:
        raise ValueError("no view count in counter response")
    return int(counts[-1].replace(",", ""))


def status_piece(views, date):
    _, _, width = MENUBAR[-1]
    date_x = width - 12            # date, right-aligned
    bx = date_x - 74 - 22          # battery, left of the date
    wx, wy = bx - 16, 15           # Wi-Fi, left of the battery
    # dx offsets space out "|": renderers may drop spaces at tspan edges.
    body = (
        f'<text x="{wx - 20}" y="14" text-anchor="end">'
        f'<tspan fill="#f0f6fc">Profile Views</tspan><tspan dx="6" fill="#6e7681">|</tspan>'
        f'<tspan dx="6" fill="#ff453a" font-weight="700">{views:,}</tspan></text>\n'
        f'<g fill="none" stroke="{LIGHT}" stroke-width="1.5" stroke-linecap="round">'
        f'<path d="M{wx - 7} {wy - 6} A9.5 9.5 0 0 1 {wx + 7} {wy - 6}"/>'
        f'<path d="M{wx - 4.2} {wy - 3.4} A6 6 0 0 1 {wx + 4.2} {wy - 3.4}"/></g>'
        f'<circle cx="{wx}" cy="{wy - 1}" r="1.4" fill="{LIGHT}"/>\n'
        f'<rect x="{bx}" y="5.5" width="19" height="9" rx="2.5" fill="none" stroke="{LIGHT}"/>'
        f'<rect x="{bx + 2}" y="7.5" width="12" height="5" rx="1" fill="{LIGHT}"/>'
        f'<rect x="{bx + 20}" y="8.5" width="1.6" height="3" rx="0.8" fill="{LIGHT}"/>\n'
        f'<text x="{date_x}" y="14" text-anchor="end" fill="#f0f6fc">{escape(date)}</text>'
    )
    return menubar_piece(width, body, left=False, right=True)


if __name__ == "__main__":
    out = sys.argv[1]
    views = int(sys.argv[sys.argv.index("--views") + 1]) if "--views" in sys.argv else read_views()
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    date = f"{now:%a %b} {now.day}"  # e.g. "Mon Oct 26"
    with open(out, "w") as f:
        f.write(status_piece(views, date))
    print(f"{out}: {views:,} views, {date}")
