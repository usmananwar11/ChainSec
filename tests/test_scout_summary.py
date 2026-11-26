import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

from helpers import CORE, run

SCRIPT = os.path.join(CORE, "chains", "soroban", "recon", "scout-summary.py")
RUN_SCOUT = os.path.join(CORE, "chains", "soroban", "recon", "run-scout.sh")

# Fake cargo: FAKE_SARIF=valid|bad|none decides what scout-audit writes to --output-path;
# FAKE_EXIT is its exit code; FAKE_SLEEP makes it hang after touching Cargo.lock.
FAKE_CARGO = """#!/usr/bin/env bash
case "$1" in
  locate-project) echo "$FAKE_ROOT/Cargo.toml"; exit 0 ;;
  scout-audit)
    echo "fake scout $*"
    echo "CARGO_TARGET_DIR=$CARGO_TARGET_DIR"
    echo "changed" >> "$FAKE_ROOT/Cargo.lock"
    out=""; prev=""
    for a in "$@"; do [ "$prev" = "--output-path" ] && out="$a"; prev="$a"; done
    case "$FAKE_SARIF" in
      valid) echo '{"version": "2.1.0", "runs": [{"results": []}]}' > "$out" ;;
      bad) echo 'partial {' > "$out" ;;
    esac
    [ -n "$FAKE_SLEEP" ] && { touch "$FAKE_ROOT/started"; sleep "$FAKE_SLEEP"; }
    exit "${FAKE_EXIT:-0}" ;;
esac
exit 64
"""


def sarif(*results):
    return {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "scout"}}, "results": list(results)}]}


def result(rule, uri, line, text, level="warning"):
    return {"ruleId": rule, "level": level, "message": {"text": text},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": line}}}]}


def summarize(content):
    d = tempfile.mkdtemp()
    src, out = os.path.join(d, "scout.json"), os.path.join(d, "scout.md")
    with open(src, "w") as f:
        f.write(content if isinstance(content, str) else json.dumps(content))
    r = run([sys.executable, SCRIPT, src, out])
    return r, (open(out).read() if r.returncode == 0 else "")


class ScoutSummaryTest(unittest.TestCase):
    def test_table(self):
        r, md = summarize(sarif(result("unsafe-unwrap", "src/lib.rs", 12, "Unsafe usage of `unwrap`\nmore"),
                                result("unprotected-update-current-contract-wasm", "src/lib.rs", 40,
                                       "a | b", level="error")))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Results: 2 from 2 detectors", md)
        self.assertIn("| UNSAFE-UNWRAP | quality | unsafe-unwrap | warning | src/lib.rs:12 | Unsafe usage of `unwrap` |",
                      md)
        self.assertIn("a \\| b", md)
        self.assertNotIn("more", md)

    def test_rule_ids_map_to_patterns_and_tiers(self):
        r, md = summarize(sarif(result("unsafe_unwrap", "src/a.rs", 1, "u"),
                                result("ZERO_ADDRESS", "src/a.rs", 2, "z"),
                                result("scout::set_contract_storage", "src/a.rs", 3, "s"),
                                result("unexpected_revert_warn", "src/a.rs", 4, "v"),
                                result("integer_overflow_underflow", "src/a.rs", 5, "i"),
                                result("iterator_over_indexing", "src/a.rs", 6, "t"),
                                result("brand-new-detector", "src/a.rs", 7, "n")))
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [line for line in md.splitlines() if line.startswith("| ") and "src/a.rs" in line]
        cells = [[c.strip() for c in line.strip("|").split(" | ")] for line in rows]
        got = {c[2]: (c[0], c[1]) for c in cells}
        self.assertEqual(got, {
            "unsafe_unwrap": ("UNSAFE-UNWRAP", "quality"),
            "ZERO_ADDRESS": ("ZERO-ADDRESS", "security"),
            "scout::set_contract_storage": ("SET-CONTRACT-STORAGE", "security"),
            "unexpected_revert_warn": ("DOS-UNEXPECTED-REVERT-WITH-VECTOR", "security"),
            "integer_overflow_underflow": ("INTEGER-OVERFLOW-OR-UNDERFLOW", "security"),
            "iterator_over_indexing": ("ITERATORS-OVER-INDEXING", "quality"),
            "brand-new-detector": ("BRAND-NEW-DETECTOR", "unknown")})
        tiers = [c[1] for c in cells]
        self.assertEqual(tiers, sorted(tiers, key=["security", "unknown", "quality"].index))

    def test_security_first_and_quality_capped(self):
        quality = [result("unsafe-unwrap", "src/q.rs", i, "q") for i in range(1, 61)]
        security = [result("divide-before-multiply", "src/s.rs", i, "s") for i in range(1, 4)]
        r, md = summarize(sarif(*(quality + security)))
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [line for line in md.splitlines() if line.startswith("| ") and ".rs:" in line]
        self.assertEqual(len(rows), 53)
        self.assertTrue(all("| security |" in row for row in rows[:3]), rows[:4])
        self.assertIn("Results: 63 from 2 detectors (3 security, 0 unknown, 60 quality)", md)
        self.assertIn("truncated: 10 more quality-tier results", md)
        self.assertNotIn("more security-tier", md)

    def test_empty_and_bad_input(self):
        r, md = summarize(sarif())
        self.assertIn("Scout reported nothing.", md)
        r, _ = summarize("not json")
        self.assertEqual(r.returncode, 1)

    def test_missing_input(self):
        r = run([sys.executable, SCRIPT, "/nonexistent/scout.json", os.path.join(tempfile.mkdtemp(), "x.md")])
        self.assertEqual(r.returncode, 1)



class RunScoutFakeCargo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = os.path.join(self.tmp, "proj")
        self.audit = os.path.join(self.tmp, "proj", ".audit", "soroban")
        self.bin = os.path.join(self.tmp, "bin")
        for d in (os.path.join(self.root, "src"), self.bin):
            os.makedirs(d)
        with open(os.path.join(self.root, "Cargo.toml"), "w") as f:
            f.write("[package]\nname='x'\n")
        cargo = os.path.join(self.bin, "cargo")
        with open(cargo, "w") as f:
            f.write(FAKE_CARGO)
        os.chmod(cargo, os.stat(cargo).st_mode | stat.S_IXUSR)
        self.out = os.path.join(self.audit, "analyzers", "scout.json")
        self.lock = os.path.join(self.root, "Cargo.lock")

    def env(self, **extra):
        return dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], FAKE_ROOT=self.root, **extra)

    def go(self, sarif="valid", code=0, lock=b"# lock\x00bytes\n"):
        if lock is not None:
            with open(self.lock, "wb") as f:
                f.write(lock)
        r = run(["bash", RUN_SCOUT, self.root, self.audit], env=self.env(FAKE_SARIF=sarif, FAKE_EXIT=str(code)))
        if lock is None:
            self.assertFalse(os.path.exists(self.lock))
        else:
            with open(self.lock, "rb") as f:
                self.assertEqual(f.read(), lock)
        self.assertEqual([n for n in os.listdir(self.audit) if n.startswith("Cargo.lock")], [])
        return r

    def test_success_keeps_sarif_and_restores_lock(self):
        r = self.go()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--output-format sarif", r.stdout)
        self.assertIn("CARGO_TARGET_DIR=" + self.audit + "/target", r.stdout)
        self.assertEqual(json.load(open(self.out))["runs"], [{"results": []}])

    def test_lock_absent_is_removed(self):
        self.assertEqual(self.go(lock=None).returncode, 0)

    def test_nonzero_exit_with_valid_sarif_keeps_it(self):
        r = self.go(code=1)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(self.out))

    def test_no_output_or_bad_output_is_failure(self):
        for sarif in ("none", "bad"):
            r = self.go(sarif=sarif, code=1)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertFalse(os.path.exists(self.out))

    def test_stale_output_is_cleared_first(self):
        os.makedirs(os.path.dirname(self.out))
        with open(self.out, "w") as f:
            f.write('{"runs": []}')
        self.assertEqual(self.go(sarif="none").returncode, 1)
        self.assertFalse(os.path.exists(self.out))

    def test_stale_backup_refused(self):
        os.makedirs(self.audit)
        for name in ("Cargo.lock.chainsec-scout-backup", "Cargo.lock.chainsec-extract-backup",
                     "Cargo.lock.chainsec-runtest-backup"):
            bak = os.path.join(self.audit, name)
            with open(bak, "w") as f:
                f.write("ORIGINAL")
            with open(self.lock, "w") as f:
                f.write("MODIFIED")
            r = run(["bash", RUN_SCOUT, self.root, self.audit], env=self.env(FAKE_SARIF="valid"))
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertNotIn("fake scout", r.stdout)
            self.assertIn(name, r.stderr)
            self.assertEqual(open(self.lock).read(), "MODIFIED")
            self.assertEqual(open(bak).read(), "ORIGINAL")
            os.remove(bak)

    def test_terminated_run_restores_lock(self):
        with open(self.lock, "w") as f:
            f.write("ORIGINAL")
        p = subprocess.Popen(["bash", RUN_SCOUT, self.root, self.audit], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=self.env(FAKE_SARIF="none", FAKE_SLEEP="30"))
        deadline = time.time() + 10
        while not os.path.exists(os.path.join(self.root, "started")) and time.time() < deadline:
            time.sleep(0.05)
        start = time.time()
        p.send_signal(signal.SIGTERM)
        p.communicate(timeout=10)
        self.assertLess(time.time() - start, 5)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(open(self.lock).read(), "ORIGINAL")
        self.assertEqual([n for n in os.listdir(self.audit) if n.startswith("Cargo.lock")], [])


if __name__ == "__main__":
    unittest.main()
