#!/usr/bin/env bash
# Update a single vendored dep to its latest upstream HEAD on its tracked branch.
# Reports the new SHA — you must then update external/VENDOR.md + open an ADR.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <name> [branch]" >&2
  echo "Example: $0 theopenlane-core main" >&2
  exit 1
fi

NAME="$1"
BRANCH="${2:-main}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/external/$NAME"

if [ ! -d "$DEST/.git" ]; then
  echo "ERROR: $DEST is not a git repo. Run bootstrap.sh first." >&2
  exit 1
fi

OLD_SHA=$(git -C "$DEST" rev-parse HEAD)
echo "Current $NAME SHA: $OLD_SHA"

git -C "$DEST" fetch origin "$BRANCH"
NEW_SHA=$(git -C "$DEST" rev-parse "origin/$BRANCH")

if [ "$OLD_SHA" = "$NEW_SHA" ]; then
  echo "Up to date: $NAME @ $NEW_SHA"
  exit 0
fi

echo ""
echo "Proposed update:"
echo "  $NAME"
echo "  $OLD_SHA  →  $NEW_SHA"
echo ""
echo "Diff summary:"
git -C "$DEST" log --oneline "$OLD_SHA..$NEW_SHA" | head -30
echo ""
echo "NEXT STEPS:"
echo "  1. Open an ADR documenting why this upgrade is needed."
echo "  2. Update external/VENDOR.md: replace $OLD_SHA with $NEW_SHA"
echo "  3. Update scripts/bootstrap.sh: same."
echo "  4. Run ./scripts/bootstrap.sh"
echo "  5. Run any layer-specific integration tests."
echo "  6. Run /cso if the upgrade touches L1 or auth-adjacent code."
echo ""
echo "This script does NOT auto-checkout — review first."
