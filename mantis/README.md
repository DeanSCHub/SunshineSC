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
- build/mock_v4.py          the proposed styling (tags by type, TPWS boxes, footprint signals) - not applied yet
- build/taps.py, perf3.py   the tap and smoothness checks
- build/report.py           makes the link check workbook

## Rebuild the map from the data
    MANTIS_CHUNK=1 python3 build/page.py data/mantis_v3c.json build/template_v3.html Mantis_Sunshine.html

## Where things stand
- Built from your first version (triangles), drawing bands moved into the asset panel,
  tool box trimmed to CBI logic / signal power distribution / comms network, no outdoor mode.
- Six missing crossovers fixed; all link-check answers applied (incl. WVS903).
- Waiting on decisions: tag colours by type, TPWS box style + colour key, footprint signals.
- Next: SharePoint asset list (needs the Drawings library file list export).
