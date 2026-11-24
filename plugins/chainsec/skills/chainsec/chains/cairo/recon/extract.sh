#!/usr/bin/env bash
# Cairo facts extractor. Usage: extract.sh <project-root> <facts.json>
# Runs `scarb build` into a temp target dir (the project tree is not touched) to record compile
# status, then parses source. Exit 3: Cairo 0 source.
# Env: CHAINSEC_NO_COMPILE=1 skips the build; CHAINSEC_PACK overrides the pack manifest.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${1:-.}" 2>/dev/null && pwd)" || { echo "no such root: ${1:-.}" >&2; exit 2; }
OUT="${2:-$ROOT/.audit/cairo/facts.json}"
PACK="${CHAINSEC_PACK:-$HERE/../pack.json}"
mkdir -p "$(dirname "$OUT")"
BUILD=""
cleanup() { if [ -n "$BUILD" ]; then rm -rf "$BUILD"; fi; }
trap cleanup EXIT
STATUS=unknown
if [ "${CHAINSEC_NO_COMPILE:-0}" != "1" ] && command -v scarb >/dev/null 2>&1 && [ -f "$ROOT/Scarb.toml" ]; then
  BUILD="$(mktemp -d)"
  if (cd "$ROOT" && SCARB_TARGET_DIR="$BUILD/target" scarb build >/dev/null 2>&1); then
    STATUS=ok
  else
    STATUS=failed
    echo "scarb build failed; facts come from source only" >&2
  fi
fi
python3 "$HERE/extract.py" --root "$ROOT" --pack "$PACK" --out "$OUT" --compile "$STATUS"
