#!/usr/bin/env bash
# Soroban facts extractor. Usage: extract.sh <project-root> <facts.json>
# Runs `cargo check` with its target dir next to facts.json (the project's own target/ is not
# touched, and Cargo.lock is restored byte-for-byte, or removed if it did not exist) to record compile status
# (ok, failed, timeout or unknown), then always parses source. Env: CHAINSEC_NO_COMPILE=1 skips the check;
# CHAINSEC_COMPILE_TIMEOUT (seconds, default 100) bounds it; CHAINSEC_PACK overrides the manifest.
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
  BACKUP="$OUTDIR/Cargo.lock.chainsec-extract-backup"
  HAD_LOCK=0
  PID=""
  stop_check() {
    if [ -n "$PID" ]; then kill -TERM -- "-$PID" 2>/dev/null || kill "$PID" 2>/dev/null; wait "$PID" 2>/dev/null; PID=""; fi
  }
  restore_lock() {
    stop_check
    if [ "$HAD_LOCK" = 1 ]; then
      cp -p "$BACKUP" "$LOCK" && rm -f "$BACKUP" || echo "FAILED to restore Cargo.lock; original kept at $BACKUP" >&2
    else rm -f "$LOCK"; fi
  }
  SAFE=1
  # Any ChainSec script's leftover backup (extract, runtest, scout) means an earlier run did not restore the lock.
  for B in "$OUTDIR"/Cargo.lock.chainsec-*-backup; do
    if [ -e "$B" ]; then
      SAFE=0
      echo "stale backup $B exists (an earlier run did not restore Cargo.lock); skipping cargo check. Restore it first: cp -p \"$B\" \"$LOCK\" && rm \"$B\"" >&2
    fi
  done
  if [ "$SAFE" = 1 ] && [ -f "$LOCK" ]; then
    if cp -p "$LOCK" "$BACKUP"; then HAD_LOCK=1; else SAFE=0; echo "cannot back up Cargo.lock; skipping cargo check" >&2; fi
  fi
  if [ "$SAFE" = 1 ]; then
    trap restore_lock EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    LIMIT="${CHAINSEC_COMPILE_TIMEOUT:-100}"
    case "$LIMIT" in ''|*[!0-9]*) LIMIT=100 ;; esac
    # Background job in its own process group (set -m) so the time limit and INT/TERM can stop cargo and its
    # rustc children; macOS has no `timeout`, so poll.
    set -m
    (cd "$ROOT" && CARGO_TARGET_DIR="$OUTDIR/target" exec cargo check --quiet >/dev/null 2>&1) &
    PID=$!
    set +m
    WAITED=0
    while kill -0 "$PID" 2>/dev/null && [ "$WAITED" -lt "$LIMIT" ]; do sleep 1; WAITED=$((WAITED + 1)); done
    if kill -0 "$PID" 2>/dev/null; then
      stop_check
      STATUS=timeout
      echo "cargo check did not finish in ${LIMIT}s; facts come from source only (raise CHAINSEC_COMPILE_TIMEOUT to wait longer)" >&2
    elif wait "$PID"; then
      PID=""; STATUS=ok
    else
      PID=""; STATUS=failed
      echo "cargo check failed; facts come from source only" >&2
    fi
  fi
  if [ "$SAFE" = 1 ]; then restore_lock; trap - EXIT INT TERM; fi
fi
python3 "$HERE/extract.py" --root "$ROOT" --pack "$PACK" --out "$OUT" --compile "$STATUS"
