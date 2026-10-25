import sys, asyncio, statistics
from playwright.async_api import async_playwright
async def scenario(pg, name, setup, drag):
    await pg.evaluate(setup); await pg.wait_for_timeout(1500)
    await pg.evaluate("window.__f = []")
    await pg.mouse.move(590, 410); await pg.mouse.down()
    for i in range(40):
        await pg.mouse.move(590 - i * drag, 410 - i * 2); await pg.wait_for_timeout(8)
    await pg.mouse.up(); await pg.wait_for_timeout(2600)
    f = sorted(await pg.evaluate("window.__f.slice(1)"))
    print(f"  {name:26} frames {len(f):4} median {statistics.median(f):5.1f}ms p95 {f[int(len(f)*.95)]:6.1f}ms worst {f[-1]:6.1f}ms >50ms {sum(x>50 for x in f)}")
async def run(path, throttle):
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 1180, "height": 820}, device_scale_factor=2)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        await pg.goto("file://" + path); await pg.wait_for_timeout(800)
        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": throttle})
        await pg.evaluate("""() => { window.__f = []; let last = performance.now();
          const tick = t => { window.__f.push(t - last); last = t; requestAnimationFrame(tick); }; requestAnimationFrame(tick); }""")
        print(f"cpu x{throttle}")
        hook = "window.__mantisTest" 
        await scenario(pg, "overview fling", f"{hook} ? {hook}.view(7200, 1400, 0.09) : 0", 12)
        await scenario(pg, "mid zoom fling", f"{hook} ? {hook}.view(5000, 1350, 0.6) : 0", 12)
        await scenario(pg, "working zoom fling", f"{hook} ? {hook}.view(4200, 1300, 2.2) : 0", 12)
        await b.close()
async def main():
    for t in (1, 4): await run(sys.argv[1], t)
asyncio.run(main())
