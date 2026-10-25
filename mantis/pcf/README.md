# Mantis map for Power Apps

The Mantis map packaged as a **code component** (PCF) for canvas apps. It's the same interactive map as
`Mantis_Sunshine.html` (pan, zoom, search, tap an asset for its drawings), as a control you can put on a screen.

The file to import is `MantisMap_<version>.zip`, an unmanaged solution containing one control,
**Mantis map** (`mantis_Mantis.MantisMap`). Publisher: Mantis SC, prefix `mantis`.

## One-off setup

1. **Allow code components in canvas apps.** A Power Platform admin (may need IT) goes to the
   Power Platform admin centre > Environments > *your environment* > Settings > Product > Features
   and turns on **Allow publishing of canvas apps with code components**. Without this, the control
   won't appear in the app.
2. **Import the solution.** make.powerapps.com > pick the environment > Solutions > Import solution >
   choose `MantisMap_1_0_0.zip` > Next > Import.

## Add the map to an app

1. Open (or create) the canvas app in Power Apps Studio.
2. Insert > **Get more components** > **Code** tab > tick **Mantis map** > Import.
3. Insert > Code components > **Mantis map**. Make it fill the screen, e.g. X `0`, Y `0`,
   Width `Parent.Width`, Height `Parent.Height`.

That's all you need for a working map. The properties below are optional.

| Property | Direction | What it does |
|---|---|---|
| `Asset` | in | An asset ID (e.g. `"WVS933"`). The map flies there and opens its panel. |
| `LinkHandling` | in | `Browser` (default): drawings open in a new tab. `App`: drawings come out through `LinkToOpen` instead. |
| `SelectedAsset` | out | The asset the user has open, blank when the panel is closed. |
| `SelectedKind` | out | What that asset is: Signal, Points, Location case, UPS... |
| `LinkToOpen` | out | With `LinkHandling` = `App`: the drawing the user tapped. |

### Examples (Power Fx)

- Show what's selected in a label: `MantisMap1.SelectedAsset & " " & MantisMap1.SelectedKind`
- Open the map at the asset picked in a gallery: set the map's `Asset` to `Gallery1.Selected.AssetId`
- Open the map at an asset passed in a link to the app (`...&asset=WVS933`): set `Asset` to `Param("asset")`
- **Drawings on phones/tablets:** if tapping a drawing does nothing in the Power Apps mobile app, set
  `LinkHandling` to `App` and set the map's **OnChange** to
  `If(!IsBlank(Self.LinkToOpen), Launch(Self.LinkToOpen))`

## Updating the map

When the PDF, links or styling change, Claude rebuilds the map and makes a new zip with a higher version
(e.g. `MantisMap_1_0_1.zip`). Then:

1. Import the new zip as above (it upgrades the existing solution).
2. Open the app in Studio. It offers to **update code components**; accept.
3. Save and **Publish** the app.

## If something's wrong

- **Control isn't in "Get more components"**: the setting in step 1 is off, or the solution was imported
  into a different environment.
- **Map area is blank**: the environment's content security policy for canvas apps may block the map's
  inline scripts. In the admin centre > Settings > Privacy + Security > Content security policy, check
  whether canvas enforcement is on; `script-src` needs `'unsafe-inline'`.
- **Drawings don't open on mobile**: use `LinkHandling` = `App` with the OnChange above.

## Building (for Claude / developers)

    cd mantis/pcf
    npm install                 # once
    ./build.sh 1.0.1            # embeds ../out/Mantis_Sunshine.html, builds, packs ../out/MantisMap_1_0_1.zip

Build the map page first (see the main README). `build.sh` gets `pac` and the .NET runtime it needs from
NuGet (`scripts/get-pac.sh`, cached in `~/.cache/mantis-pac`). Always use a version higher than the last
one imported.

How it works: the control puts the map page in an iframe, so the map's full-page styles can't affect the
app. The two sides talk with `postMessage`: the app sends `mantis:select`; the map sends
`mantis:selected`, `mantis:closed` and, in App link mode, `mantis:open`. The map only enables these when
the control sets `window.MANTIS_EMBED`, so the standalone page is unaffected.
`solution/src` is the unpacked solution. `build.sh` copies the built control into it and packs it with
`pac solution pack`.
