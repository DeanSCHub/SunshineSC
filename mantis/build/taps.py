import sys, asyncio, json
from playwright.async_api import async_playwright
d = json.load(open(sys.argv[2]))
L = d["links"]; N = d["names"]
def rect_of(f, idx=0):
    m = [l for l in L if l["f"] == f]
    return m[idx]["r"]
CASES = [
  ("WVS933 number", N["WVS933"], "WVS933"),
  ("WVS933 triangle", rect_of("WVS933G.pdf"), "WVS933"),
  ("WVS933 TPWS arrow", rect_of("WVS933TPWS.pdf", 2), "WVS933"),
  ("WVS933 TPWS tag", rect_of("WVS933TPWS.PDF"), "WVS933"),
  ("TNT968 triangle (stacked)", rect_of("TNT968G.pdf"), "TNT968"),
  ("TNT968 number", N["TNT968"], "TNT968"),
  ("SUN920ZB box", N["SUN920ZB"], "SUN920ZB"),
  ("833W points", N["SUN833W"], "SUN833W"),
  ("Track circuit 919T/817T", [l for l in L if l.get("h") and l["l"] == "919T/817T"][0]["h"], "919T/817T"),
  ("Track circuit 922T/920T", [l for l in L if l.get("h") and l["l"] == "922T/920T"][0]["h"], "922T/920T"),
  ("Directions pin", [l["r"][0]+3, l["r"][1]-2, l["r"][2]-3, l["r"][3]-6] if False else [x for x in L if x["t"]=="Directions"][5]["r"], "*"),
  ("MW291 number", N["MW291"], "MW291"),
]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1180, "height": 820})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto("file://" + sys.argv[1]); await pg.wait_for_timeout(500)
        ok = 0
        for name, r, want in CASES:
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            # put that spot in the middle of the screen at a working zoom, then tap it
            await pg.evaluate(f"""() => {{ closeSheetForTest(); }}""") if False else None
            await pg.evaluate(f"""() => window.__mantisTest.view({cx}, {cy}, 2.4)""")
            await pg.wait_for_timeout(350)
            pos = await pg.evaluate(f"""() => window.__mantisTest.screen({cx}, {cy})""")
            await pg.mouse.click(pos[0], pos[1]); await pg.wait_for_timeout(450)
            title = await pg.evaluate("document.getElementById('sTitle').textContent")
            hl = await pg.evaluate("(() => { const r=document.querySelector('#hl rect'); return r ? [+r.getAttribute('x'), +r.getAttribute('width')] : null })()")
            good = want == "*" and bool(title) or title.upper().replace(" ", "") == want.upper().replace(" ", "")
            ok += good
            print(("PASS" if good else "FAIL"), f"{name:28} -> {title:12} highlight x={hl}")
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(150)
        print(ok, "/", len(CASES), "errors", errs)
        await b.close()
asyncio.run(main())
