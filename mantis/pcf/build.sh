#!/usr/bin/env bash
# Build the Mantis map code component and pack it into an importable solution.
#   ./build.sh 1.0.1            -> ../out/MantisMap_1_0_1.zip
# Every release needs a higher version than the last import, or Power Apps won't offer the update.
# Needs: npm install (once), and pac + DOTNET_ROOT from scripts/get-pac.sh.
set -euo pipefail
cd "$(dirname "$0")"
VER="${1:?usage: ./build.sh <version, e.g. 1.0.1>}"
[[ "$VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must look like 1.0.1"; exit 1; }
if [ -z "${PAC:-}" ]; then eval "$(scripts/get-pac.sh)"; fi
export DOTNET_CLI_TELEMETRY_OPTOUT=1 PAC_CLI_TELEMETRY_OPTOUT=1

# 1. the map page and the component, both stamped with this version
node scripts/embed-map.js "${MAP:-../out/Mantis_Sunshine.html}"
sed -i -E "s/(constructor=\"MantisMap\" version=\")[0-9.]+\"/\1$VER\"/" MantisMap/ControlManifest.Input.xml
npm run build --silent

# 2. the solution
C=solution/src/Controls/mantis_Mantis.MantisMap
cp out/controls/MantisMap/ControlManifest.xml out/controls/MantisMap/bundle.js "$C/"
sed -i -E "s#<Version>[0-9.]+</Version>#<Version>$VER.0</Version>#" solution/src/Other/Solution.xml
ZIP="../out/MantisMap_${VER//./_}.zip"
mkdir -p ../out
"$PAC" solution pack --zipfile "$ZIP" --folder solution/src --packagetype Unmanaged
echo "built $ZIP"
