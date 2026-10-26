"""Build an ASCII-art portrait SVG in a terminal-window frame.

Usage: python3 build.py <photo> <out.svg> [cols]
Needs ImageMagick (`magick`) on PATH to decode the photo.
"""
import subprocess
import sys
from collections import deque
from html import escape

RAMP = " .:-=+*xoX#%&@M"  # sparse -> dense; dense reads bright on dark bg
# Same colors as the portfolio site's .rainbow class; first and last match.
RAINBOW = ["#ff6b6b", "#ffb86b", "#f9f871", "#6bff95", "#6bd6ff", "#b18bff", "#ff6b6b"]
CELL_ASPECT = 0.6         # matches char_w / line_h in to_svg
BG_THRESHOLD = 225        # min(r,g,b) above this counts as white background
HALO_THRESHOLD = 200      # skip light edge pixels when averaging a cell


def read_rgb(path, *ops):
    ppm = subprocess.run(
        ["magick", path, "-alpha", "remove", "-background", "white", *ops,
         "-depth", "8", "-compress", "none", "ppm:-"],
        check=True, capture_output=True, text=True).stdout.split()
    w, h = int(ppm[1]), int(ppm[2])
    vals = list(map(int, ppm[4:]))
    return w, h, [tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)]


def background_mask(w, h, px):
    # Flood fill from the border so white teeth and eyes stay in the subject.
    near_white = [min(p) > BG_THRESHOLD for p in px]
    bg = [False] * (w * h)
    queue = deque(i for i in range(w * h)
                  if (i < w or i >= w * (h - 1) or i % w in (0, w - 1)) and near_white[i])
    for i in queue:
        bg[i] = True
    while queue:
        i = queue.popleft()
        x, y = i % w, i // w
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                j = ny * w + nx
                if near_white[j] and not bg[j]:
                    bg[j] = True
                    queue.append(j)
    return bg


def to_ascii(path, cols):
    w, h, px = read_rgb(path)
    bg = background_mask(w, h, px)
    # Local contrast (CLAHE) brings out eyes, smile, beard on darker skin.
    _, _, eq = read_rgb(path, "-colorspace", "gray", "-clahe", "12x12%+128+2.5")
    luma = [p[0] for p in eq]

    cw = w / cols
    ch = cw / CELL_ASPECT
    rows = int(h / ch)
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x0, x1 = int(c * cw), int((c + 1) * cw)
            y0, y1 = int(r * ch), int((r + 1) * ch)
            idx = [y * w + x for y in range(y0, y1) for x in range(x0, x1)]
            fg = [luma[i] for i in idx if not bg[i]]
            if len(fg) <= len(idx) / 2:
                row.append(None)
                continue
            solid = sorted(luma[i] for i in idx if not bg[i] and min(px[i]) < HALO_THRESHOLD) or sorted(fg)
            if len(fg) < len(idx):
                # Edge cell: the darker half avoids the light anti-aliased rim.
                solid = solid[:max(1, len(solid) // 2)]
            row.append(sum(solid) / len(solid))
        cells.append(row)

    # Equalize brightness over subject cells only, so dark tones keep detail.
    ranked = sorted(v for row in cells for v in row if v is not None)
    n = len(ranked)

    def level(v):
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if ranked[mid] < v:
                lo = mid + 1
            else:
                hi = mid
        return lo / n

    lines = []
    for row in cells:
        line = ""
        for v in row:
            if v is None:
                line += " "
                continue
            # Index 1+ so the darkest subject cells still draw the outline.
            line += RAMP[1 + int(level(v) ** 1.1 * (len(RAMP) - 2))]
        lines.append(line)
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def to_svg(lines, title):
    font = 7
    char_w = font * 0.6
    line_h = font * 1.0
    pad = 22
    bar = 34
    cols = len(lines[0])
    art_w = cols * char_w
    width = int(art_w + pad * 2)
    art_top = bar + pad
    height = int(art_top + len(lines) * line_h + pad)
    mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

    # Browsers drop leading spaces in SVG text even with xml:space, which
    # slides every row to the left. Non-breaking spaces are never dropped.
    text = "\n".join(
        f'<text x="{pad}" y="{art_top + (i + 1) * line_h:.1f}" textLength="{art_w:.1f}" '
        f'lengthAdjust="spacingAndGlyphs">{escape(line).replace(" ", "\u00a0")}</text>'
        for i, line in enumerate(lines))
    stops = "\n".join(
        f'<stop offset="{i / (len(RAINBOW) - 1):.3f}" stop-color="{c}"/>'
        for i, c in enumerate(RAINBOW))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="#0d1117" stroke="#30363d"/>
<circle cx="20" cy="17" r="6" fill="#ff5f56"/>
<circle cx="40" cy="17" r="6" fill="#ffbd2e"/>
<circle cx="60" cy="17" r="6" fill="#27c93f"/>
<text x="{width - 18}" y="21" text-anchor="end" font-family="{mono}" font-size="12" fill="#8b949e">{escape(title)}</text>
<line x1="0" y1="{bar}" x2="{width}" y2="{bar}" stroke="#30363d"/>
<!-- Rainbow fill that moves across the art. The gradient repeats every art
     width and starts and ends on one color, so the loop has no seam. -->
<defs>
<linearGradient id="rainbow" gradientUnits="userSpaceOnUse" x1="{pad}" y1="0" x2="{pad + art_w:.1f}" y2="0" spreadMethod="repeat">
{stops}
<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{art_w:.1f} 0" dur="6s" repeatCount="indefinite"/>
</linearGradient>
</defs>
<g font-family="{mono}" font-size="{font}" fill="url(#rainbow)" xml:space="preserve">
{text}
</g>
</svg>
'''


if __name__ == "__main__":
    photo, out = sys.argv[1], sys.argv[2]
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 80
    art = to_ascii(photo, cols)
    with open(out, "w") as f:
        f.write(to_svg(art, "portrait.txt"))
    print(f"{len(art)} rows x {cols} cols -> {out}")
