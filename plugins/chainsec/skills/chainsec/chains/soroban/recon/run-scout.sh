#!/usr/bin/env bash
# Lock-safe Scout run for recon Step 2b. Usage: run-scout.sh <project-root> <audit-dir>
# Runs `cargo scout-audit` with SARIF output at <audit-dir>/analyzers/scout.json and its target dir under
# <audit-dir>/target (the project's own target/ is not touched). Cargo.lock is restored byte-for-byte, or
# removed if it did not exist, also when the run is interrupted (INT/TERM).
# The SARIF file is kept whenever it parses as JSON with a "runs" list, whatever Scout's exit code (Scout can
# exit non-zero when it reports findings); otherwise it is removed.
# Exit: 0 SARIF written; 1 Scout produced no usable SARIF; 2 refused (stale lock backup, no backup possible).
set -u
if [ $# -lt 2 ]; then echo "usage: run-scout.sh <project-root> <audit-dir>" >&2; exit 2; fi
ROOT="$(cd "$1" 2>/dev/null && pwd)" || { echo "no such root: $1" >&2; exit 2; }
mkdir -p "$2/analyzers" && A="$(cd "$2" && pwd)" || { echo "cannot use audit dir: $2" >&2; exit 2; }
OUT="$A/analyzers/scout.json"
rm -f "$OUT"
WS="$(cd "$ROOT" && cargo locate-project --workspace --message-format plain 2>/dev/null)"
LOCK="$(dirname "${WS:-$ROOT/Cargo.toml}")/Cargo.lock"
BACKUP="$A/Cargo.lock.chainsec-scout-backup"
# A leftover backup (any ChainSec script's) means an earlier run died before restoring Cargo.lock.
for B in "$A"/Cargo.lock.chainsec-*-backup; do
  if [ -e "$B" ]; then
    echo "refusing: stale backup $B exists (an earlier run did not restore Cargo.lock). Restore it first: cp -p \"$B\" \"$LOCK\" && rm \"$B\"" >&2
    exit 2
  fi
done
HAD_LOCK=0
if [ -f "$LOCK" ]; then
  if cp -p "$LOCK" "$BACKUP"; then HAD_LOCK=1; else echo "cannot back up Cargo.lock; not running Scout" >&2; exit 2; fi
fi

PID=""
cleanup() {
  rc=$?
  if [ -n "$PID" ]; then kill -TERM -- "-$PID" 2>/dev/null || kill "$PID" 2>/dev/null; wait "$PID" 2>/dev/null; fi
  if [ "$HAD_LOCK" = 1 ]; then
    cp -p "$BACKUP" "$LOCK" && rm -f "$BACKUP" || { echo "FAILED to restore Cargo.lock; original kept at $BACKUP" >&2; [ "$rc" = 0 ] && rc=2; }
  else rm -f "$LOCK"; fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# In the background, in its own process group (set -m), so a signal interrupts `wait` at once and cleanup can
# stop the whole build (cargo and its rustc children) before restoring the lock.
set -m
(cd "$ROOT" && CARGO_TARGET_DIR="$A/target" exec cargo scout-audit --output-format sarif --output-path "$OUT") &
PID=$!
set +m
wait "$PID"
RC=$?
PID=""
if python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); sys.exit(0 if isinstance(d, dict) and isinstance(d.get("runs"), list) else 1)' "$OUT" 2>/dev/null; then
  [ "$RC" = 0 ] || echo "scout exited $RC; keeping its SARIF output" >&2
  exit 0
fi
rm -f "$OUT"
echo "scout failed (exit $RC) and wrote no SARIF; scout pre-scan: SKIPPED (failed)" >&2
exit 1
