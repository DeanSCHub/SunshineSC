import sys, json

data = json.load(open(sys.argv[1]))
tpl = open(sys.argv[2]).read()
out = sys.argv[3]

light, dark, rules = [], [], []
for p in data["palette"]:
    i = p["i"]
    light.append(f"--p{i}:{p['light']};")
    dark.append(f"--p{i}:{p['dark']};")
    if p["role"] == "fill":
        rules.append(f".m .f{i}{{fill:var(--p{i})}}")
    elif p["role"] in ("stroke", "edge"):
        rules.append(f".m .s{i}{{stroke:var(--p{i})}}")
    else:
        rules.append(f".m .t{i}{{fill:var(--p{i})}}")
rules.append(".m .tw{fill:var(--tw)}")
for p in data["palette"]:
    if p["role"] == "text" and p["light"].lower() in ("#ffffff", "#fff", "#f3f7fa"):
        rules.append(f':root[data-theme="outdoor"] #map .t{p["i"]}{{stroke:none}}')

swatch_light = "--tw:#ffffff;--tpws-sw:#c93ba8;--kp-sw:#d9681f;--speed-sw:#1d2a33;--appr-sw:#2f8fe0;--supply-sw:#5c6773;--p-station:#6d2a8c;"
swatch_dark = "--tw:#0e1a22;--tpws-sw:#e870cf;--kp-sw:#f0a061;--speed-sw:#cfd9e0;--appr-sw:#5fb0f5;--supply-sw:#93a1ad;--p-station:#b07ad0;"

pal_light = "  " + "".join(light) + swatch_light
outdoor = []
for p in data["palette"]:
    v = p["light"]
    if p["src"] == "#000000" and p["role"] in ("stroke", "text"):
        v = "#000000"
    outdoor.append(f"--p{p['i']}:{v};")
pal_outdoor = "  " + "".join(outdoor) + swatch_light.replace("--tw:#ffffff", "--tw:#ffffff")
pal_dark = "  " + "".join(dark) + swatch_dark

html = tpl.replace("__PAL_LIGHT__", pal_light).replace("__PAL_DARK__", pal_dark).replace("__PAL_OUTDOOR__", pal_outdoor)
html = html.replace("</style>", "\n" + "\n".join(rules) + "\n" + data.get("extra_css", "") + "\n</style>", 1)
W = data["w"]
Y0 = data["top"]
H = data["bot"] - data["top"]
html = html.replace("__W__", f"{W:.0f}").replace("__H__", f"{H:.0f}").replace("__Y0__", f"{Y0:.0f}")
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chunk import layer_markup, CELL
ncells = 0
for k, v in data["layers"].items():
    if os.environ.get("MANTIS_CHUNK") == "1":
        v, n = layer_markup(v, Y0)
        ncells += n
    html = html.replace(f"__L_{k}__", v)
html = html.replace("__CELL__", str(CELL))
print("cells", ncells)
LEG = [("160", "#dd1717"), ("130", "#ffba00"), ("115", "#7d9ec0"), ("80", "#40e0d0"), ("65", "#b58442"), ("50", "#ba81d5"), ("15", "#009300")]
legend = []
for v, h in LEG:
    m = [p for p in data["palette"] if p["src"] == h and p["role"] == "stroke"]
    legend.append({"v": v, "c": f"var(--p{m[0]['i']})" if m else h})
data["legend"] = legend
slim = {k: data.get(k) for k in ("w", "top", "bot", "links", "chrome", "labels", "mini", "legend", "names", "live", "baked_edits")}
html = html.replace("__DATA__", json.dumps(slim, separators=(",", ":")).replace("</", "<\\/"))
open(out, "w").write(html)
print("bytes", len(html.encode()))
