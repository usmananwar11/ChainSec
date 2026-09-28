#!/usr/bin/env bash
# Solidity facts extractor. Usage: extract.sh <project-root> <facts.json>
# Tries `forge build --ast` into a temp dir (compiler mode); falls back to regex mode.
# Env: CHAINSEC_NO_COMPILE=1 forces regex mode; CHAINSEC_PACK overrides the pack manifest.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${1:-.}" && pwd)"
OUT="${2:-$ROOT/.audit/solidity/facts.json}"
PACK="${CHAINSEC_PACK:-$HERE/../pack.json}"
mkdir -p "$(dirname "$OUT")"
BUILD=""
cleanup() { if [ -n "$BUILD" ]; then rm -rf "$BUILD"; fi; }
trap cleanup EXIT
set -- --root "$ROOT" --pack "$PACK" --out "$OUT"
if [ "${CHAINSEC_NO_COMPILE:-0}" != "1" ] && command -v forge >/dev/null 2>&1; then
  TOML="$(find "$ROOT" -maxdepth 2 -name foundry.toml -not -path '*/lib/*' 2>/dev/null | head -1)"
  if [ -n "$TOML" ]; then
    FDIR="$(dirname "$TOML")"
    BUILD="$(mktemp -d)"
    if (cd "$FDIR" && forge build --ast --out "$BUILD/out" --cache-path "$BUILD/cache" >/dev/null 2>&1); then
      set -- "$@" --artifacts "$BUILD/out" --foundry-dir "$FDIR"
    else
      echo "forge build failed; using regex mode" >&2
    fi
  fi
fi
python3 "$HERE/extract.py" "$@"
