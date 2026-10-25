"""Make every track circuit name on the map tappable.

Most track names (e.g. 933T/922T) already sit under a link to their bonding drawing. For the ones that
don't, add a link with no drawing (nd=1): tapping the name opens a panel saying there's no drawing,
the same way 26kVA GEN behaves. Safe to run again: names it has already added count as covered.

    python3 build/track_names.py data/mantis_v3c.json
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geom import mat, attr

P = sys.argv[1]
d = json.load(open(P))
L = d["links"]
TRACK = re.compile(r"^(?:[A-Z]*\d+T(?:\(\d\))?|-|SIDING)(?:/(?:[A-Z]*\d+T(?:\(\d\))?|-|SIDING))*$")


def box(el):
    m = mat(attr(el, "transform"))
    ts = re.search(r'<tspan x="([^"]*)" y="([^"]*)"', el)
    if not ts:
        return None
    xs = [float(v) for v in ts.group(1).split()]
    y = float(ts.group(2))
    fs = float(attr(el, "font-size") or 10)
    sc = (m[0] ** 2 + m[1] ** 2) ** .5
    x0 = m[0] * xs[0] + m[2] * y + m[4]
    x1 = m[0] * xs[-1] + m[2] * y + m[4] + fs * sc * .6
    yy = m[1] * xs[0] + m[3] * y + m[5]
    return [round(min(x0, x1), 1), round(yy - fs * sc * .8, 1), round(max(x0, x1), 1), round(yy + fs * sc * .1, 1)]


def covered(b):
    for l in L:
        r = l.get("h") or l["r"]
        if not (b[2] < r[0] - 1 or b[0] > r[2] + 1 or b[3] < r[1] - 1 or b[1] > r[3] + 1):
            return True
    return False


added = []
nxt = max(l["i"] for l in L) + 1
for el in re.findall(r"<text [^>]*>.*?</text>", d["layers"]["base"], re.S):
    name = re.sub(r"<[^>]+>", "", el).strip().replace(" ", "")
    if not (TRACK.match(name) and re.search(r"\d+T", name)):
        continue
    b = box(el)
    if not b or covered(b):
        continue
    L.append(dict(i=nxt, u="", t="Track circuit", a="", l=name, f="", r=[b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], h=b, m=1, nd=1))
    nxt += 1
    added.append(name)
json.dump(d, open(P, "w"))
print("added", len(added), added)
