"""Add SAMPLE live data (faults and work orders) to the viewer data, so the live badges can be previewed.

The real feed would have the same shape: one item per open work order or recent fault, keyed by asset ID.
    a      asset ID as written on the map (e.g. WVS933)
    k      "fault" or "wo"
    ref    fault number / JDE work order number
    title  short description
    open   faults only: still open (False = cleared in the last 7 days)
    fresh  faults only: reported in the last 2 hours (badge pulses)
    when   faults: reported (open) or cleared time
    status, due   work orders only
    url    link to the item in the fault app / JDE
"""
import sys, json, random
from datetime import datetime, timedelta

data = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
NOW = datetime(2026, 10, 25, 8, 42)
rng = random.Random(7)

types = {}
for l in data["links"]:
    if l.get("a") and l["a"] in data["names"]:
        types.setdefault(l["a"], set()).add(l["t"])


def kind(a):
    t = types[a]
    for k in ("Signal", "Points", "UPS", "Location case", "Level crossing", "Track circuit"):
        if k in t:
            return k
    return None


FAULTS = {
    "Signal": ["Signal lamp proving failure", "Signal displaying stop aspect in error", "Signal flickering, reported by driver"],
    "Points": ["Points failed to detect normal", "Points slow to swing reverse", "Points out of correspondence"],
    "UPS": ["UPS on battery, mains supply lost", "UPS battery alarm"],
    "Location case": ["Location case door alarm", "Location case high temperature alarm"],
    "Level crossing": ["Crossing bells not ringing", "Boom gate slow to lower"],
    "Track circuit": ["Track circuit showing occupied with no train", "Track circuit dropping out intermittently"],
}
WOS = {
    "Signal": ["PM 3-monthly signal inspection", "Replace LED signal head module", "Sighting check after vegetation works"],
    "Points": ["PM points service and adjustment", "Replace points detector rod", "Lubricate slide chairs"],
    "UPS": ["PM 6-monthly UPS battery test", "Replace UPS battery bank"],
    "Location case": ["PM annual location case inspection", "Replace door seal"],
    "Level crossing": ["PM monthly level crossing test", "Replace boom arm lights"],
    "Track circuit": ["PM track circuit test and record", "Replace rail bond"],
}

cands = [a for a in sorted(types) if kind(a)]
rng.shuffle(cands)
items = []
fn, wn = 241000, 30551000
for i, a in enumerate(cands[:44]):
    k = kind(a)
    roll = rng.random()
    if roll < 0.22:      # open fault (some also have a work order)
        age = rng.choice([25, 70, 190, 600, 1500])
        fn += rng.randint(3, 40)
        items.append(dict(a=a, k="fault", ref=f"F-{fn}", title=rng.choice(FAULTS[k]), open=True, fresh=age < 120,
                          when=(NOW - timedelta(minutes=age)).isoformat(timespec="minutes"), url="#"))
        if rng.random() < 0.5:
            wn += rng.randint(5, 300)
            items.append(dict(a=a, k="wo", ref=str(wn), title=f"Rectify fault F-{fn}", status="Assigned",
                              due=(NOW + timedelta(days=1)).strftime("%d %b"), url="#"))
    elif roll < 0.4:     # fault cleared in the last week
        fn += rng.randint(3, 40)
        items.append(dict(a=a, k="fault", ref=f"F-{fn}", title=rng.choice(FAULTS[k]), open=False,
                          when=(NOW - timedelta(hours=rng.randint(10, 160))).isoformat(timespec="minutes"), url="#"))
    else:                # open work orders
        for _ in range(1 if rng.random() < 0.7 else 2):
            wn += rng.randint(5, 300)
            items.append(dict(a=a, k="wo", ref=str(wn), title=rng.choice(WOS[k]),
                              status=rng.choice(["Open", "Assigned", "In progress"]),
                              due=(NOW + timedelta(days=rng.randint(-3, 20))).strftime("%d %b"), url="#"))

# make sure the spots used in screenshots and checks have something to show
items += [
    dict(a="WVS933", k="fault", ref="F-241987", title="Signal displaying stop aspect in error", open=True, fresh=True,
         when=(NOW - timedelta(minutes=35)).isoformat(timespec="minutes"), url="#"),
    dict(a="WVS933", k="wo", ref="30551988", title="Rectify fault F-241987", status="Assigned", due="25 Oct", url="#"),
    dict(a="WVS933", k="wo", ref="30551302", title="PM 3-monthly signal inspection", status="Open", due="02 Nov", url="#"),
    dict(a="SUN920ZB", k="wo", ref="30551410", title="PM annual location case inspection", status="Open", due="29 Oct", url="#"),
    dict(a="MW453UPS", k="fault", ref="F-241850", title="UPS on battery, mains supply lost", open=False,
         when=(NOW - timedelta(hours=30)).isoformat(timespec="minutes"), url="#"),
]
data["live"] = dict(updated=NOW.isoformat(timespec="minutes"), sample=True, items=items)
json.dump(data, open(OUT, "w"))
n = lambda f: sum(1 for i in items if f(i))
print("assets", len({i["a"] for i in items}), "open faults", n(lambda i: i["k"] == "fault" and i["open"]),
      "recent faults", n(lambda i: i["k"] == "fault" and not i["open"]), "work orders", n(lambda i: i["k"] == "wo"))
