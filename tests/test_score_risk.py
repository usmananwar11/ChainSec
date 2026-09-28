import unittest

from helpers import load, run_py, write_tmp_json

PACK = {"risk_weights": {"external_calls": 5, "state_writers": 4}, "loc_weight": 0.05,
        "novelty_bonus": 15, "value_bonus": 10, "novelty_allowlist": ["lib/**"]}


def facts(counters, units=(), value_files=()):
    return {"chain": "solidity", "mode": "regex", "units": list(units), "entry_points": [], "auth_sites": [],
            "storage_writes": [], "external_calls": [],
            "value_transfers": [{"unit": "U", "function": "f", "file": f, "line": 1, "asset": "token"} for f in value_files],
            "counters": counters}


def score(f, pack=PACK):
    r = run_py("score-risk.py", write_tmp_json(f), write_tmp_json(pack))
    assert r.returncode == 0, r.stderr
    import json
    return json.loads(r.stdout)


class ScoreRiskTest(unittest.TestCase):
    def test_hand_computed_scores(self):
        out = score(facts({"src/A.sol": {"loc": 100, "external_calls": 2, "state_writers": 3},
                           "lib/B.sol": {"loc": 40, "external_calls": 0, "state_writers": 1}},
                          value_files=["src/A.sol"]))
        by = {r["file"]: r for r in out["files"]}
        self.assertEqual(by["src/A.sol"]["score"], 52.0)   # 10 + 12 + 5 + 15 + 10
        self.assertEqual(by["lib/B.sol"]["score"], 6.0)    # 0 + 4 + 2 + 0 + 0
        self.assertEqual([r["file"] for r in out["files"]], ["src/A.sol", "lib/B.sol"])
        self.assertEqual(out["size"], "SMALL")
        self.assertEqual({r["tier"] for r in out["files"]}, {"DEEP"})

    def test_tiers_and_parent_promotion(self):
        counters = {f"src/F{i:02d}.sol": {"loc": i * 100} for i in range(20)}
        units = [{"name": "Child", "file": "src/F19.sol", "loc": 1, "parents": ["Base"]},
                 {"name": "Base", "file": "src/F00.sol", "loc": 1, "parents": []}]
        out = score(facts(counters, units), {**PACK, "novelty_bonus": 0})
        tiers = [r["tier"] for r in out["files"]]
        self.assertEqual(tiers[:5], ["DEEP"] * 5)
        self.assertEqual(tiers[5:15], ["STANDARD"] * 10)
        self.assertEqual(tiers[15:19], ["SCAN"] * 4)
        last = out["files"][-1]
        self.assertEqual((last["file"], last["tier"], last.get("promoted")), ("src/F00.sol", "STANDARD", True))
        self.assertEqual(out["size"], "MEDIUM")

    def test_output_file(self):
        import os, tempfile
        dest = os.path.join(tempfile.mkdtemp(), "risk.json")
        r = run_py("score-risk.py", write_tmp_json(facts({"a.sol": {"loc": 1}})), write_tmp_json(PACK), "-o", dest)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(load(dest)["files"][0]["file"], "a.sol")


if __name__ == "__main__":
    unittest.main()
