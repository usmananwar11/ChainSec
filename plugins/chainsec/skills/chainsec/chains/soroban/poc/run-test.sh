#!/usr/bin/env bash
# Safe Soroban test runner. Usage: run-test.sh <crate-dir> <test-file> <work-dir> [extra cargo test args...]
# Copies <test-file> into <crate-dir>/tests/, runs `cargo test --test <name>` with its target dir under
# <work-dir>/target, then restores the crate exactly: removes the copied test, a tests/ folder it created,
# a test_snapshots/ folder it created, and puts Cargo.lock back byte-for-byte (or removes it if it did not exist).
# Exits with cargo's exit status; exit 2 on refusal (never overwrites a user's file).
set -u
if [ $# -lt 3 ]; then echo "usage: run-test.sh <crate-dir> <test-file> <work-dir> [cargo test args...]" >&2; exit 2; fi
CRATE="$(cd "$1" 2>/dev/null && pwd)" || { echo "no such crate dir: $1" >&2; exit 2; }
TESTFILE="$2"
[ -f "$TESTFILE" ] || { echo "no such test file: $TESTFILE" >&2; exit 2; }
mkdir -p "$3" && WORK="$(cd "$3" && pwd)" || { echo "cannot use work dir: $3" >&2; exit 2; }
shift 3
NAME="$(basename "$TESTFILE")"
STEM="${NAME%.rs}"
DEST="$CRATE/tests/$NAME"
if [ -e "$DEST" ]; then echo "refusing: $DEST already exists (not overwriting user files)" >&2; exit 2; fi

HAD_TESTS=0; [ -d "$CRATE/tests" ] && HAD_TESTS=1
HAD_SNAPS=0; [ -e "$CRATE/test_snapshots" ] && HAD_SNAPS=1
WS="$(cd "$CRATE" && cargo locate-project --workspace --message-format plain 2>/dev/null)"
LOCK="$(dirname "${WS:-$CRATE/Cargo.toml}")/Cargo.lock"
BACKUP="$WORK/Cargo.lock.chainsec-runtest-backup"
# A leftover backup (either script's) means an earlier run died before restoring Cargo.lock: never overwrite it.
for B in "$BACKUP" "$WORK/Cargo.lock.chainsec-extract-backup"; do
  if [ -e "$B" ]; then
    echo "refusing: stale backup $B exists (an earlier run did not restore Cargo.lock). Restore it first: cp -p \"$B\" \"$LOCK\" && rm \"$B\"" >&2
    exit 2
  fi
done
HAD_LOCK=0
if [ -f "$LOCK" ]; then
  if cp -p "$LOCK" "$BACKUP"; then HAD_LOCK=1; else echo "cannot back up Cargo.lock; not running" >&2; exit 2; fi
fi

COPIED=0
cleanup() {
  rc=$?
  [ "$COPIED" = 1 ] && rm -f "$DEST"
  [ "$HAD_TESTS" = 0 ] && rmdir "$CRATE/tests" 2>/dev/null
  [ "$HAD_SNAPS" = 0 ] && rm -rf "$CRATE/test_snapshots"
  if [ "$HAD_LOCK" = 1 ]; then
    cp -p "$BACKUP" "$LOCK" && rm -f "$BACKUP" || { echo "FAILED to restore Cargo.lock; original kept at $BACKUP" >&2; [ "$rc" = 0 ] && rc=2; }
  else rm -f "$LOCK"; fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

COPIED=1
mkdir -p "$CRATE/tests" && cp "$TESTFILE" "$DEST" || { echo "cannot copy test into $CRATE/tests" >&2; exit 2; }
cd "$CRATE" && CARGO_TARGET_DIR="$WORK/target" cargo test --test "$STEM" "$@"
