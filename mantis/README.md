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
- pcf/                      the map as a Power Apps code component (see pcf/README.md)
- build/filecheck.py        checks every link against a SharePoint file list export; makes the file check workbook

## Rebuild the map from the data
Apply the approved styling (tags by type, TPWS boxes, footprint signals), then build the page:

    mkdir -p out
    python3 build/mock_v4.py data/mantis_v3c.json out/styled.json tags,tpws,signals
    MANTIS_CHUNK=1 python3 build/page.py out/styled.json build/template_v3.html out/Mantis_Sunshine.html

Live badges mockup (sample faults and work orders on real asset IDs):

    python3 build/live_mock.py out/styled.json out/live.json
    MANTIS_CHUNK=1 python3 build/page.py out/live.json build/template_v3.html out/Mantis_live_mockup.html

## Power Apps (canvas app code component)
`pcf/` wraps the built map as a code component in an importable solution. Setup steps for the
environment and app are in `pcf/README.md`.

    cd pcf && npm install && ./build.sh 1.0.0      # -> out/MantisMap_1_0_0.zip

## SharePoint file check
Export Shared Documents > Sunshine to Excel (all items, no folders), then:

    python3 build/filecheck.py MantisSunshineDrawings.xlsx data/mantis_v3c.json out/Mantis_file_check.xlsx

It prints `use_address` entries for links it can fix (same file name in ~Assets). Add them to
build/overrides.json and apply with:

    python3 build/apply_overrides.py data/mantis_v3c.json build/overrides.json data/mantis_v3c.json

Every track circuit name on the map is tappable. Names with no bonding drawing get a "No drawing for this
track" link; re-run this after rebuilding the data from the PDF (safe to run more than once):

    python3 build/track_names.py data/mantis_v3c.json

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
- SharePoint file check done (export of 25 Oct 2026): 9 broken links fixed to their ~Assets copies.
  Still broken: axle counter overviews for DPK935ZB, DPK927ZB, DPK932ZB, DPK820ZB (no file in SharePoint)
  and two links with no file name. 103 drawings in ~Assets aren't linked from the map; see the workbook.
- Power Apps: code component + solution (MantisMap 1.0.1), tested in a local harness and in iPad (A16)
  emulation inside a scaled 16:9 app; not yet imported into an environment.
- All 439 track circuit names tappable (14 added with "No drawing for this track").
- Parked: live badges (needs fault app and JDE work order exports).
- Left for now (no drawings): MW325 CHCPB, A26T, A364UPS, 26kVA GEN.
