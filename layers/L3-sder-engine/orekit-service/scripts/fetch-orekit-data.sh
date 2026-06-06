#!/usr/bin/env bash
# Fetch the Orekit data set (EOP, leap seconds, gravity models) that the service
# needs to propagate. Per ADR-0013 the data is mounted at runtime, never baked
# into the image. Run this once before `docker compose --profile sder up`.
#
# Usage: ./fetch-orekit-data.sh [TARGET_DIR]
#   TARGET_DIR defaults to ../../../../cross-cutting/deploy/orekit-data
#   (the directory docker-compose mounts read-only at /orekit-data).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TARGET="$SCRIPT_DIR/../../../../cross-cutting/deploy/orekit-data"
TARGET_DIR="${1:-$DEFAULT_TARGET}"

# Canonical Orekit physical-data repository (GitLab, CS GROUP / FR — ADR-0002).
# Pin to the maintained master archive; revisit vendoring a frozen snapshot for
# fully reproducible regulator-facing runs in Phase 4 (CONTRACT.md open question).
DATA_URL="https://gitlab.orekit.org/orekit/orekit-data/-/archive/master/orekit-data-master.zip"

echo "Fetching orekit-data -> $TARGET_DIR"
mkdir -p "$TARGET_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL "$DATA_URL" -o "$TMP_DIR/orekit-data.zip"
unzip -q "$TMP_DIR/orekit-data.zip" -d "$TMP_DIR"

# The archive expands to orekit-data-master/<files>; flatten into TARGET_DIR.
SRC_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d -name 'orekit-data*' | head -1)"
if [ -z "$SRC_DIR" ]; then
  echo "ERROR: unexpected archive layout; no orekit-data* directory found" >&2
  exit 1
fi
cp -R "$SRC_DIR"/. "$TARGET_DIR"/

FILE_COUNT="$(find "$TARGET_DIR" -type f | wc -l | tr -d ' ')"
echo "Done: $FILE_COUNT files in $TARGET_DIR"
echo "Now run: docker compose --profile sder up -d orekit  (from cross-cutting/deploy)"
