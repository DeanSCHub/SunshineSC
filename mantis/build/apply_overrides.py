"""Apply the person's link corrections (overrides.json) to the viewer data."""
import sys, json, urllib.parse as up

data = json.load(open(sys.argv[1]))
ov = json.load(open(sys.argv[2]))
OUT = sys.argv[3]
L = data["links"]
by_i = {l["i"]: l for l in L}
log = []


def fkey(l):
    return up.unquote(up.unquote(l["u"].split("?")[0])).split("/")[-1].lower()


drop = set()
keep_files = {v.lower() for v in ov["stacked_keep"].values()}
for l in L:
    if "x" not in l:
        continue
    w = by_i[l["x"]]
    pair = {w["f"].lower(), l["f"].lower()}
    keep = pair & keep_files
    if not keep:
        continue
    k = keep.pop()
    loser, winner = (l, w) if w["f"].lower() == k else (w, l)
    drop.add(loser["i"])
    winner.pop("x", None)
    log.append(f"Stacked: kept {winner['f']}, removed {loser['f']}")

for l in L:
    k = fkey(l)
    if k in ov["use_address"] and l["u"] != ov["use_address"][k]:
        log.append(f"Address: {l['f']} -> {ov['use_address'][k].split('/')[-1]}")
        l["u"] = ov["use_address"][k]

for r in ov["relink"]:
    for l in L:
        if l["f"].upper() == r["file"].upper() and abs(l["r"][0] - r["near"][0]) < 4 and abs(l["r"][1] - r["near"][1]) < 4:
            l.update(u=r["to"], a=r["asset"], t=r["type"], f=r["to"].split("/")[-1])
            log.append(f"Relinked: {r['file']} at {r['near']} -> {l['f']} ({r['asset']})")

data["links"] = [l for l in L if l["i"] not in drop]
data["issues"] = [x for x in data["issues"]
                  if not (x["kind"] == "Two links stacked on one symbol")
                  and not (x["kind"] == "Same drawing, different addresses")
                  and x.get("asset") not in ov["no_drawing_needed"]]
data["override_log"] = data.get("override_log", []) + log
json.dump(data, open(OUT, "w"))
print("\n".join(log))
print("links", len(L), "->", len(data["links"]))
