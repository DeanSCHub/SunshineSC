"""v3 data: fix link addresses, resolve stacked links, find names, strip the drawing bands off the map."""
import sys, re, json, collections, urllib.parse as up
import pymupdf

PDF, JSON_IN, JSON_OUT = sys.argv[1], sys.argv[2], sys.argv[3]
page = pymupdf.open(PDF)[0]
WORDS = [dict(t=w[4], r=(w[0], w[1], w[2], w[3])) for w in page.get_text("words")]
data = json.load(open(JSON_IN))
links = data["links"]
issues = [x for x in data["issues"] if x["kind"] != "Link sits on an indicator, not the name"]
BANDS = {"Signalling arrangement plan", "Bonding plan", "Control tables"}


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def dist(a, b):
    dx = max(a[0] - b[2], 0, b[0] - a[2])
    dy = max(a[1] - b[3], 0, b[1] - a[3])
    return (dx * dx + dy * dy) ** .5


def overlap(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0
    return ix * iy / min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


# ---------- 1. address fixes
fixes = []
for l in links:
    u0 = l["u"]
    u = re.sub(r"(/Sunshine/Drawings)//+", r"\1/", u0)
    if u != u0:
        l["u"] = u
        fixes.append(dict(kind="Fixed: removed double slash", text=" ".join(l["words"]), before=u0, after=u))
    if l["f"].lower() in (".pdf", "") and l["t"] not in ("Directions", "Email", "Link"):
        l["missing"] = True

# ---------- 1b. one signal filed under two IDs (DPWA201G.pdf vs A201TPWS.pdf): use the ID written on the map
ids = {l.get("a") for l in links if l.get("a")}
merged = {}
for x in sorted(ids):
    m = re.match(r"^[A-Z]{2,4}(A\d+)$", x)
    if m and m.group(1) in ids:
        merged[x] = m.group(1)
for l in links:
    if l.get("a") in merged:
        l["a"] = merged[l["a"]]
if merged:
    fixes.append(dict(kind="Merged IDs", text=", ".join(f"{k} = {v}" for k, v in merged.items()), before="", after=""))
data["name_hot"] = {merged.get(k, k): v for k, v in data["name_hot"].items()}

# ---------- 2. names on the map (including names run together with other text)
name_hot = dict(data["name_hot"])
by_asset = collections.defaultdict(list)
for l in links:
    if l.get("a"):
        by_asset[l["a"]].append(l)
for a, ls in by_asset.items():
    if a in name_hot:
        continue
    key = norm(a)
    lr = [tuple(l["r"]) for l in ls]
    best, bd = None, 60
    for w in WORDS:
        t = norm(w["t"])
        if len(t) > len(key) and t.endswith(key):
            d = min(dist(w["r"], r) for r in lr)
            if d < bd:
                # tighten to the trailing part of the word
                frac = len(key) / len(t)
                x0, y0, x1, y1 = w["r"]
                best, bd = (x1 - (x1 - x0) * frac, y0, x1, y1), d
    if not best:
        short = re.sub(r"^[A-Z]+(?=\d)", "", key)          # SUN833W -> 833W (points are labelled without the prefix)
        if short != key and len(short) >= 3:
            for w in WORDS:
                if norm(w["t"]) == short:
                    d = min(dist(w["r"], r) for r in lr)
                    if d < bd:
                        best, bd = w["r"], d
    if best:
        name_hot[a] = list(best)

# ---------- 3. stacked links: same spot, different assets. Keep the one whose name is written there.
stacked = 0
SKIP = {"Directions", "Signalling arrangement plan", "Bonding plan", "Control tables"}
for i, a in enumerate(links):
    if a["t"] in SKIP or a.get("loser") is not None:
        continue
    for b in links[i + 1:]:
        if b["t"] in SKIP or b.get("loser") is not None or b["u"].lower() == a["u"].lower():
            continue
        if not a.get("a") and not b.get("a"):
            continue
        if a.get("a") and b.get("a") and a["a"] == b["a"]:
            continue
        if overlap(tuple(a["r"]), tuple(b["r"])) > .8 and min(a["r"][2] - a["r"][0], b["r"][2] - b["r"][0]) < 40:
            def near(l):
                if not l.get("a"):
                    return 1e8                     # an asset's own symbol beats a general drawing link
                n = name_hot.get(l["a"])
                return dist(tuple(n), tuple(l["r"])) if n else 1e9
            lose = a if near(a) > near(b) else b
            win = b if lose is a else a
            lose["loser"] = win["i"]
            stacked += 1
            issues.append(dict(kind="Two links stacked on one symbol", i=lose["i"], asset=lose.get("a") or win.get("a", ""), text=" ".join(lose["words"]),
                               opens=lose["f"], note=f"{win['f']} and {lose['f']} sit on the same spot. Map now opens {win['f']} "
                                                       f"(its name is written there); {lose['f']} is listed in that panel under 'Also linked here'."))
            if lose is a:
                break

# ---------- 4. take the drawing bands off the map (they're offered from each asset instead)
pal = {(p["role"], p["src"]): p["i"] for p in data["palette"]}
BAND_FILLS = {pal.get(("fill", h)) for h in ("#7b7bc0", "#7d9ec0", "#7e7eec", "#80c3d9", "#81e9b2", "#ba81d5", "#ffad5b")} - {None}
BAND_TEXT = re.compile(r"SIGNALLING ARRANGEMENT|BONDING PLANS|CONTROL TABLES|ARRANGEMENT PLANS|^\s*PLANS\s*$|^\s*BLES", re.I)
EL = re.compile(r"<path [^>]*/>|<text [^>]*>.*?</text>", re.S)
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from geom import mat, points, attr

removed = {"shapes": 0, "text": 0}


def strip(m):
    el = m.group(0)
    if el.startswith("<path"):
        cl = attr(el, "class") or ""
        fills = [int(c[1:]) for c in cl.split() if c.startswith("f")]
        if fills and fills[0] in BAND_FILLS:
            pts, _ = points(attr(el, "d") or "", mat(attr(el, "transform")))
            if pts:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if (w >= 100 and 30 <= h <= 50) or (w >= 150 and h >= 100):
                    removed["shapes"] += 1
                    return ""
        return el
    if BAND_TEXT.search(re.sub(r"<[^>]+>", "", el)):
        removed["text"] += 1
        return ""
    return el


data["layers"]["base"] = EL.sub(strip, data["layers"]["base"])

# ---------- 5. slim link records for the viewer
slim = []
for l in links:
    rec = dict(i=l["i"], u=l["u"], t=l["t"], a=l.get("a", ""), l=l.get("l", ""), f=l["f"], r=l["r"])
    if l.get("hot"):
        rec["h"] = [round(v, 1) for v in l["hot"]]
    if l.get("g"):
        rec["g"] = l["g"]
    if l.get("p"):
        rec["p"] = l["p"]
    if l.get("loser") is not None and l.get("loser") is not False:
        rec["x"] = l["loser"]
    if l.get("missing"):
        rec["m"] = 1
    slim.append(rec)
data["links"] = slim
data["names"] = {a: [round(v, 1) for v in r] for a, r in name_hot.items()}
data["issues"] = issues
data["fixes"] = fixes
json.dump(data, open(JSON_OUT, "w"))
print("names", len(name_hot), "of", len(by_asset), "| stacked", stacked, "| fixes", len(fixes), "| bands removed", removed)
print(collections.Counter(x["kind"] for x in issues))
