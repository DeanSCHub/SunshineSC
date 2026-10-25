"""Mockup styling for decisions: tags by type, TPWS loop boxes on the rail, footprint-safe signals."""
import sys, re, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geom import mat, points, attr

data = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
WANT = set(sys.argv[3].split(","))          # tags,tpws,signals
pal = {(p["role"], p["src"]): p["i"] for p in data["palette"]}
INK = pal[("stroke", "#000000")]
SIGNAL_FILLS = {pal.get(("fill", h)) for h in ("#ff0000", "#32cd32", "#33cc33", "#0000ff")} - {None}
TPWS_FILLS = {pal.get(("fill", h)) for h in ("#e040c4", "#8b0000")} - {None}
TAG_FILL = pal.get(("fill", "#388e8e"))
WHITE_TEXT = pal.get(("text", "#ffffff"))
EL = re.compile(r"<path [^>]*/>|<text [^>]*>.*?</text>", re.S)
stats = {}


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def el_box(el):
    pts, _ = points(attr(el, "d") or "", mat(attr(el, "transform")))
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def triangle(el):
    pts, curve = points(attr(el, "d") or "", mat(attr(el, "transform")))
    if curve:
        return None
    u = []
    for p in pts:
        if not any(abs(p[0] - q[0]) < .3 and abs(p[1] - q[1]) < .3 for q in u):
            u.append(p)
    if len(u) != 3:
        return None
    for i in range(3):
        a, b, c = u[i], u[(i + 1) % 3], u[(i + 2) % 3]
        if abs(a[0] - b[0]) < 0.6:
            return dict(bx=(a[0] + b[0]) / 2, y0=min(a[1], b[1]), y1=max(a[1], b[1]), ax=c[0], ay=c[1])
    return None


def text_anchor(el):
    m = mat(attr(el, "transform"))
    ts = re.search(r'<tspan x="([^"]*)" y="([^"]*)"', el)
    if not ts:
        return None
    x, y = float(ts.group(1).split()[0]), float(ts.group(2))
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


# ---------- track lines (for which side of a signal the track is)
TRACKS = []
for el in EL.findall(data["layers"]["base"]):
    if el.startswith("<path") and re.search(rf'class="s{INK}"', el) and not attr(el, "stroke-dasharray"):
        pts, curve = points(attr(el, "d") or "", mat(attr(el, "transform")))
        if curve:
            continue
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if abs(y1 - y2) < .6 and abs(x2 - x1) >= 40:
                TRACKS.append((min(x1, x2), max(x1, x2), (y1 + y2) / 2))


def track_y(x, y, maxd=30):
    best, bd = None, maxd
    for x0, x1, ty in TRACKS:
        if x0 - 1 <= x <= x1 + 1 and abs(ty - y) < bd:
            bd, best = abs(ty - y), ty
    return best


# ---------- signals drawn inside the old triangle's footprint (so they can't hit anything new)
def signal_svg(t, fill):
    d = 1 if t["ax"] > t["bx"] else -1
    h = t["y1"] - t["y0"]
    w = abs(t["ax"] - t["bx"])
    r = min(h * 0.34, w * 0.4)
    hx = t["ax"] - d * r                       # head's outer edge = the old apex
    yc = t["ay"]
    px = t["bx"] + d * 0.9
    ty = track_y(px, yc)
    foot = t["y1"] if (ty is None or ty > yc) else t["y0"]   # post rises from the track side
    return (f'<g class="sig"><circle class="halo f{fill}" cx="{f(hx)}" cy="{f(yc)}" r="{f(r * 1.45)}"/>'
            f'<path class="s{INK}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" d="M{f(px)} {f(foot)}V{f(yc)}H{f(hx - d * r)}"/>'
            f'<circle class="f{fill} s{INK}" stroke-width=".9" cx="{f(hx)}" cy="{f(yc)}" r="{f(r)}"/></g>')


# ---------- TPWS: one box per loop on the rail, touching loops joined, arrow inside (like the CBD Mantis)
def tpws_run_svg(run, fill):
    out = []
    yc = sum(t["ay"] for t, _ in run) / len(run)
    hh = 2.3
    segs = []
    for t, _ in run:
        x0, x1 = sorted((t["bx"], t["ax"]))
        segs.append((x0, x1, 1 if t["ax"] > t["bx"] else -1))
    X0, X1 = segs[0][0] - .6, segs[-1][1] + .6
    out.append(f'<g class="loop" style="--c:var(--p{fill})">')
    for i, (x0, x1, d) in enumerate(segs):
        a = X0 if i == 0 else (segs[i - 1][1] + x0) / 2
        b = X1 if i == len(segs) - 1 else (x1 + segs[i + 1][0]) / 2
        out.append(f'<rect class="seg" x="{f(a)}" y="{f(yc - hh)}" width="{f(b - a)}" height="{f(hh * 2)}"/>')
        tail, head = (a + 1.1, b - 1.0) if d == 1 else (b - 1.1, a + 1.0)
        back = head - d * 1.6
        out.append(f'<path class="ar" d="M{f(tail)} {f(yc)}H{f(back)}"/><path class="hd" d="M{f(back)} {f(yc - 1.1)}L{f(head)} {f(yc)}L{f(back)} {f(yc + 1.1)}Z"/>')
    out.append(f'<rect class="box" x="{f(X0)}" y="{f(yc - hh)}" width="{f(X1 - X0)}" height="{f(hh * 2)}"/></g>')
    return "".join(out)


def classify(el):
    if not el.startswith("<path"):
        return None
    fills = [int(c[1:]) for c in (attr(el, "class") or "").split() if c[0] == "f" and c[1:].isdigit()]
    if not fills or fills[0] not in SIGNAL_FILLS | TPWS_FILLS:
        return None
    t = triangle(el)
    if not t:
        return None
    h, w = t["y1"] - t["y0"], abs(t["ax"] - t["bx"])
    if fills[0] in SIGNAL_FILLS and 14 <= h <= 19 and 12 <= w <= 17:
        return ("sig", t, fills[0])
    if fills[0] in TPWS_FILLS and 5.5 <= h <= 8.5 and 4.5 <= w <= 7.5:
        return ("tpws", t, fills[0])
    return None


def near_box(b, boxes, tol=1.2):
    return any(all(abs(b[k] - c[k]) <= tol for k in range(4)) for c in boxes)


# ---------- pass 1
tag_boxes, sym_boxes, runs = [], [], {}
texts = []
for lname, s in data["layers"].items():
    loops = []
    for el in EL.findall(s):
        c = classify(el)
        if c:
            t = c[1]
            sym_boxes.append((min(t["bx"], t["ax"]), t["y0"], max(t["bx"], t["ax"]), t["y1"]))
            if c[0] == "tpws":
                loops.append((t, c[2]))
        elif el.startswith("<path") and TAG_FILL is not None and re.search(rf'class="[^"]*\bf{TAG_FILL}\b', el):
            b = el_box(el)
            if b and b[2] - b[0] < 400 and b[3] - b[1] < 120:
                tag_boxes.append(b)
        elif el.startswith("<text"):
            a = text_anchor(el)
            if a:
                texts.append((a, re.sub(r"<[^>]+>", "", el).strip()))
    loops.sort(key=lambda z: (round(z[0]["ay"]), min(z[0]["bx"], z[0]["ax"])))
    rr, cur = [], []
    for t, fill in loops:
        if cur:
            p, pf = cur[-1]
            gap = min(t["bx"], t["ax"]) - max(p["bx"], p["ax"])
            if pf == fill and abs(p["ay"] - t["ay"]) < .8 and -1.5 < gap < 1.6:
                cur.append((t, fill)); continue
            rr.append(cur)
        cur = [(t, fill)]
    if cur:
        rr.append(cur)
    first = {}
    for run in rr:
        keys = [tuple(round(v) for v in (min(t["bx"], t["ax"]), t["y0"])) for t, _ in run]
        first[keys[0]] = run
        for k in keys[1:]:
            first[k] = None
    runs[lname] = first


def tag_type(b):
    words = " ".join(t for (x, y), t in texts if b[0] - 1 <= x <= b[2] + 1 and b[1] - 1 <= y <= b[3] + 3).upper()
    if "TPWS" in words:
        return "tp"
    if "UPS" in words or "GEN" in words:
        return "ups"
    if re.search(r"SER\b|PER\b|EH\b|CHCPB|TCUPS", words):
        return "ser"
    return "zb"


tag_kind = {tuple(round(v, 1) for v in b): tag_type(b) for b in tag_boxes}


def kind_at(pt):
    for b in tag_boxes:
        if pt and b[0] - 1 <= pt[0] <= b[2] + 1 and b[1] - 1 <= pt[1] <= b[3] + 3:
            return tag_kind[tuple(round(v, 1) for v in b)]
    return None


def transform(s, lname):
    first = runs.get(lname, {})

    def rep(m):
        el = m.group(0)
        c = classify(el)
        if c:
            kind, t, fill = c
            if kind == "sig" and "signals" in WANT:
                stats["signals"] = stats.get("signals", 0) + 1
                return signal_svg(t, fill)
            if kind == "tpws" and "tpws" in WANT:
                key = tuple(round(v) for v in (min(t["bx"], t["ax"]), t["y0"]))
                run = first.get(key, "missing")
                if run is None:
                    return ""
                if run == "missing":
                    run = [(t, fill)]
                stats["loops"] = stats.get("loops", 0) + len(run)
                return tpws_run_svg(run, fill)
            return el
        if el.startswith("<path") and "tags" in WANT:
            cl = attr(el, "class") or ""
            if TAG_FILL is not None and re.search(rf"\bf{TAG_FILL}\b", cl):
                b = el_box(el)
                k = tag_kind.get(tuple(round(v, 1) for v in b), "zb") if b else "zb"
                stats["tags"] = stats.get("tags", 0) + 1
                return el.replace('class="', f'class="tag tg-{k} ', 1)
            if not any(x[0] == "f" and x[1:].isdigit() for x in cl.split()):
                b = el_box(el)
                if b and "tpws" in WANT and near_box(b, sym_boxes):
                    return ""
                if b and near_box(b, tag_boxes, 1.6):
                    nb = min(tag_boxes, key=lambda t: sum(abs(t[i] - b[i]) for i in range(4)))
                    k = tag_kind.get(tuple(round(v, 1) for v in nb), "zb")
                    return el.replace('class="', f'class="tagline tg-{k} ', 1)
            return el
        if el.startswith("<path") and "tpws" in WANT:
            cl = attr(el, "class") or ""
            if not any(x[0] == "f" and x[1:].isdigit() for x in cl.split()):
                b = el_box(el)
                if b and near_box(b, sym_boxes):
                    return ""
        if el.startswith("<text") and "tags" in WANT and WHITE_TEXT is not None and re.search(rf'class="t{WHITE_TEXT}\b', el):
            k = kind_at(text_anchor(el))
            if k:
                return el.replace(f'class="t{WHITE_TEXT}', f'class="tz tz-{k}', 1)
        return el
    return EL.sub(rep, s)


data["layers"] = {k: transform(v, k) for k, v in data["layers"].items()}
CSS = """
:root,:root[data-theme="light"]{--halo:.2;
 --zb-bg:#e3f1f1;--zb-line:#2b7a7e;--zb-ink:#175a5e;
 --ups-bg:#fbf0dc;--ups-line:#b9781a;--ups-ink:#7a4c0a;
 --ser-bg:#e8ebf3;--ser-line:#56658a;--ser-ink:#38445f;
 --tp-bg:#f8e6f3;--tp-line:#b0459a;--tp-ink:#7d2b6b;
 --loop-fill:.85;--loop-line:#1d2a33}
:root[data-theme="dark"]{--halo:.3;
 --zb-bg:#10313a;--zb-line:#3b9ca1;--zb-ink:#9adfe1;
 --ups-bg:#3a2c12;--ups-line:#d39a3f;--ups-ink:#f2c77d;
 --ser-bg:#1f2840;--ser-line:#7d8fc0;--ser-ink:#c3cdeb;
 --tp-bg:#3a1834;--tp-line:#d572bf;--tp-ink:#f3b9e4;
 --loop-fill:.9;--loop-line:#d9e3ea}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--halo:.3;
 --zb-bg:#10313a;--zb-line:#3b9ca1;--zb-ink:#9adfe1;--ups-bg:#3a2c12;--ups-line:#d39a3f;--ups-ink:#f2c77d;
 --ser-bg:#1f2840;--ser-line:#7d8fc0;--ser-ink:#c3cdeb;--tp-bg:#3a1834;--tp-line:#d572bf;--tp-ink:#f3b9e4;--loop-fill:.9;--loop-line:#d9e3ea}}
.m path.tg-zb{fill:var(--zb-bg);stroke:var(--zb-line)} .m .tz-zb{fill:var(--zb-ink)}
.m path.tg-ups{fill:var(--ups-bg);stroke:var(--ups-line)} .m .tz-ups{fill:var(--ups-ink)}
.m path.tg-ser{fill:var(--ser-bg);stroke:var(--ser-line)} .m .tz-ser{fill:var(--ser-ink)}
.m path.tg-tp{fill:var(--tp-bg);stroke:var(--tp-line)} .m .tz-tp{fill:var(--tp-ink)}
.m path.tagline{fill:none}
.m .sig .halo{opacity:var(--halo);stroke:none}
.m .loop .seg{fill:var(--c);fill-opacity:var(--loop-fill);stroke:none}
.m .loop .box{fill:none;stroke:var(--loop-line);stroke-width:.55}
.m .loop .ar{fill:none;stroke:var(--loop-line);stroke-width:.5}
.m .loop .hd{fill:var(--loop-line)}
"""
data["extra_css"] = CSS
json.dump(data, open(OUT, "w"))
print(stats, "tag kinds", {k: list(tag_kind.values()).count(k) for k in set(tag_kind.values())})
