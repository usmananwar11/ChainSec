import json
import os
import sys
import tempfile
import unittest

from helpers import REPO, run

TOOL = os.path.join(REPO, "tools", "score_benchmark.py")


def entry(i, total, exact, partial=0, fp=0, tool="chainsec"):
    return {"id": i, "tool": tool, "official_total": total, "exact": exact, "partial": partial, "fp": fp}


def results_dir(*entries):
    d = tempfile.mkdtemp()
    for e in entries:
        with open(os.path.join(d, e["id"] + ".json"), "w") as f:
            json.dump(e, f)
    return d


def baseline(*entries):
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(list(entries), f)
    return p


class ScoreBenchmarkTest(unittest.TestCase):
    def test_uniform_partial_credit(self):
        d = results_dir(entry("arcade", 8, 2, partial=1))
        r = run([sys.executable, TOOL, "score", os.path.join(d, "arcade.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("recall 31.25", r.stdout)
        self.assertIn("precision 100.00", r.stdout)

    def test_compare_pass(self):
        base = baseline(entry("a", 10, 2, tool="krait"), entry("b", 10, 1, tool="krait"))
        d = results_dir(entry("a", 10, 1), entry("b", 10, 2))
        r = run([sys.executable, TOOL, "compare", base, d])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS", r.stdout)

    def test_compare_fail_on_new_fp(self):
        base = baseline(entry("a", 10, 2, tool="krait"))
        d = results_dir(entry("a", 10, 3, fp=1))
        r = run([sys.executable, TOOL, "compare", base, d])
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)

    def test_compare_fail_on_recall(self):
        base = baseline(entry("a", 10, 3, tool="krait"))
        d = results_dir(entry("a", 10, 2))
        self.assertEqual(run([sys.executable, TOOL, "compare", base, d]).returncode, 1)

    def test_shipped_baseline_aggregate(self):
        base = os.path.join(REPO, "benchmarks", "solidity", "baselines", "krait-v8.json")
        r = run([sys.executable, TOOL, "score", base])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("aggregate recall 17.42", r.stdout)


if __name__ == "__main__":
    unittest.main()
