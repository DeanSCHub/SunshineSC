# Mantis build pack (25 Oct 2026)

Everything needed to rebuild the Mantis Sunshine HTML map from MANTIS_Sunshine.pdf.
Attach this zip (and the PDF) at the start of a new chat, or put it in a code repository,
and Claude can carry on from here.

## What's in it
- data/mantis_v3c.json      the converted map + links + your corrections, ready to build
- build/overrides.json      your link decisions from the link check (edit this to change links)
- build/template_v3.html    the viewer (pan/zoom, search, panel, layers, tool box)
- build/page.py + chunk.py  turn the data + viewer into the single Mantis_Sunshine.html
- build/extract2.py, overlays.py, audit.py, v3data.py, apply_overrides.py
                            convert the PDF into the data (only needed if the PDF changes)
- build/mock_v4.py          the approved styling (tags by type, TPWS boxes, footprint signals)
- build/live_mock.py        sample live data for the live badges mockup
- build/taps.py, perf3.py   the tap and smoothness checks
- build/report.py           makes the link check workbook

## Rebuild the map from the data
Apply the approved styling (tags by type, TPWS boxes, footprint signals), then build the page:

    mkdir -p out
    python3 build/mock_v4.py data/mantis_v3c.json out/styled.json tags,tpws,signals
    MANTIS_CHUNK=1 python3 build/page.py out/styled.json build/template_v3.html out/Mantis_Sunshine.html

Live badges mockup (sample faults and work orders on real asset IDs):

    python3 build/live_mock.py out/styled.json out/live.json
    MANTIS_CHUNK=1 python3 build/page.py out/live.json build/template_v3.html out/Mantis_live_mockup.html

## Live badges
The viewer draws a badge beside any asset that has entries in `live` in the data:
red `!` = open fault (pulses if reported in the last 2 hours), outlined `!` = fault cleared in the last 7 days,
blue number = open work orders. Tapping a badge opens the asset, with a "Live work" list at the top of its panel.
There's a "Live work" switch in Layers. Without `live` in the data, nothing changes.
The item format is described at the top of `build/live_mock.py`; a real feed from the fault app and the
JDE work order list just needs to produce the same list, matched by asset ID as written on the map.

## Where things stand
- Built from your first version (triangles), drawing bands moved into the asset panel,
  tool box trimmed to CBI logic / signal power distribution / comms network, no outdoor mode.
- Six missing crossovers fixed; all link-check answers applied (incl. WVS903).
- Styling approved and part of the build: tag colours by type, TPWS boxes, footprint signals.
- Live badges mocked up with sample data; needs the real fault app and work order exports to go live.
- Next: SharePoint asset list (needs the Drawings library file list export).
