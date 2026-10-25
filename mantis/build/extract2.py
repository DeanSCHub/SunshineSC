"""Turn MuPDF's SVG export of the cleaned Mantis PDF into themed, layered SVG fragments."""
import sys, re, json, math, colorsys
import xml.etree.ElementTree as ET

SVG_IN, JSON_IO = sys.argv[1], sys.argv[2]
NS = {"svg": "http://www.w3.org/2000/svg", "ink": "http://www.inkscape.org/namespaces/inkscape"}
INK_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"
SVGNS = "{http://www.w3.org/2000/svg}"

tree = ET.parse(SVG_IN)
root = tree.getroot()


def layer_for(label):
    if label is None:
        return "base"
    l = label.lower()
    if "button" in l or l.endswith(" off") or l.endswith(" on") or "click" in l or label in (
            "Lights", "Version Info", "TPWS Sound Off") or label.startswith("Telephone Rd"):
        return None
    if label == "TPWS":
        return "tpws"
    if label == "Speed Overlay":
        return "speed"
    if label == "Asset Supply Overlay":
        return "supply"
    if label == "KP Overlay":
        return "kp"
    if "approach" in l or l.endswith("rd overlay"):
        return "approach"
    return "base"


# ------------------------------------------------------------------ colours
def hexc(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v * 255))) for v in rgb)


def norm(h):
    h = h.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", h):
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


FILL = {
    "#ff0000": ("#e5484d", "#ff6369"),
    "#33cc33": ("#2f9e5b", "#4cc38a"), "#32cd32": ("#2f9e5b", "#4cc38a"),
    "#0000ff": ("#3358d4", "#6e8cff"),
    "#e040c4": ("#c93ba8", "#e870cf"),
    "#388f8f": ("#2c7a80", "#1f6a70"), "#388e8e": ("#2c7a80", "#1f6a70"),
    "#282828": ("#26323b", "#34444f"),
    "#800080": ("#6d2a8c", "#7a3a9c"),
    "#808080": ("#6b7682", "#4a5662"),
    "#000000": ("#1d2a33", "#3d4f5c"),
    "#292929": ("#26323b", "#34444f"),
    "#ffffff": ("#f6f8fa", "#0e1a22"),
    "#ffe6e6": ("#fbe4e2", "#3a2629"), "#ffe3e0": ("#fbe4e2", "#3a2629"),
    "#ffbfcc": ("#f6c4cf", "#5a2f3a"),
    "#afeeee": ("#c8eeee", "#1d4448"), "#b0eded": ("#c8eeee", "#1d4448"),
    "#8b0000": ("#9b2226", "#c0392b"), "#8c0000": ("#9b2226", "#c0392b"),
    "#7d9ec0": ("#7d9cbd", "#3f5f80"), "#7e9fbf": ("#7d9cbd", "#3f5f80"),
    "#80c3d9": ("#7fc0d6", "#2f6f84"), "#82c3d9": ("#7fc0d6", "#2f6f84"),
    "#81e9b2": ("#7fdcab", "#2b7a55"), "#82e8b2": ("#7fdcab", "#2b7a55"),
    "#7e7eec": ("#8686e8", "#4646a8"),
    "#ba81d5": ("#b98ad3", "#6a3f86"), "#ba82d5": ("#b98ad3", "#6a3f86"),
    "#ffad5b": ("#f7ae63", "#9a5a1a"),
}
STROKE = {
    "#000000": ("#1d2a33", "#c9d6df"),
    "#b5844f": ("#b07a35", "#d9a35a"), "#b58442": ("#b07a35", "#d9a35a"),
    "#ffffff": ("#f6f8fa", "#0e1a22"),
    "#f5f5f5": ("#eef1f4", "#16252e"),
    "#666666": ("#5c6773", "#93a1ad"),
    "#800080": ("#7a3a9c", "#b07ad0"),
    "#ff6a1f": ("#e46f2a", "#f29a5c"), "#ff691f": ("#e46f2a", "#f29a5c"), "#ff6820": ("#e46f2a", "#f29a5c"),
    "#42a5f5": ("#2f8fe0", "#5fb0f5"),
}
TEXT = {
    "#000000": ("#1d2a33", "#d9e3ea"),
    "#ffffff": ("#ffffff", "#f3f7fa"),
    "#ff6a1f": ("#d9681f", "#f0a061"), "#ff691f": ("#d9681f", "#f0a061"), "#ff6820": ("#d9681f", "#f0a061"),
    "#7a7abf": ("#5f63b0", "#a3a7ee"), "#7b7bbf": ("#5f63b0", "#a3a7ee"), "#7b7bc0": ("#5f63b0", "#a3a7ee"),
    "#004d00": ("#2d7a3a", "#79c98a"), "#005400": ("#2d7a3a", "#79c98a"),
    "#8b0000": ("#a32a2a", "#ff8a80"), "#8c0000": ("#a32a2a", "#ff8a80"),
    "#de1c1c": ("#c62828", "#ff7a7a"),
    "#387db8": ("#2f6fa8", "#7cb7ea"),
    "#4b0082": ("#4b2a8a", "#b9a2f0"),
    "#7d9ec0": ("#5f84a8", "#8fb3d6"), "#7d9ebf": ("#5f84a8", "#8fb3d6"),
}


def auto_dark(h, role):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.12:
        l2, s2, hh = 0.09 + (1 - l) * 0.78, 0.12, 0.56
        if role == "fill" and l < 0.35:
            l2 = 0.27
    elif l > 0.8:
        l2, s2 = 0.22, min(s, 0.35)
    else:
        l2, s2 = 0.34 + l * 0.4, s * 0.9
    if role == "text" and s >= 0.12:
        l2 = max(l2, 0.68)
    return hexc(colorsys.hls_to_rgb(hh, l2, s2))


palette = {}


def cls(role, h):
    h = norm(h)
    key = (role, h)
    if key not in palette:
        table = {"fill": FILL, "stroke": STROKE, "text": TEXT}.get(role, {})
        if role == "edge":
            light, dark = "rgba(20,32,40,.6)", "rgba(220,232,240,.32)"
        elif h in table:
            light, dark = table[h]
        else:
            light, dark = h, auto_dark(h, role)
        palette[key] = dict(i=len(palette), role=role, src=h, light=light, dark=dark)
    return palette[key]["i"]


# ------------------------------------------------------------------ helpers
NUM = re.compile(r"-?\d*\.?\d+(?:e-?\d+)?")


def short(s, nd=3):
    def r(m):
        v = float(m.group())
        t = f"{v:.{nd}f}".rstrip("0").rstrip(".")
        return "0" if t in ("-0", "") else t
    return NUM.sub(r, s)


def mat(t):
    m = re.match(r"matrix\(([^)]*)\)", t or "")
    if not m:
        return (1, 0, 0, 1, 0, 0)
    v = [float(x) for x in re.split(r"[ ,]+", m.group(1).strip())]
    return tuple(v)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


KP_RE = re.compile(r"^\s*\d{1,2}\.\d{2,3}\s?[kK][pP]\s*$")
DROP_ATTR = {"stroke-miterlimit": "10", "stroke-linejoin": "miter", "stroke-linecap": "butt"}

data = json.load(open(JSON_IO))
OVL = data.get("ovl", {})
TOK = re.compile(r"[MLHVCZmlhvcz]|-?\d*\.?\d+(?:e-?\d+)?")


def path_bbox(d, m):
    toks = TOK.findall(d)
    xs, ys = [], []
    cmd, i, cx, cy = None, 0, 0.0, 0.0
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t; i += 1
            continue
        if cmd in ("M", "L", "C"):
            cx, cy = float(toks[i]), float(toks[i + 1]); i += 2
        elif cmd == "H":
            cx = float(toks[i]); i += 1
        elif cmd == "V":
            cy = float(toks[i]); i += 1
        else:
            i += 1
            continue
        xs.append(m[0] * cx + m[2] * cy + m[4]); ys.append(m[1] * cx + m[3] * cy + m[5])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def overlay_for_rect(b):
    if not b:
        return None
    cx, cy, w, h = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0], b[3] - b[1]
    for g, o in OVL.items():
        for r in o["rects"]:
            if abs((r[0] + r[2]) / 2 - cx) < 2 and abs((r[1] + r[3]) / 2 - cy) < 2 and abs((r[2] - r[0]) - w) < 4 and abs((r[3] - r[1]) - h) < 4:
                return g
    return None


def overlay_for_text(content, x, y):
    c = content.strip()
    for g, o in OVL.items():
        for t, b in o["texts"]:
            if t == c and b[0] - 4 <= x <= b[2] + 4 and b[1] - 4 <= y <= b[3] + 4:
                return g
    return None


layers = {k: [] for k in ["base", "kp", "tpws", "speed", "approach", "supply"]}
stats = {"skipped": 0}


def emit_path(el, layer, op):
    a = dict(el.attrib)
    d = a.pop("d", "")
    if not d:
        return
    fill = a.pop("fill", None)
    stroke = a.pop("stroke", None)
    classes = []
    has_fill = fill is None or fill != "none"
    if has_fill:
        fill = fill or "#000000"
        if fill.startswith("url("):
            stats["skipped"] += 1
            return
        classes.append(f"f{cls('fill', fill)}")
    if stroke and stroke != "none":
        if norm(stroke) == "#000000" and has_fill and norm(fill) != "#000000":
            classes.append(f"s{cls('edge', stroke)}")
        else:
            classes.append(f"s{cls('stroke', stroke)}")
    else:
        for k in [k for k in a if k.startswith("stroke")]:
            a.pop(k)
    if not classes:
        return
    # MuPDF's SVG export reports PDF-XChange's comment-tool strokes as 8 (or 10) wide; they draw at 1
    if a.get("stroke-width") in ("8", "10") and layer != "speed":
        a["stroke-width"] = "1"
    # (overlay content comes from the per-layer comparison below; never move base drawing by shape alone -
    #  that misfiled crossovers that sit under a speed-overlay line)
    for k, v in DROP_ATTR.items():
        if a.get(k) == v:
            a.pop(k)
    a.pop("id", None)
    if op < 0.999:
        a["opacity"] = f"{op:.2f}"
    out = [f'<path class="{" ".join(classes)}"']
    for k, v in a.items():
        if k == "transform":
            v = short(v, 5)
        out.append(f' {k}="{v}"')
    out.append(f' d="{short(d, 2)}"/>')
    layers[layer].append("".join(out))


labels = []


def emit_text(el, layer, op):
    a = dict(el.attrib)
    fill = a.pop("fill", "#000000")
    a.pop("font-family", None)
    a.pop("{http://www.w3.org/XML/1998/namespace}space", None)
    bold = a.pop("font-weight", "") == "bold"
    fs = float(a.get("font-size", "10"))
    m = mat(a.get("transform"))
    scale = math.hypot(m[0], m[1])
    spans = []
    content = ""
    first = None
    for ts in el.iter(SVGNS + "tspan"):
        t = ts.text or ""
        if not t.strip():
            continue
        content += t
        xs = ts.get("x", "0")
        y = ts.get("y", "0")
        if first is None:
            first = (float(xs.split()[0]), float(y))
        spans.append(f'<tspan x="{short(xs, 2)}" y="{short(y, 2)}">{esc(t)}</tspan>')
    if not spans:
        return
    eff = fs * scale
    X = m[0] * first[0] + m[2] * first[1] + m[4]
    Y = m[1] * first[0] + m[3] * first[1] + m[5]
    if layer == "base" and KP_RE.match(content) and eff < 6:
        layer = "kp"
    c = f"t{cls('text', fill)}"
    if bold:
        c += " b"
    attrs = f' font-size="{short(a.get("font-size", "10"), 3)}"'
    if "transform" in a:
        attrs += f' transform="{short(a["transform"], 5)}"'
    if op < 0.999:
        attrs += f' opacity="{op:.2f}"'
    if a.get("fill-opacity"):
        attrs += f' fill-opacity="{a["fill-opacity"]}"'
    layers[layer].append(f'<text class="{c}"{attrs}>{"".join(spans)}</text>')
    if layer == "base" and eff >= 7 and len(content.strip()) >= 2:
        labels.append([content.strip(), round(X, 1), round(Y - eff, 1), round(X + eff * 0.55 * len(content), 1), round(Y, 1), round(eff, 1)])


def walk(el, label, op):
    tag = el.tag.replace(SVGNS, "")
    if tag in ("defs", "clipPath", "mask", "image", "use"):
        return
    if tag == "g":
        lab = el.get(INK_LABEL, label)
        o = op * float(el.get("opacity", "1"))
        for ch in el:
            walk(ch, lab, o)
        return
    layer = layer_for(label)
    if layer is None:
        return
    o = op * float(el.get("opacity", "1"))
    if tag == "path":
        emit_path(el, layer, o)
    elif tag == "text":
        emit_text(el, layer, o)


for ch in root:
    walk(ch, None, 1.0)

# ---- Speed and Approach overlays don't survive the all-layers export; diff per-layer exports instead
import collections, pymupdf
TMPD = sys.argv[3]
LEGEND_BOX = (5890, 240, 6395, 780)   # speed legend panel - rebuilt in the Layers menu
CHROME = [LEGEND_BOX, (-100, -100, 14500, 216), (-100, 2644, 14500, 2900), (6430, 220, 7757, 782), (0, 214, 2200, 420),
          (0, 2440, 2800, 2644), (13440, 2310, 14130, 2650), (2070, 2040, 2690, 2480)]


def leaves(svgtext):
    r = ET.fromstring(svgtext)
    out = []
    def w(e, op):
        tag = e.tag.replace(SVGNS, "")
        if tag in ("defs", "clipPath", "mask", "image", "use"):
            return
        if tag == "g":
            o = op * float(e.get("opacity", "1"))
            for c in e:
                w(c, o)
            return
        if tag in ("path", "text"):
            out.append((ET.tostring(e), e, op * float(e.get("opacity", "1"))))
    w(r, 1.0)
    return out


def in_chrome(x, y):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in CHROME)


def svg_lines(path):
    t = pymupdf.open(path)[0].get_svg_image(text_as_path=False)
    return [l for l in t.split("\n") if l.startswith("<path") or l.startswith("<text")]


base_lines = collections.Counter(svg_lines(f"{TMPD}/ovl_base.pdf"))
WRAP = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">{}</svg>'
for g in ("speed", "approach"):
    rem = collections.Counter(base_lines)
    n = 0
    for line in svg_lines(f"{TMPD}/ovl_{g}.pdf"):
        if rem[line] > 0:
            rem[line] -= 1
            continue
        e = ET.fromstring(WRAP.format(line))[0]
        op = 1.0
        m = mat(e.get("transform"))
        if e.tag.endswith("path"):
            bb = path_bbox(e.get("d", ""), m)
            if not bb or in_chrome((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2):
                continue
            emit_path(e, g, op)
        else:
            ts = next(e.iter(SVGNS + "tspan"), None)
            if ts is None:
                continue
            x0, y0 = float(ts.get("x", "0").split()[0]), float(ts.get("y", "0"))
            if in_chrome(m[0] * x0 + m[2] * y0 + m[4], m[1] * x0 + m[3] * y0 + m[5]):
                continue
            emit_text(e, g, op)
        n += 1
    print(g, "overlay elements", n)

# ---- comment-tool annotations (lines and boxes drawn with PDF-XChange) aren't in the page content
for an in pymupdf.open(f"{TMPD}/ovl_base.pdf")[0].annots():
    t = an.type[1]
    col = an.colors or {}
    st = col.get("stroke") or [0, 0, 0]
    fi = col.get("fill") or []
    w = an.border.get("width") or 1
    w = 1 if w < 0 else w
    if t == "Line" and an.vertices and len(an.vertices) >= 2:
        (x1, y1), (x2, y2) = an.vertices[0], an.vertices[1]
        layers["base"].append(f'<path class="s{cls("stroke", hexc(st))}" stroke-width="{w:.2f}" d="M{x1:.2f} {y1:.2f}L{x2:.2f} {y2:.2f}"/>')
    elif t == "Square":
        r = an.rect
        c = f's{cls("stroke", hexc(st))}'
        if fi:
            c = f'f{cls("fill", hexc(fi))} s{cls("edge", hexc(st))}' if hexc(st) == "#000000" and hexc(fi) != "#000000" else f'f{cls("fill", hexc(fi))} s{cls("stroke", hexc(st))}'
        layers["base"].append(f'<path class="{c}" stroke-width="{w:.2f}" d="M{r.x0+w/2:.2f} {r.y0+w/2:.2f}H{r.x1-w/2:.2f}V{r.y1-w/2:.2f}H{r.x0+w/2:.2f}Z"/>')

data["layers"] = {k: "".join(v) for k, v in layers.items()}
data["palette"] = list(palette.values())
data["labels"] = labels
json.dump(data, open(JSON_IO, "w"))
print({k: len(v) for k, v in layers.items()}, "palette", len(palette), "labels", len(labels), stats,
      "svg chars", sum(len(v) for v in data["layers"].values()))
