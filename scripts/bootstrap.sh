#!/usr/bin/env bash
# Reconstitute external/ vendored deps from external/VENDOR.md
# Idempotent — safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL="$REPO_ROOT/external"
VENDOR_MD="$EXTERNAL/VENDOR.md"

if [ ! -f "$VENDOR_MD" ]; then
  echo "ERROR: $VENDOR_MD not found" >&2
  exit 1
fi

mkdir -p "$EXTERNAL"

clone_pinned() {
  local name="$1" url="$2" sha="$3"
  local dest="$EXTERNAL/$name"
  if [ -d "$dest/.git" ]; then
    local cur
    cur=$(git -C "$dest" rev-parse HEAD)
    if [ "$cur" = "$sha" ]; then
      echo "✓ $name @ $sha"
      return 0
    fi
    echo "→ $name updating from $cur to $sha"
    git -C "$dest" fetch --depth=1 origin "$sha" 2>/dev/null || git -C "$dest" fetch origin
    git -C "$dest" checkout "$sha"
  else
    echo "→ $name cloning $url @ $sha"
    git clone --depth=1 "$url" "$dest"
    git -C "$dest" fetch --depth=1 origin "$sha" 2>/dev/null || git -C "$dest" fetch origin
    git -C "$dest" checkout "$sha"
  fi
  echo "✓ $name @ $sha"
}

# Sources of truth. Update SHAs in external/VENDOR.md, then update here, then re-run.
clone_pinned theopenlane-core       https://github.com/theopenlane/core.git                                 a76ccb5c35955ed8cb364a7aab65cec9808b854a
clone_pinned orekit                 https://github.com/CS-SI/Orekit.git                                     fb3a845cd8ef453413bda2a6ad41d281a8b9a760
clone_pinned ostk                   https://github.com/open-space-collective/open-space-toolkit.git         1eaf348fbcd9bc9265aaa47398dfe0ef51709fda
clone_pinned openmct                https://github.com/nasa/openmct.git                                     3aaa0f05e9cc294412ac0557aef5fb82737e7c7e
clone_pinned lightrag               https://github.com/HKUDS/LightRAG.git                                   405525a5e5b2c7d4385a0a3d4726accd285f9934
clone_pinned trustgraph             https://github.com/trustgraph-ai/trustgraph.git                         159b1e282406810b4a10e109d444b5ac85941b96
clone_pinned compliance-nlp         https://github.com/bettyguo/ComplianceNLP.git                           8a85f38aef6720eeeb7e25ba97b91f5e55f3ca3b
clone_pinned accord-nlp             https://github.com/Accord-Project/accord-nlp.git                        f1bc23101b5eec36926732728f05ba1e3001de15
clone_pinned itu-compliance-monitor https://github.com/ThomasGRoberts/ITU-Compliance-Assessment-Monitor.git d8bf1b441f49265482b5b48d6131123d68574f11
clone_pinned jeffallan-skills       https://github.com/Jeffallan/claude-skills.git                          5e8b6b8ff4007414f91f980771047b6136600c34

# Refresh cherry-picked Jeffallan skills into .claude/skills/
for s in rag-architect prompt-engineer postgres-pro database-optimizer mcp-developer fastapi-expert nextjs-developer kubernetes-specialist; do
  rm -rf "$REPO_ROOT/.claude/skills/$s"
  cp -r "$EXTERNAL/jeffallan-skills/skills/$s" "$REPO_ROOT/.claude/skills/$s"
done

echo ""
echo "Bootstrap complete. External vendored deps:"
du -sh "$EXTERNAL"/*/ 2>/dev/null
