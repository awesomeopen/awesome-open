"""Write the interface icon SVGs listed in site/brand/icons.json.

Each icon is drawn per size (12, 16, 24 px) from the shapes in brand/icons.md,
with whole-pixel strokes and straight lines snapped to the pixel grid. Structure
uses currentColor; the accent part (check, cross, dash, badge) uses
var(--icon-accent, currentColor) so CSS can apply the map's token to it.
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "site/brand/icons.json"
OUTPUT = ROOT / "site/brand/icons"
ACCENT = "var(--icon-accent, currentColor)"
# size: (px, stroke, padding, tick length)
SIZES = {"s": (12, 1, 1, 1), "m": (16, 2, 1, 1), "l": (24, 2, 2, 3)}
ACCENT_WIDTH = {12: 1, 16: 1.5, 24: 2}


def n(value):
    return f"{round(value, 3):g}"


def snap(value, width):
    """Centre a stroke of `width` on whole pixels: odd widths on .5, even on integers."""
    return math.floor(value) + 0.5 if round(width) % 2 else round(value)


class Pen:
    def __init__(self, size, stroke, pad, tick):
        self.S, self.w, self.p, self.t = size, stroke, pad, tick
        self.c = size / 2
        self.parts, self.defs = [], []

    def stroke(self, colour, width):
        return f'fill="none" style="stroke:{colour}" stroke-width="{n(width)}"'

    def line(self, points, width=None, colour="currentColor", closed=False, cap=""):
        width = width or self.w
        pts = [(snap(x, width), snap(y, width)) for x, y in points]
        d = "M" + " L".join(f"{n(x)} {n(y)}" for x, y in pts) + (" Z" if closed else "")
        self.parts.append(f'<path d="{d}" {self.stroke(colour, width)}{cap}/>')

    def free(self, points, width=None, colour="currentColor"):
        """Unsnapped polyline for diagonals."""
        d = "M" + " L".join(f"{n(x)} {n(y)}" for x, y in points)
        self.parts.append(f'<path d="{d}" {self.stroke(colour, width or self.w)}/>')

    def path(self, d, width=None, colour="currentColor", extra=""):
        self.parts.append(f'<path d="{d}" {self.stroke(colour, width or self.w)}{extra}/>')

    def fill(self, d, colour="currentColor"):
        self.parts.append(f'<path d="{d}" style="fill:{colour}"/>')

    def circle(self, cx, cy, r, width=None, colour="currentColor", extra=""):
        self.parts.append(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" {self.stroke(colour, width or self.w)}{extra}/>')

    def dot(self, cx, cy, r, colour="currentColor"):
        self.parts.append(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" style="fill:{colour}"/>')

    def rect(self, x, y, w, h, colour="currentColor"):
        self.parts.append(f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" style="fill:{colour}"/>')

    def svg(self, title):
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.S}" height="{self.S}" viewBox="0 0 {self.S} {self.S}" '
                f'stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true">'
                f"<title>{title}</title>{defs}{''.join(self.parts)}</svg>\n")


# Ring family: a ring inside four registration ticks.

def ticks(p):
    a, t = p.p, p.t
    k = 2  # tick width; even, so ticks centre on the canvas midline
    c = p.c
    p.rect(c - k / 2, a, k, t)
    p.rect(c - k / 2, p.S - a - t, k, t)
    p.rect(a, c - k / 2, t, k)
    p.rect(p.S - a - t, c - k / 2, t, k)


def ring_radius(p):
    outer = p.c - p.p - p.t
    return outer - p.w / 2, outer - p.w


def ring(p, dashes=0):
    r, inner = ring_radius(p)
    extra = ""
    if dashes:
        step = 2 * math.pi * r / dashes
        dash, gap = step * 0.6, step * 0.4
        # Start mid-gap at 3 o'clock so gaps fall under the ticks and dashes sit between them.
        extra = f' stroke-dasharray="{n(dash)} {n(gap)}" stroke-dashoffset="{n(dash + gap / 2)}" stroke-linecap="butt"'
    p.circle(p.c, p.c, r, extra=extra)
    ticks(p)
    return inner


def check(p, inner, colour=ACCENT):
    c, k = p.c, inner
    p.free([(c - 0.66 * k, c + 0.04 * k), (c - 0.2 * k, c + 0.5 * k), (c + 0.66 * k, c - 0.46 * k)],
           width=ACCENT_WIDTH[p.S], colour=colour)


def state_current(p):
    check(p, ring(p))


def state_failed(p):
    inner = ring(p)
    k = inner * (0.55 if p.S == 12 else 0.48)
    c = p.c
    w = ACCENT_WIDTH[p.S]
    p.free([(c - k, c - k), (c + k, c + k)], width=w, colour=ACCENT)
    p.free([(c - k, c + k), (c + k, c - k)], width=w, colour=ACCENT)


def state_partial(p):
    inner = ring(p)
    c = p.c
    p.fill(f"M{n(c)} {n(c - inner)} A{n(inner)} {n(inner)} 0 0 0 {n(c)} {n(c + inner)} Z")


def state_pending(p):
    r, _ = ring_radius(p)
    dot = {12: 1, 16: 1.35, 24: 1.75}[p.S]
    for i in range(8):
        a = math.pi / 8 + i * math.pi / 4
        p.dot(p.c + r * math.cos(a), p.c + r * math.sin(a), dot)
    ticks(p)


def state_none(p):
    inner = ring(p)
    k = math.ceil(inner * 0.6)
    p.line([(p.c - k, p.c), (p.c + k, p.c)], colour=ACCENT, cap=' stroke-linecap="butt"')


def question(p, inner):
    c, k = p.c, inner
    w = ACCENT_WIDTH[p.S]
    r = 0.42 * k
    cy = c - 0.32 * k
    p.path(f"M{n(c - r)} {n(cy)} A{n(r)} {n(r)} 0 1 1 {n(c + r * 0.35)} {n(cy + r * 0.95)} "
           f"L{n(c)} {n(cy + r * 1.3)} L{n(c)} {n(c + 0.3 * k)}", width=w, extra=' stroke-linecap="butt"')
    p.dot(c, c + 0.66 * k, max(w * 0.6, 0.75))


def state_unknown(p):
    question(p, ring(p, dashes=8))


def clock(p, cx, cy, r, width):
    p.circle(cx, cy, r, width=width, colour=ACCENT)
    p.free([(cx, cy - r * 0.6), (cx, cy), (cx + r * 0.55, cy)], width=width, colour=ACCENT)


def state_aged(p):
    # Ring and check, cut by a knockout around the lower-right badge.
    badge = {12: 2, 16: 3.5, 24: 5}[p.S]
    bx = by = p.S - badge - (0 if p.S == 12 else 0.5)
    mid = f"aged-{p.S}"
    p.defs.append(f'<mask id="{mid}"><rect width="{p.S}" height="{p.S}" fill="#fff"/>'
                  f'<circle cx="{n(bx)}" cy="{n(by)}" r="{n(badge + 1)}" fill="#000"/></mask>')
    start = len(p.parts)
    check(p, ring(p), colour="currentColor")
    masked = "".join(p.parts[start:])
    del p.parts[start:]
    p.parts.append(f'<g mask="url(#{mid})">{masked}</g>')
    if p.S == 12:
        p.dot(bx, by, badge, colour=ACCENT)
    else:
        clock(p, bx, by, badge - 0.75, 1.5)


def badge_aged(p):
    clock(p, p.c, p.c, p.c - p.p - p.w / 2, p.w)


def review_current(p):
    outer = p.c - p.p - p.t
    inset = p.c - outer + p.w / 2
    side = 2 * outer - p.w
    rx = 1 if p.S < 24 else 2
    p.parts.append(f'<rect x="{n(inset)}" y="{n(inset)}" width="{n(side)}" height="{n(side)}" rx="{rx}" {p.stroke("currentColor", p.w)}/>')
    ticks(p)
    check(p, outer - p.w)


def status_archived(p):
    a, b = p.p, p.S - p.p - 1
    top = round(p.S * 0.18)
    p.line([(a, top), (b, top), (b, b), (a, b)], closed=True)
    hy = top + round((b - top) * 0.35)
    hw = round((b - a) * 0.4 / 2)
    p.line([(p.c - hw, hy), (p.c + hw - 1, hy)], cap=' stroke-linecap="butt"')


def link_external(p):
    a, b = p.p, p.S - p.p - 1
    gap = round(p.S * 0.38)
    p.line([(b - gap, a), (a, a), (a, b), (b, b), (b, a + gap)])
    head = round(p.S * 0.3)
    end = p.S - p.p - p.w
    start = p.c - p.S * 0.06
    p.free([(start, p.S - start), (end, p.S - end)])
    p.free([(end - head, p.S - end), (end, p.S - end), (end, p.S - end + head)])


def link_permalink(p):
    L = p.S - 2 * p.p
    lw, lh = L * 0.64, L * 0.36
    for dx in (-1, 1):
        cx, cy = p.c + dx * L * 0.165, p.c - dx * L * 0.165
        p.parts.append(f'<rect x="{n(cx - lw / 2)}" y="{n(cy - lh / 2)}" width="{n(lw)}" height="{n(lh)}" rx="{n(lh / 2)}" '
                       f'transform="rotate(-45 {n(cx)} {n(cy)})" {p.stroke("currentColor", p.w)}/>')


def link_commit(p):
    r = p.S * 0.2
    y = snap(p.c, p.w)
    p.circle(p.c, y, r)
    p.parts.append(f'<path d="M{n(p.p)} {n(y)} H{n(p.c - r - p.w / 2)} M{n(p.c + r + p.w / 2)} {n(y)} H{n(p.S - p.p)}" '
                   f'{p.stroke("currentColor", p.w)} stroke-linecap="butt"/>')


def link_download(p):
    base = p.S - p.p - 1
    tip = base - p.w - 1
    head = round(p.S * 0.28)
    x = p.c if p.w % 2 == 0 else p.c - 0.5
    p.line([(x, p.p), (x, tip)])
    p.free([(snap(x, p.w) - head, tip - head), (snap(x, p.w), tip), (snap(x, p.w) + head, tip - head)])
    p.line([(p.p + 1, base), (p.S - p.p - 2, base)])


def link_data(p):
    a, b = p.p + (1 if p.S >= 16 else 0), p.S - p.p - (2 if p.S >= 16 else 1)
    t, bot = p.p, p.S - p.p - 1
    fold = round((b - a) * 0.4)
    p.line([(a, t), (b - fold, t), (b, t + fold), (b, bot), (a, bot)], width=1, closed=True)
    p.line([(b - fold, t), (b - fold, t + fold), (b, t + fold)], width=1)
    # Braces: vertical bars with a centre nub, pointing outward.
    y0, y1 = t + fold + 2, bot - 2
    mid = round((y0 + y1) / 2)
    for side in (-1, 1):
        x = p.c + side * (2 if p.S == 12 else 3) - (1 if side > 0 else 0)
        nub = x + side * 1
        hook = x - side * 1
        if p.S == 12:
            p.line([(x, y0), (x, mid - 1), (nub, mid), (x, mid + 1), (x, y1)], width=1)
        else:
            p.line([(hook, y0), (x, y0), (x, mid - 1), (nub, mid), (x, mid + 1), (x, y1), (hook, y1)], width=1)


def disclose_closed(p):
    a, b = p.p + 1, p.S - p.p - 1
    x = snap(p.c, p.w)
    p.line([(a, x), (b - (1 if p.w % 2 else 0), x)], cap=' stroke-linecap="butt"')
    p.line([(x, a), (x, b - (1 if p.w % 2 else 0))], cap=' stroke-linecap="butt"')


def disclose_open(p):
    """Upright six-arm asterisk on the plus's centre and arm length (B-PR146-01)."""
    a, b = p.p + 1, p.S - p.p - 1 - (1 if p.w % 2 else 0)
    x = snap(p.c, p.w)
    p.line([(x, a), (x, b)], cap=' stroke-linecap="butt"')
    top, bottom = snap(a, p.w), snap(b, p.w)  # diagonals cross at the snapped stroke's midpoint
    y, r = (top + bottom) / 2, (bottom - top) / 2
    dx, dy = r * math.cos(math.radians(30)), r * math.sin(math.radians(30))
    for sign in (1, -1):
        p.path(f"M{n(x - dx)} {n(y - sign * dy)} L{n(x + dx)} {n(y + sign * dy)}", extra=' stroke-linecap="butt"')


def control_reset(p):
    r = p.c - p.p - p.w / 2 - (0.5 if p.S == 12 else 1)
    start, sweep = 90, 270  # from the top, counter-clockwise to the right side
    pt = lambda deg: (p.c + r * math.cos(math.radians(deg)), p.c - r * math.sin(math.radians(deg)))
    x0, y0 = pt(start)
    end = start + sweep
    x1, y1 = pt(end)
    p.path(f"M{n(x0)} {n(y0)} A{n(r)} {n(r)} 0 1 0 {n(x1)} {n(y1)}", extra=' stroke-linecap="butt"')  # sweep 0 = counter-clockwise on screen
    # Arrowhead along the counter-clockwise tangent at the end point.
    th = math.radians(end)
    dx, dy = -math.sin(th), -math.cos(th)
    nx, ny = -dy, dx
    h = p.S * 0.3
    tip = (x1 + dx * h * 0.55, y1 + dy * h * 0.55)
    left = (x1 + nx * h * 0.5 - dx * h * 0.15, y1 + ny * h * 0.5 - dy * h * 0.15)
    right = (x1 - nx * h * 0.5 - dx * h * 0.15, y1 - ny * h * 0.5 - dy * h * 0.15)
    p.fill(f"M{n(tip[0])} {n(tip[1])} L{n(left[0])} {n(left[1])} L{n(right[0])} {n(right[1])} Z")


def scope_collection(p):
    gap = 1
    cell = (p.S - 2 * p.p - 2 * gap) / 3
    for i in range(3):
        for j in range(3):
            p.rect(p.p + i * (cell + gap), p.p + j * (cell + gap), cell, cell)


def view_chart(p):
    axis = 1 if p.S == 12 else 2
    p.rect(p.p, p.p, axis, p.S - 2 * p.p)
    bar = 2
    x0 = p.p + axis + 1
    room = p.S - p.p - x0
    rows = [p.p + 1, round(p.c - bar / 2), p.S - p.p - 1 - bar]
    for y, frac in zip(rows, (0.8, 0.55, 1.0)):
        p.rect(x0, y, round(room * frac), bar)


def view_table(p):
    a, b = p.p, p.S - p.p - 1
    t, bot = p.p + 1, p.S - p.p - 2
    p.line([(a, t), (b, t), (b, bot), (a, bot)], width=1, closed=True)
    p.rect(a, t, b - a + 1, 2)
    for k in (1, 2):
        p.line([(a, t + 1 + round((bot - t - 1) * k / 3)), (b, t + 1 + round((bot - t - 1) * k / 3))], width=1)
    p.line([(p.c, t), (p.c, bot)], width=1)


DRAW = {
    "state.current": state_current, "state.aged": state_aged, "state.partial": state_partial,
    "state.pending": state_pending, "state.none": state_none, "state.failed": state_failed,
    "state.unknown": state_unknown, "badge.aged": badge_aged, "review.current": review_current,
    "status.archived": status_archived, "link.external": link_external, "link.permalink": link_permalink,
    "link.commit": link_commit, "link.download": link_download, "link.data": link_data,
    "disclose.closed": disclose_closed, "disclose.open": disclose_open, "control.reset": control_reset,
    "scope.collection": scope_collection, "view.chart": view_chart, "view.table": view_table,
}


def render(icon_id, size):
    pen = Pen(*SIZES[size])
    DRAW[icon_id](pen)
    return pen.svg(icon_id)


def build(output=OUTPUT, manifest=MANIFEST):
    icons = [i for i in json.loads(Path(manifest).read_text(encoding="utf-8"))["icons"] if i["id"] in DRAW]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    written = []
    for icon in icons:
        for size in icon["sizes"]:
            path = output / f"{icon['id']}-{size}.svg"
            path.write_text(render(icon["id"], size), encoding="utf-8")
            written.append(path)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()
    print(f"Wrote {len(build(args.output))} icon files")
