#!/usr/bin/env bash
# Build the release tarball for Asura's Wrath Recompiled.
#
#   scripts/package_release.sh [version] [pkg_dir]
#
# The package is the built, ready-to-run folder (paths.env LAUNCHER by default):
# the launcher script, the bundled engine and an empty rom_data, where the
# player's own disc gets compiled into a module on first run.
#
# Never included: the player's disc or extracted copy (disc_extracted/), the
# module compiled from it (rom_data/*.ppumod), their settings.json / recomp.cfg.
# Shipping a settings file would overwrite the player's on every update, since
# RecompLauncher unpacks releases over the game's folder.
#
# recomplauncher.json is copied in from this repo on every run, so the release
# always carries the current manifest next to the program.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-1.2.0}"
# shellcheck disable=SC1091
[ -f paths.env ] && . ./paths.env
PKG_DIR="${2:-${LAUNCHER:-}}"
if [ -z "$PKG_DIR" ] || [ ! -f "$PKG_DIR/asuraswrath" ]; then
    echo "no package folder: pass one, or set LAUNCHER in paths.env" >&2
    exit 2
fi
[ -f recomplauncher.json ] || { echo "recomplauncher.json missing from the repo root" >&2; exit 2; }

NAME="AsurasWrathRecomp-${VERSION}-Linux-x86_64"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
OUT="$STAGE/$NAME"
install -d "$OUT/engine" "$OUT/rom_data" "$OUT/mods"

for f in asuraswrath README.txt LICENSE asuraswrath.png asuraswrath.desktop install-desktop-entry.sh; do
    [ -f "$PKG_DIR/$f" ] && cp -p "$PKG_DIR/$f" "$OUT/$f"
done
cp recomplauncher.json "$OUT/recomplauncher.json"

if [ -x "$PKG_DIR/engine/rpcs3" ]; then
    cp -p "$PKG_DIR/engine/rpcs3" "$OUT/engine/rpcs3"
else
    echo "warning: no engine/rpcs3 to bundle; the release needs one" >&2
fi
[ -f "$PKG_DIR/rom_data/.keep" ] && cp -p "$PKG_DIR/rom_data/.keep" "$OUT/rom_data/.keep"

tar -C "$STAGE" -czf "$NAME.tar.gz" "$NAME"
echo "$NAME.tar.gz"
echo "sha256: $(sha256sum "$NAME.tar.gz" | cut -d' ' -f1)"
