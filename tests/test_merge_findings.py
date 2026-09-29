import os
import tempfile
import unittest

from helpers import FIXTURES, SCRIPTS, load, run_py, valid_finding, write_tmp_json

CHAINS = os.path.join(FIXTURES, "merge", "chains")


def merge(*lists, concat=False):
    out = os.path.join(tempfile.mkdtemp(), "merged.json")
    args = ["-o", out, "--chains-dir", CHAINS] + (["--concat"] if concat else [])
    r = run_py("merge-findings.py", *args, *[write_tmp_json(l) for l in lists])
    assert r.returncode == 0, r.stderr
    return load(out)


def loc(file, a, b):
    return [{"file": file, "line_start": a, "line_end": b}]


class MergeFindingsTest(unittest.TestCase):
    def test_dedup_keeps_more_severe(self):
        hi = valid_finding(id="SOL-001", severity="High", locations=loc("src/V.sol", 10, 20))
        med = valid_finding(id="SOL-009", severity="Medium", locations=loc("src/V.sol", 15, 16),
                            root_cause="  Missing ACCESS control on sweep ")
        out = merge([med], [hi])
        self.assertEqual([f["id"] for f in out], ["SOL-001"])
        self.assertEqual(out[0]["merged_from"], ["SOL-009"])

    def test_different_root_cause_not_merged(self):
        a = valid_finding(id="A", locations=loc("src/V.sol", 1, 5))
        b = valid_finding(id="B", locations=loc("src/V.sol", 1, 5), root_cause="rounding")
        self.assertEqual(len(merge([a, b])), 2)

    def test_killed_dropped_and_ranking(self):
        low = valid_finding(id="L", severity="Low", locations=loc("a.sol", 1, 1), root_cause="x")
        crit = valid_finding(id="C", severity="Critical", locations=loc("b.sol", 1, 1), root_cause="y")
        dead = valid_finding(id="K", status="killed", locations=loc("c.sol", 1, 1), root_cause="z")
        self.assertEqual([f["id"] for f in merge([low, dead, crit])], ["C", "L"])

    def test_boundary_tag(self):
        f = valid_finding(id="X", locations=loc("evm/Bridge.sol", 1, 2) + loc("starknet/src/bridge.cairo", 3, 4))
        self.assertTrue(merge([f])[0]["boundary"])
        self.assertNotIn("boundary", merge([valid_finding()])[0])

    def test_concat(self):
        a, b = valid_finding(id="A"), valid_finding(id="B", status="killed")
        self.assertEqual([f["id"] for f in merge([a], [b], concat=True)], ["A", "B"])


class MergeInputErrorsTest(unittest.TestCase):
    def run_merge(self, *inputs):
        out = os.path.join(tempfile.mkdtemp(), "merged.json")
        r = run_py("merge-findings.py", "-o", out, "--chains-dir", CHAINS, *inputs)
        return r, out

    def assert_rejected(self, bad, needle):
        r, out = self.run_merge(write_tmp_json([valid_finding()]), bad)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(bad, r.stderr)
        self.assertIn(needle, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_missing_file(self):
        self.assert_rejected(os.path.join(tempfile.mkdtemp(), "none.json"), "cannot read")

    def test_invalid_json(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("[{")
        self.assert_rejected(path, "cannot read")

    def test_top_level_not_list(self):
        self.assert_rejected(write_tmp_json(valid_finding()), "must be a JSON list of objects")

    def test_element_not_object(self):
        self.assert_rejected(write_tmp_json([valid_finding(), "x"]), "must be a JSON list of objects")

    def test_script_is_executable(self):
        self.assertTrue(os.access(os.path.join(SCRIPTS, "merge-findings.py"), os.X_OK))


if __name__ == "__main__":
    unittest.main()
