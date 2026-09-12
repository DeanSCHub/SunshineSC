# JDE Work Order Paste & Master-Data Match

Adds a "Paste Work Orders" step to the SignalTech Hub work order page.
Technicians paste a tab-separated block copied from JDE; it's parsed,
matched against the master asset data (Dataverse table
`crcc8_sunshineassetsapp`) by Serial Number, shown in a review table
with unmatched rows flagged, and on confirm creates the Work Order
record(s) directly via the Dataverse Web API (the native
`{% entityform %}` can't run this prefill/lookup logic, so this bypasses
it with custom JS + a Web API create call).

## Files

- `work-order-paste-match.js` — parsing, master-data lookup, review UI, submit.
- `work-order-paste-match.css` — styling, matches the page's existing brand colors.
- `page-snippet.html` — the HTML block to add to the page content.

## What's confirmed vs. what you need to verify

**Confirmed from `Master_Data_v2.xlsx`'s "Dataversedata" sheet** (this sheet
is the actual Dataverse export, with real column logical names):

- Master asset table logical name: `crcc8_sunshineassetsapp` (derived from
  the primary key column `crcc8_sunshineassetsappid`).
- Match field: `crcc8_assetnumber` — holds values in the same format as
  JDE's Serial Number (verified against sample rows, e.g. `ADR-020306-ADRZB-INT`).
- KP field: `crcc8_kilometerpost`.
- The full non-system column list (Corridor, Work Group, Access Via, Fed
  From, Reset From, Drawing, Bonding, SAP, On/Off Track, Night/Day, Fenced,
  Signed, attributes A1–A5, vegetation description, etc.) — all wired up in
  `ASSET_TABLE.primaryFields` / `secondaryFields` in the JS file.

**NOT confirmed — this session had no Dataverse/Power Platform connection,
so these are placeholders guessed from naming convention. Before testing,
open the maker portal (make.powerapps.com > your environment > Tables),
open the table behind the "Work Order Submission" entity form, and check
its Columns list for the real Schema Names:**

1. `WORK_ORDER_TABLE.entitySet` in the JS (guessed `crcc8_workorders`) —
   also check the table's entity **set** name specifically (Table >
   Properties), not just its logical name, since that's what the Web API
   URL uses.
2. `WORK_ORDER_TABLE.fieldMap` — the seven JDE columns (Order Number, 2nd
   Item Number, Serial Number, Asset Number Description, Or Ty
   Description, Planned Start Date, Complete By) need their real logical
   names substituted in.
3. `WORK_ORDER_TABLE.enrichedFieldMap` — whether there's already a column
   on the Work Order table to hold the matched KP (and whether you want
   more than KP copied across — add pairs here for any others).
4. Also double check `ASSET_TABLE.entitySet` (guessed `crcc8_sunshineassetsapps`)
   against the real entity set name — Dataverse's default pluralization
   isn't always a simple "+s".

A quick way to sanity-check any of the above once you're signed into the
portal: visit `https://<your-site>/_api/<entitySet>?$top=1` in the browser;
a JSON response confirms the entity set name, a 404 means it's wrong.

## Deployment steps

1. In Power Pages Studio: **Content > Web Files > Upload file**, upload
   `work-order-paste-match.js` and `work-order-paste-match.css` as-is.
2. Open the Work Order page and add the contents of `page-snippet.html`
   directly above the existing `{% entityform name: "Work Order Submission" %}`
   block.
3. Fix the config values in `work-order-paste-match.js` per the checklist
   above.
4. **Table permissions & Web API site settings** (required for the portal
   to call `/_api/...` at all):
   - `crcc8_sunshineassetsapp`: add a **read-only** Table Permission scoped
     to whatever web role your technicians have (Global or Account scope),
     and a site setting `Webapi/crcc8_sunshineassetsapp/enabled` = `true`.
   - The Work Order table: it likely already has create permissions (the
     entity form uses them), but double-check the matching
     `Webapi/<table>/enabled` site setting exists and includes the `POST`
     verb — entity forms sometimes only need a narrower site setting than
     raw Web API calls do.
5. Test end-to-end: paste the sample block from the feature request,
   confirm KP and the other matched fields show up, confirm an unmatched
   Serial Number is flagged and blocks submission until the override
   checkbox is ticked, then submit and verify the created Work Order
   record(s) in Dataverse.

## Behavior notes

- Rows are matched by exact Serial Number match (case-insensitive on the
  client side; Dataverse's default text column collation is
  case-insensitive too). A genuine typo or a truly missing asset record
  both surface the same "No master-data match" badge — that's
  intentional, per the request to catch both.
- Parse errors (wrong column count, non-numeric Order Number, bad date
  format) block that row from submission entirely; they can't be
  overridden, only fixed by correcting the paste.
- Unmatched-but-otherwise-valid rows can be submitted anyway via an
  explicit checkbox, for the case where an asset is genuinely new and
  hasn't been added to master data yet.
- Dates are parsed as dd/mm/yyyy (matches the sample data, e.g.
  `21/09/2026`) and sent to Dataverse as `YYYY-MM-DD`.
