"""Find the geometry that only appears when the Speed and Approach overlays are switched on."""
import sys, json, collections
import pymupdf

SRC, OUT, TMP = sys.argv[1], sys.argv[2], sys.argv[3]
src = pymupdf.open(SRC)
OCGS = src.get_ocgs()
NAME2X = {v["name"]: k for k, v in OCGS.items()}
GROUPS = {
    "speed": ["Speed Overlay"],
    "approach": [n for n in NAME2X if (n.endswith("Approach Overlay") and n != "Approach Overlay")
                 or n in ("Hopkins Rd Overlay", "Troupes Rd Overlay", "Leakes Rd Overlay", "Paynes Rd Overlay",
                          "My Cottrell Rd Overlay", "Ferris Rd Overlay")],
}


def page_with(names, tag):
    d = pymupdf.open(SRC)
    on = [NAME2X[n] for n in names]
    d.set_layer(-1, on=on, off=[k for k in OCGS if k not in on])
    d.save(f"{TMP}/ovl_{tag}.pdf")
    return pymupdf.open(f"{TMP}/ovl_{tag}.pdf")[0]


def dkey(x):
    return ("d", x["type"], tuple(round(v, 1) for v in x["rect"]), x.get("color"), x.get("fill"), len(x["items"]))


def tkey(s):
    return ("t", "".join(chr(c[0]) for c in s["chars"]), tuple(round(v, 1) for v in s["bbox"]))


base = page_with([], "base")
bc = collections.Counter([dkey(x) for x in base.get_drawings()] + [tkey(s) for s in base.get_texttrace()])
out = {}
for g, names in GROUPS.items():
    p = page_with(names, g)
    rem = collections.Counter(bc)
    rects, texts = [], []
    for x in p.get_drawings():
        k = dkey(x)
        if rem[k] > 0:
            rem[k] -= 1
        else:
            r = x["rect"]
            rects.append([round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)])
    for s in p.get_texttrace():
        k = tkey(s)
        if rem[k] > 0:
            rem[k] -= 1
        else:
            texts.append(["".join(chr(c[0]) for c in s["chars"]).strip(), [round(v, 1) for v in s["bbox"]]])
    out[g] = dict(rects=rects, texts=texts)
    print(g, len(rects), len(texts))
d = json.load(open(OUT))
d["ovl"] = out
json.dump(d, open(OUT, "w"))
