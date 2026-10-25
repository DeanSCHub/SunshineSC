"""Audit every Mantis link against the text under it, and build tight hotspots for the viewer."""
import sys, re, json, collections, urllib.parse as up
import pymupdf

PDF, JSON_IN, JSON_OUT = sys.argv[1], sys.argv[2], sys.argv[3]
page = pymupdf.open(PDF)[0]
data = json.load(open(JSON_IN))
links = data["links"]

WORDS = [dict(t=w[4], r=(w[0], w[1], w[2], w[3])) for w in page.get_text("words")]
ID_RE = re.compile(r"^[A-Z]{1,4}\d{1,4}[A-Z]{0,4}\d?$")


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def inter(a, b, pad=0):
    return a[0] - pad < b[2] and b[0] - pad < a[2] and a[1] - pad < b[3] and b[1] - pad < a[3]


def centre(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def dist(a, b):
    dx = max(a[0] - b[2], 0, b[0] - a[2])
    dy = max(a[1] - b[3], 0, b[1] - a[3])
    return (dx * dx + dy * dy) ** .5


def words_in(r):
    out = []
    for w in WORDS:
        cx, cy = centre(w["r"])
        if r[0] - 1 <= cx <= r[2] + 1 and r[1] - 1 <= cy <= r[3] + 1:
            out.append(w)
    return out


def union(rs):
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))


def fname_key(u):
    f = up.unquote(up.unquote(u.split("?")[0])).rstrip("/").split("/")[-1]
    return f.lower()


issues = []
BANDS = {"Signalling arrangement plan", "Bonding plan", "Control tables"}

# ---------- per link: tighten to the words under it, check they name the asset
for i, l in enumerate(links):
    l["i"] = i
    r = tuple(l["r"])
    ws = words_in(r)
    l["words"] = [w["t"] for w in ws]
    l["hot"] = None
    a = l.get("a") or ""
    if l["t"] in BANDS or l["t"] == "Directions":
        continue
    if ws:
        ids = [w for w in ws if ID_RE.match(norm(w["t"]))]
        def names(w):
            t = norm(w["t"])
            A = norm(a)
            return (t == A or t == A.replace("TPWS", "") or (A.startswith(t) and len(t) >= 4)
                    or (len(t) >= 3 and A.endswith(t) and re.match(r"^[A-Z]*\d", t))          # 833W in SUN833W, A201 in DPWA201
                    or (l["t"] == "Axle counter overview" and re.match(r"^[A-Z]?\d+[A-Z]*T(/|$)", w["t"]))  # section labels
                    or (re.match(r"^\d+[A-Z]*T/", w["t"]) and l["t"] in ("Track circuit", "Location case")))
        match = [w for w in ws if a and names(w)]
        l["hot"] = list(union([w["r"] for w in ws]))
        if a and not match and ids:
            other = [w["t"] for w in ids]
            issues.append(dict(kind="Link opens a different asset", i=i, text=" ".join(l["words"]), opens=l["f"], asset=a,
                               note=f"Text under the link says {', '.join(other)} but the link opens {l['f']}"))
        elif a and not match:
            issues.append(dict(kind="Link sits on an indicator, not the name", i=i, text=" ".join(l["words"]), opens=l["f"], asset=a,
                               note="Link covers a small label (route/speed indicator) rather than the asset name"))

# ---------- per asset: find the name text on the map near its links
by_asset = collections.defaultdict(list)
for l in links:
    if l.get("a"):
        by_asset[l["a"]].append(l)

name_hot = {}
for a, ls in by_asset.items():
    key = norm(a)
    base_key = key
    for suf in ("TPWS",):
        if key.endswith(suf):
            base_key = key[:-len(suf)]
    lr = union([tuple(l["r"]) for l in ls if l["t"] not in ("TPWS",)] or [tuple(l["r"]) for l in ls])
    best, bd = None, 140
    short = re.sub(r"^[A-Z]{2,4}(?=A\d)", "", base_key)      # DPWA201 -> A201
    for w in WORDS:
        if norm(w["t"]) in (base_key, short):
            d = dist(w["r"], lr)
            if d < bd:
                best, bd = w, d
    if best:
        name_hot[a] = list(best["r"])
    else:
        types = collections.Counter(l["t"] for l in ls)
        if types.get("Signal"):
            issues.append(dict(kind="Name not found near link", i=ls[0]["i"], text="", opens=ls[0]["f"], asset=a,
                               note="Couldn't find this signal's number written near its link"))

# ---------- signal numbers written on the map with no link
SIG_WORD = re.compile(r"^(MW|SUN|WVS|WVD|DPK|DPW|MEL|MNW|TLN|TNT|PWN|ADR|RBK|WFY|FSY|MFY|CSP|TOT|KEN|MYD|A)\d{2,4}$")
linked_names = {norm(a) for a in by_asset}
for w in WORDS:
    t = norm(w["t"])
    if SIG_WORD.match(t) and t not in linked_names:
        near = [l for l in links if dist(tuple(l["r"]), w["r"]) < 25]
        issues.append(dict(kind="Name on map with no link", i=near[0]["i"] if near else -1, text=w["t"], opens=near[0]["f"] if near else "",
                           asset=t, note="This number is on the map but nothing links to " + t, r=list(w["r"])))

# ---------- duplicates and odd URLs
seen = collections.defaultdict(list)
for l in links:
    if l.get("a"):
        seen[(l["a"], fname_key(l["u"]))].append(l)
for (a, fk), ls in seen.items():
    urls = {l["u"] for l in ls}
    if len(urls) > 1:
        issues.append(dict(kind="Same drawing, different addresses", i=ls[0]["i"], text=a, opens=fk, asset=a,
                           note="; ".join(sorted(urls))))
for l in links:
    u = up.unquote(l["u"])
    if re.search(r"/Drawings//", u):
        issues.append(dict(kind="Double slash in address", i=l["i"], text=" ".join(l["words"]), opens=l["f"], asset=l.get("a", ""), note=l["u"]))
    if l["f"].lower() in (".pdf", "") and l["t"] not in ("Directions",) and not l["u"].startswith("mailto"):
        issues.append(dict(kind="Link has no file name", i=l["i"], text=" ".join(l["words"]), opens=l["f"], asset=l.get("a", ""), note=l["u"]))
    if l["u"].startswith("http://"):
        issues.append(dict(kind="Not a secure address", i=l["i"], text=" ".join(l["words"]), opens=l["f"], asset=l.get("a", ""), note=l["u"]))
    if re.search(r"\.pdf$", up.unquote(l["u"].split("?")[0]), re.I) and re.search(r"\.PDF$", l["u"].split("?")[0]):
        pass

data["name_hot"] = name_hot
data["issues"] = issues
json.dump(data, open(JSON_OUT, "w"))
c = collections.Counter(x["kind"] for x in issues)
print(len(links), "links;", len(by_asset), "assets;", len(name_hot), "names found")
for k, v in c.most_common():
    print(f"  {v:4}  {k}")
