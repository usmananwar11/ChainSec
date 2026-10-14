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

    def full_entries(self):
        return [entry(i, total, 1) for i, total in {
            "pooltogether": 9, "initcapital": 15, "goodentry": 14,
            "arcade": 8, "frankencoin": 21,
        }.items()]

    def compare(self, base, results, *args):
        return run([sys.executable, TOOL, "compare", baseline(*base),
                    results_dir(*results), *args])

    def test_compare_pass(self):
        r = self.compare(self.full_entries(), self.full_entries())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS", r.stdout)
        self.assertIn("all five targets", r.stdout)

    def test_compare_fail_on_new_fp(self):
        results = self.full_entries()
        results[0]["fp"] = 1
        r = self.compare(self.full_entries(), results)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)

    def test_compare_fail_on_recall(self):
        results = self.full_entries()
        results[0]["exact"] = 0
        r = self.compare(self.full_entries(), results)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)

    def test_compare_requires_each_target_in_both_inputs(self):
        for side in ("baseline", "results"):
            for target in self.full_entries():
                with self.subTest(side=side, target=target["id"]):
                    incomplete = [e for e in self.full_entries() if e["id"] != target["id"]]
                    base, results = self.full_entries(), self.full_entries()
                    if side == "baseline":
                        base = incomplete
                    else:
                        results = incomplete
                    r = self.compare(base, results)
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(f"{side}: missing target {target['id']}", r.stdout)
                    self.assertNotIn("PASS", r.stdout)

    def test_pooltogether_alone_requires_explicit_target(self):
        results = [self.full_entries()[0]]
        r = self.compare(self.full_entries(), results)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("PASS", r.stdout)
        r = self.compare(self.full_entries(), results, "--target", "pooltogether")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not full acceptance", r.stdout)
        self.assertIn("PASS", r.stdout)

    def test_compare_rejects_duplicates(self):
        for side in ("baseline", "results"):
            with self.subTest(side=side):
                es = self.full_entries()
                base = baseline(*(es + [es[0]] if side == "baseline" else es))
                d = results_dir(*es)
                if side == "results":
                    # Duplicates must be detected across files and within lists.
                    with open(os.path.join(d, "duplicate.json"), "w") as f:
                        json.dump([es[0]], f)
                r = run([sys.executable, TOOL, "compare", base, d])
                self.assertEqual(r.returncode, 1)
                self.assertIn(f"{side}: duplicate target pooltogether", r.stdout)
                self.assertNotIn("PASS", r.stdout)

    def test_compare_rejects_incorrect_totals_even_when_inputs_agree(self):
        for target in range(5):
            for side in ("baseline", "results", "both"):
                with self.subTest(target=target, side=side):
                    base, results = self.full_entries(), self.full_entries()
                    if side in ("baseline", "both"):
                        base[target]["official_total"] -= 1
                    if side in ("results", "both"):
                        results[target]["official_total"] -= 1
                    r = self.compare(base, results)
                    self.assertEqual(r.returncode, 1)
                    self.assertIn("official_total must be", r.stdout)
                    self.assertNotIn("PASS", r.stdout)

    def test_shipped_baseline_aggregate(self):
        base = os.path.join(REPO, "benchmarks", "solidity", "baselines", "krait-v8.json")
        with open(base, encoding="utf-8") as f:
            entries = json.load(f)
        expected = {
            "pooltogether": (9, 1, 0, 0),
            "initcapital": (15, 0, 1, 0),
            "goodentry": (14, 5, 0, 0),
            "arcade": (8, 2, 1, 0),
            "frankencoin": (21, 2, 1, 0),
        }
        self.assertEqual(len(entries), len(expected))
        self.assertEqual(
            {e["id"]: (e["official_total"], e["exact"], e["partial"], e["fp"])
             for e in entries},
            expected,
        )
        self.assertEqual(sum(e["official_total"] for e in entries), 67)
        self.assertEqual(sum(e["exact"] + 0.5 * e["partial"] for e in entries), 11.5)
        r = run([sys.executable, TOOL, "score", base])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("aggregate recall 17.16 total fp 0", r.stdout)


if __name__ == "__main__":
    unittest.main()
