"""Split each map layer into a grid of cells so the viewer only draws the cells near the screen."""
import re, math
from geom import mat, points, attr

CELL = 300          # map units per grid cell
EL = re.compile(r"<path [^>]*/>|<text [^>]*>.*?</text>|<g [^>]*>.*?</g>", re.S)


def bbox(el):
    if el.startswith("<text"):
        m = mat(attr(el, "transform"))
        ts = re.search(r'<tspan x="([^"]*)" y="([^"]*)"', el)
        if not ts:
            return None
        xs = [float(v) for v in ts.group(1).split()]
        y = float(ts.group(2))
        fs = float(attr(el, "font-size") or 10)
        sc = (m[0] ** 2 + m[1] ** 2) ** .5
        x0 = m[0] * xs[0] + m[2] * y + m[4]
        x1 = m[0] * xs[-1] + m[2] * y + m[4] + fs * sc * .7
        yy = m[1] * xs[0] + m[3] * y + m[5]
        return (min(x0, x1), yy - fs * sc, max(x0, x1), yy)
    if el.startswith("<g"):
        inner = re.findall(r"<path [^>]*/>", el)
        bs = [b for b in (bbox(p) for p in inner) if b]
        if not bs:
            return None
        return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
    pts, _ = points(attr(el, "d") or "", mat(attr(el, "transform")))
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def size_class(el, b):
    """z1 = tiny (only drawn when zoomed in), z2 = small (hidden at overview zoom)."""
    if not b:
        return ""
    if el.startswith("<text"):
        m = mat(attr(el, "transform"))
        eff = float(attr(el, "font-size") or 10) * (m[0] ** 2 + m[1] ** 2) ** .5
        return "z1" if eff < 5.5 else "z2" if eff < 9.5 else ""
    big = max(b[2] - b[0], b[3] - b[1])
    return "z1" if big < 7 else "z2" if big < 18 else ""


def tag(el, z):
    if not z:
        return el
    if ' class="' in el[:40]:
        return el.replace(' class="', f' class="{z} ', 1)
    return el.replace(" ", f' class="{z}" ', 1)


def chunk(svg, y0):
    """Return (always_markup, {(cx, cy): markup}) for one layer."""
    always, cells = [], {}
    for el in EL.findall(svg):
        b = bbox(el)
        el = tag(el, size_class(el, b))
        if not b or (b[2] - b[0]) > CELL or (b[3] - b[1]) > CELL:
            always.append(el)
            continue
        cx = int(((b[0] + b[2]) / 2) // CELL)
        cy = int(((b[1] + b[3]) / 2 - y0) // CELL)
        cells.setdefault((cx, cy), []).append(el)
    return "".join(always), {k: "".join(v) for k, v in cells.items()}


def layer_markup(svg, y0):
    always, cells = chunk(svg, y0)
    out = [always]
    for (cx, cy), m in sorted(cells.items()):
        out.append(f'<g class="cell" data-c="{cx},{cy}">{m}</g>')
    return "".join(out), len(cells)
