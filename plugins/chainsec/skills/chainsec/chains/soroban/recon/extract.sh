#!/usr/bin/env bash
# Soroban facts extractor. Usage: extract.sh <project-root> <facts.json>
# Runs `cargo check` with its target dir next to facts.json (the project's own target/ is not
# touched, and Cargo.lock is restored byte-for-byte, or removed if it did not exist) to record compile status, then
# parses source. Env: CHAINSEC_NO_COMPILE=1 skips the check; CHAINSEC_PACK overrides the manifest.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${1:-.}" 2>/dev/null && pwd)" || { echo "no such root: ${1:-.}" >&2; exit 2; }
OUT="${2:-$ROOT/.audit/soroban/facts.json}"
PACK="${CHAINSEC_PACK:-$HERE/../pack.json}"
mkdir -p "$(dirname "$OUT")"
OUTDIR="$(cd "$(dirname "$OUT")" && pwd)"
STATUS=unknown
if [ "${CHAINSEC_NO_COMPILE:-0}" != "1" ] && command -v cargo >/dev/null 2>&1 && [ -f "$ROOT/Cargo.toml" ]; then
  WS="$(cd "$ROOT" && cargo locate-project --workspace --message-format plain 2>/dev/null)"
  LOCK="$(dirname "${WS:-$ROOT/Cargo.toml}")/Cargo.lock"
  BACKUP="$OUTDIR/Cargo.lock.chainsec-backup"
  HAD_LOCK=0
  restore_lock() {
    if [ "$HAD_LOCK" = 1 ]; then cp -p "$BACKUP" "$LOCK" && rm -f "$BACKUP"; else rm -f "$LOCK"; fi
  }
  SAFE=1
  if [ -f "$LOCK" ]; then
    if cp -p "$LOCK" "$BACKUP"; then HAD_LOCK=1; else SAFE=0; echo "cannot back up Cargo.lock; skipping cargo check" >&2; fi
  fi
  if [ "$SAFE" = 1 ]; then
    trap restore_lock EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    if (cd "$ROOT" && CARGO_TARGET_DIR="$OUTDIR/target" cargo check --quiet >/dev/null 2>&1); then
      STATUS=ok
    else
      STATUS=failed
      echo "cargo check failed; facts come from source only" >&2
    fi
  fi
  if [ "$SAFE" = 1 ]; then restore_lock; trap - EXIT INT TERM; fi
fi
python3 "$HERE/extract.py" --root "$ROOT" --pack "$PACK" --out "$OUT" --compile "$STATUS"
