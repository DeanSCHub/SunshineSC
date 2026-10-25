#!/usr/bin/env bash
# Fetch the Power Platform CLI (pac) and the .NET runtime it needs from NuGet into ~/.cache/mantis-pac.
# (The usual .NET installer site isn't reachable from Claude's cloud sessions; NuGet is.)
# Prints the two exports build.sh needs.
set -euo pipefail
PAC_VER=2.14.1
NET_VER=10.0.13
C="${MANTIS_PAC_CACHE:-$HOME/.cache/mantis-pac}"
mkdir -p "$C/dl"
get() { # id version
  local f="$C/dl/$1.$2.nupkg"
  [ -s "$f" ] || curl -sSL --fail -o "$f" "https://api.nuget.org/v3-flatcontainer/$1/$2/$1.$2.nupkg"
  rm -rf "$C/dl/$1" && mkdir -p "$C/dl/$1" && unzip -q -o "$f" -d "$C/dl/$1"
}
if [ ! -x "$C/pac/pac" ]; then
  get microsoft.powerapps.cli.core.linux-x64 "$PAC_VER"
  rm -rf "$C/pac" && cp -r "$C/dl/microsoft.powerapps.cli.core.linux-x64/tools" "$C/pac" && chmod +x "$C/pac/pac"
fi
R="$C/dotnet"
if [ ! -d "$R/shared/Microsoft.NETCore.App/$NET_VER" ]; then
  get microsoft.netcore.app.runtime.linux-x64 "$NET_VER"
  get microsoft.aspnetcore.app.runtime.linux-x64 "$NET_VER"
  N="$C/dl/microsoft.netcore.app.runtime.linux-x64/runtimes/linux-x64"
  mkdir -p "$R/host/fxr/$NET_VER" "$R/shared/Microsoft.NETCore.App/$NET_VER" "$R/shared/Microsoft.AspNetCore.App/$NET_VER"
  cp "$N/native/libhostfxr.so" "$R/host/fxr/$NET_VER/"
  cp "$N"/lib/net10.0/* "$N"/native/* "$R/shared/Microsoft.NETCore.App/$NET_VER/"
  cp "$C"/dl/microsoft.aspnetcore.app.runtime.linux-x64/runtimes/linux-x64/lib/net10.0/* "$R/shared/Microsoft.AspNetCore.App/$NET_VER/"
fi
rm -rf "$C/dl"/*/   # keep the downloads, drop the unzipped copies
echo "export DOTNET_ROOT=$R PAC=$C/pac/pac"
