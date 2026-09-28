import json
import os
import unittest

from helpers import FIXTURES, run_py

D = os.path.join(FIXTURES, "detect")


def detect(name):
    r = run_py("detect-chain.py", os.path.join(D, name), "--chains-dir", os.path.join(D, "chains"))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["chains"]


class DetectChainTest(unittest.TestCase):
    def test_solidity_only_ignores_lib(self):
        self.assertEqual(detect("sol-only"), [{"chain": "solidity", "root": "."}])

    def test_mixed_repo(self):
        self.assertEqual(detect("mixed"), [{"chain": "cairo", "root": "starknet"},
                                           {"chain": "solidity", "root": "evm"}])

    def test_fallback_glob(self):
        self.assertEqual(detect("fallback"), [{"chain": "solidity", "root": "."}])

    def test_nothing(self):
        self.assertEqual(detect("none"), [])

    def test_real_solidity_pack_detects_fixture(self):
        from helpers import FIXTURES as F
        r = run_py("detect-chain.py", os.path.join(F, "solidity-basic"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["chains"], [{"chain": "solidity", "root": "."}])


if __name__ == "__main__":
    unittest.main()
