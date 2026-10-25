"""Fold map edits made in the Power App into the map file, so they're part of the snapshot.

    python3 build/apply_edits.py data/mantis_v3c.json <edits.csv or edits.json> [...]

Input: an export of the "Mantis map edits" Dataverse table (CSV or Excel saved as CSV, with columns
Name, Kind, Asset, Data), or the JSON from the map's "Export edits" button. Edits with the same Name
replace earlier ones. Baked edits are drawn like app edits but can't be removed in the app, so delete the
baked rows from the table afterwards (the script lists them).
"""
import sys, csv, json

P = sys.argv[1]
d = json.load(open(P))
baked = {e["id"]: e for e in d.get("baked_edits", [])}


def norm(r):
    g = lambda *ks: next((r[k] for k in ks if k in r and r[k] not in (None, "")), "")
    rid, kind = g("id", "Name", "name"), str(g("kind", "Kind")).lower()
    if not rid or kind not in ("asset", "links", "hide", "draw"):
        return None
    data = g("data", "Data") or "{}"
    if isinstance(data, str):
        data = json.loads(data)
    return {"id": str(rid), "kind": kind, "asset": str(g("asset", "Asset")), "data": data}


added = []
for f in sys.argv[2:]:
    if f.lower().endswith(".json"):
        rows = json.load(open(f))
    else:
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
    for r in rows:
        e = norm(r)
        if e:
            baked[e["id"]] = e
            added.append(e["id"])
d["baked_edits"] = list(baked.values())
json.dump(d, open(P, "w"))
print(f"baked {len(added)} edits ({len(baked)} in the map file). Delete these rows from the edits table:")
print("\n".join(added))
