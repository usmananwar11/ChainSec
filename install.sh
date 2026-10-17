#!/usr/bin/env bash
# Install ChainSec skills for tools that load Agent Skills from folders.
# Usage: install.sh [--tool agents|claude|opencode|antigravity] [--global] [--link] [--dest DIR]
#   agents      -> .agents/skills           (Codex, OpenCode, Cursor, Gemini CLI, Antigravity)
#   claude      -> .claude/skills           (Claude Code without the plugin; also read by OpenCode/Cursor)
#   opencode    -> .opencode/skills
#   antigravity -> .agents/skills  (--global: ~/.gemini/config/skills)
# --global installs under your home folder; --link symlinks instead of copying.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/plugins/chainsec/skills"
TOOL=agents
GLOBAL=0
LINK=0
DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --tool) TOOL="$2"; shift 2 ;;
    --global) GLOBAL=1; shift ;;
    --link) LINK=1; shift ;;
    --dest) DEST="$2"; shift 2 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
if [ -z "$DEST" ]; then
  case "$TOOL:$GLOBAL" in
    agents:0|antigravity:0) DEST=".agents/skills" ;;
    agents:1) DEST="$HOME/.agents/skills" ;;
    claude:0) DEST=".claude/skills" ;;
    claude:1) DEST="$HOME/.claude/skills" ;;
    opencode:0) DEST=".opencode/skills" ;;
    opencode:1) DEST="$HOME/.config/opencode/skills" ;;
    antigravity:1) DEST="$HOME/.gemini/config/skills" ;;
    *) echo "unknown tool: $TOOL" >&2; exit 2 ;;
  esac
fi
# Resolve existing symlinks and nonexistent descendants before creating or deleting anything.
python3 - "$SRC" "$DEST" <<'PYGUARD' || exit 2
import os
import sys

source, destination = map(os.path.realpath, sys.argv[1:])
if os.path.commonpath([source, destination]) == source:
    sys.exit("refusing to install: destination is inside ChainSec's source folder")
# An ancestor destination can also erase the source through a same-named target.
for name in os.listdir(source):
    target = os.path.join(destination, name)
    # rm -rf removes a target symlink itself, not the directory it points to.
    if not os.path.islink(target) and os.path.commonpath([source, target]) == target:
        sys.exit("refusing to install: an install target contains ChainSec's source folder")
PYGUARD
mkdir -p "$DEST"
for skill in "$SRC"/*/; do
  name="$(basename "$skill")"
  target="$DEST/$name"
  if [ -e "$target" ] || [ -L "$target" ]; then rm -rf "$target"; fi
  if [ "$LINK" = 1 ]; then ln -s "${skill%/}" "$target"; else cp -R "${skill%/}" "$target"; fi
  echo "installed $name -> $target"
done
echo "Done. ChainSec skills must stay together in one folder (entry skills use ../chainsec)."
