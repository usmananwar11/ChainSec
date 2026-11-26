import os
import shutil
import stat
import tempfile
import unittest

from helpers import CORE, FIXTURES, run

RUN_TEST = os.path.join(CORE, "chains", "soroban", "poc", "run-test.sh")
FIXTURE = os.path.join(FIXTURES, "soroban-basic")
SLOW = os.environ.get("CHAINSEC_SLOW_TESTS") == "1"

FAKE_CARGO = """#!/usr/bin/env bash
case "$1" in
  locate-project) echo "$FAKE_CRATE/Cargo.toml"; exit 0 ;;
  test)
    echo "fake cargo test $*"
    echo "CARGO_TARGET_DIR=$CARGO_TARGET_DIR"
    ls "$FAKE_CRATE/tests/" | sed 's/^/COPIED:/'
    [ -n "$FAKE_RO_LOCK" ] && { echo x >> "$FAKE_CRATE/Cargo.lock"; chmod 444 "$FAKE_CRATE/Cargo.lock"; }
    echo "changed" >> "$FAKE_CRATE/Cargo.lock"
    mkdir -p "$FAKE_CRATE/test_snapshots"; echo '{}' > "$FAKE_CRATE/test_snapshots/x.json"
    ls "$FAKE_CRATE/tests" > /dev/null || exit 99
    exit "${FAKE_EXIT:-0}" ;;
esac
exit 64
"""


def snapshot(root):
    out = {}
    for d, _, files in os.walk(root):
        out[os.path.relpath(d, root) + "/"] = None
        for f in files:
            with open(os.path.join(d, f), "rb") as fh:
                out[os.path.relpath(os.path.join(d, f), root)] = fh.read()
    return out


class RunTestFakeCargo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.crate = os.path.join(self.tmp, "crate")
        self.work = os.path.join(self.tmp, "work")
        self.bin = os.path.join(self.tmp, "bin")
        for d in (os.path.join(self.crate, "src"), self.work, self.bin):
            os.makedirs(d)
        with open(os.path.join(self.crate, "Cargo.toml"), "w") as f:
            f.write("[package]\nname='x'\n")
        with open(os.path.join(self.crate, "src", "lib.rs"), "w") as f:
            f.write("// lib\n")
        self.testfile = os.path.join(self.tmp, "chainsec_poc_x_001.rs")
        with open(self.testfile, "w") as f:
            f.write("// poc\n")
        cargo = os.path.join(self.bin, "cargo")
        with open(cargo, "w") as f:
            f.write(FAKE_CARGO)
        os.chmod(cargo, os.stat(cargo).st_mode | stat.S_IXUSR)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def go(self, code=0, **extra):
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"],
                   FAKE_CRATE=self.crate, FAKE_EXIT=str(code), **extra)
        return run(["bash", RUN_TEST, self.crate, self.testfile, self.work, "--", "--nocapture"], env=env)

    def check(self, code=0, lock=None, tests_dir=False):
        lockp = os.path.join(self.crate, "Cargo.lock")
        if lock is not None:
            with open(lockp, "wb") as f:
                f.write(lock)
        if tests_dir:
            os.makedirs(os.path.join(self.crate, "tests"))
        before_crate, before_work = snapshot(self.crate), snapshot(self.work)
        r = self.go(code)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        self.assertIn("fake cargo test", r.stdout)
        self.assertIn("--test chainsec_poc_x_001", r.stdout)
        self.assertIn("--nocapture", r.stdout)
        self.assertIn("COPIED:chainsec_poc_x_001.rs", r.stdout)
        self.assertIn("CARGO_TARGET_DIR=" + self.work + "/target", r.stdout)
        self.assertEqual(snapshot(self.crate), before_crate)
        self.assertEqual(snapshot(self.work), before_work)

    def test_lock_existed(self):
        self.check(lock=b"# lock\x00bytes\n")

    def test_lock_absent(self):
        self.check()

    def test_tests_dir_existed(self):
        self.check(tests_dir=True, lock=b"L")

    def test_cargo_failure_propagates(self):
        self.check(code=1)
        self.check(code=1, tests_dir=True)

    def test_existing_snapshots_dir_kept(self):
        os.makedirs(os.path.join(self.crate, "test_snapshots"))
        with open(os.path.join(self.crate, "test_snapshots", "keep.json"), "w") as f:
            f.write("keep")
        before = snapshot(self.crate)
        r = self.go()
        self.assertEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.crate, "test_snapshots", "keep.json")))
        self.assertTrue(os.path.isdir(os.path.join(self.crate, "test_snapshots")))
        self.assertEqual(snapshot(self.crate).keys() - before.keys(), {"test_snapshots/x.json"})

    def test_stale_backup_refused(self):
        for name in ("Cargo.lock.chainsec-runtest-backup", "Cargo.lock.chainsec-extract-backup",
                     "Cargo.lock.chainsec-scout-backup"):
            bak = os.path.join(self.work, name)
            with open(bak, "w") as f:
                f.write("ORIGINAL")
            with open(os.path.join(self.crate, "Cargo.lock"), "w") as f:
                f.write("MODIFIED")
            before_c, before_w = snapshot(self.crate), snapshot(self.work)
            r = self.go()
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertNotIn("fake cargo test", r.stdout)
            self.assertIn(name, r.stderr)
            self.assertEqual(snapshot(self.crate), before_c)
            self.assertEqual(snapshot(self.work), before_w)
            os.remove(bak)

    def test_backup_failure_not_run(self):
        with open(os.path.join(self.crate, "Cargo.lock"), "w") as f:
            f.write("L")
        os.chmod(self.work, 0o555)
        self.addCleanup(os.chmod, self.work, 0o755)
        before = snapshot(self.crate)
        r = self.go()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("fake cargo test", r.stdout)
        self.assertEqual(snapshot(self.crate), before)

    def test_restore_failure_is_nonzero(self):
        with open(os.path.join(self.crate, "Cargo.lock"), "w") as f:
            f.write("L")
        self.addCleanup(lambda: os.chmod(os.path.join(self.crate, "Cargo.lock"), 0o644))
        r = self.go(FAKE_RO_LOCK="1")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("FAILED to restore", r.stderr)
        os.remove(os.path.join(self.work, "Cargo.lock.chainsec-runtest-backup"))
        os.chmod(os.path.join(self.crate, "Cargo.lock"), 0o644)
        r = self.go(1, FAKE_RO_LOCK="1")
        self.assertEqual(r.returncode, 1)

    def test_existing_test_file_refused(self):
        os.makedirs(os.path.join(self.crate, "tests"))
        mine = os.path.join(self.crate, "tests", "chainsec_poc_x_001.rs")
        with open(mine, "w") as f:
            f.write("user file")
        with open(os.path.join(self.crate, "Cargo.lock"), "w") as f:
            f.write("L")
        before = snapshot(self.crate)
        r = self.go()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("fake cargo test", r.stdout)
        self.assertEqual(snapshot(self.crate), before)


@unittest.skipUnless(SLOW and shutil.which("cargo"), "set CHAINSEC_SLOW_TESTS=1 with cargo installed")
class RunTestRealCargo(unittest.TestCase):
    def test_poc_on_fixture_copy(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        crate = os.path.join(tmp, "soroban-basic")
        shutil.copytree(FIXTURE, crate)
        with open(os.path.join(CORE, "chains", "soroban", "poc", "guide.md"), encoding="utf-8") as gf:
            guide = gf.read()
        start = guide.index("```rust\n", guide.index("<!-- chainsec:verified-poc-skeleton -->")) + len("```rust\n")
        src = guide[start:guide.index("```", start)]
        work = os.path.join(tmp, "audit")
        poc = os.path.join(work, "poc", "SOROBAN-001")
        os.makedirs(poc)
        tf = os.path.join(poc, "chainsec_poc_soroban_001.rs")
        with open(tf, "w") as f:
            f.write(src)
        before = snapshot(crate)
        r = run(["bash", RUN_TEST, crate, tf, work])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("chainsec_poc_soroban_001_withdraw_without_auth ... ok", r.stdout + r.stderr)
        self.assertEqual(snapshot(crate), before)

    def test_fuzz_harness_on_fixture_copies(self):
        with open(os.path.join(CORE, "chains", "soroban", "fuzz", "guide.md"), encoding="utf-8") as gf:
            guide = gf.read()
        start = guide.index("```rust\n", guide.index("<!-- chainsec:verified-fuzz-harness -->")) + len("```rust\n")
        src = guide[start:guide.index("```", start)]

        def go(fixed):
            tmp = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
            crate = os.path.join(tmp, "soroban-basic")
            shutil.copytree(FIXTURE, crate)
            if fixed:
                lib = os.path.join(crate, "src", "lib.rs")
                with open(lib, encoding="utf-8") as f:
                    code = f.read()
                sig = "pub fn withdraw(env: Env, from: Address, to: Address, amount: i128) {\n"
                self.assertIn(sig, code)
                with open(lib, "w", encoding="utf-8") as f:
                    f.write(code.replace(sig, sig + "        from.require_auth();\n"))
            work = os.path.join(tmp, "audit")
            tf = os.path.join(work, "fuzz", "tests", "chainsec_fuzz.rs")
            os.makedirs(os.path.dirname(tf))
            with open(tf, "w") as f:
                f.write(src)
            before = snapshot(crate)
            r = run(["bash", RUN_TEST, crate, tf, work, "--", "--nocapture"])
            self.assertEqual(snapshot(crate), before)
            return r

        r = go(False)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("INV-1 broken", r.stdout + r.stderr)
        r = go(True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("chainsec_fuzz_vault_invariants ... ok", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
