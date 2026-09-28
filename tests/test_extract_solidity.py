import os
import shutil
import sys
import tempfile
import unittest

from helpers import CORE, FIXTURES, SCRIPTS, load, make_tree, run

sys.path.insert(0, SCRIPTS)
from _schema import validate  # noqa: E402

EXTRACT = os.path.join(CORE, "chains", "solidity", "recon", "extract.sh")
PROJECT = os.path.join(FIXTURES, "solidity-basic")
PACK = os.path.join(FIXTURES, "solidity-pack-scope.json")


def extract(**env):
    out = os.path.join(tempfile.mkdtemp(), "facts.json")
    r = run(["bash", EXTRACT, PROJECT, out], env=dict(os.environ, CHAINSEC_PACK=PACK, **env))
    assert r.returncode == 0, r.stderr
    return load(out)


class Common:
    facts = None

    def test_schema(self):
        self.assertEqual(validate(self.facts, load(os.path.join(CORE, "engine", "facts.schema.json"))), [])

    def test_scope_excludes_tests_and_libs(self):
        self.assertEqual(sorted(self.facts["counters"]), ["src/Base.sol", "src/Vault.sol"])

    def test_units(self):
        units = {u["name"]: u for u in self.facts["units"]}
        self.assertEqual(set(units), {"Owned", "IERC20", "Vault"})
        self.assertEqual(units["Vault"]["parents"], ["Owned"])
        self.assertEqual(units["IERC20"]["kind"], "interface")

    def test_entry_points(self):
        eps = {(e["unit"], e["name"]) for e in self.facts["entry_points"]}
        self.assertEqual(eps, {("Owned", "transferOwnership"), ("Vault", "deposit"), ("Vault", "depositEth"),
                               ("Vault", "sweep"), ("Vault", "withdraw"), ("Vault", "setFee"), ("Vault", "balanceOf")})

    def test_counters(self):
        strip = lambda c: {k: v for k, v in c.items() if k != "loc"}
        self.assertEqual(strip(self.facts["counters"]["src/Vault.sol"]),
                         {"external_calls": 3, "state_writers": 5, "payable": 1, "assembly_blocks": 1, "unchecked_blocks": 1})
        self.assertEqual(strip(self.facts["counters"]["src/Base.sol"]),
                         {"external_calls": 0, "state_writers": 1, "payable": 0, "assembly_blocks": 0, "unchecked_blocks": 0})

    def test_storage_writes(self):
        writes = {(w["function"], w["target"]) for w in self.facts["storage_writes"]}
        self.assertEqual(writes, {("constructor", "owner"), ("transferOwnership", "owner"),
                                  ("deposit", "balances"), ("deposit", "totalDeposits"), ("depositEth", "balances"),
                                  ("withdraw", "balances"), ("withdraw", "totalDeposits")})

    def test_value_transfers(self):
        vt = {(v["function"], v["asset"]) for v in self.facts["value_transfers"]}
        self.assertEqual(vt, {("deposit", "token"), ("sweep", "native"), ("withdraw", "token")})

    def test_auth_sites(self):
        sites = sorted((a["unit"], a["kind"]) for a in self.facts["auth_sites"])
        self.assertEqual(sites, [("Owned", "inline"), ("Owned", "modifier:onlyOwner"), ("Vault", "modifier:onlyOwner")])


class RegexModeTest(Common, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = extract(CHAINSEC_NO_COMPILE="1")

    def test_mode(self):
        self.assertEqual(self.facts["mode"], "regex")


@unittest.skipUnless(shutil.which("forge"), "forge not installed")
class CompilerModeTest(Common, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = extract()

    def test_mode(self):
        self.assertEqual(self.facts["mode"], "compiler")

    def test_fixture_untouched(self):
        self.assertFalse(os.path.exists(os.path.join(PROJECT, "out")))
        self.assertFalse(os.path.exists(os.path.join(PROJECT, "cache")))


PAIR_SRC = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Pair {
    uint112 private reserve0;
    uint112 private reserve1;
    uint32 private blockTimestampLast;

    function _update(uint256 balance0, uint256 balance1) internal {
        (reserve0, reserve1, blockTimestampLast) =
            (uint112(balance0), uint112(balance1), uint32(block.timestamp));
    }

    function _decode() internal pure returns (uint256, uint256) {
        (uint256 x, uint256 y) = (1, 2);
        return (x, y);
    }
}
"""

FOUNDRY_TOML = """[profile.default]
src = "src"
out = "out"
libs = ["lib"]
"""


class TupleAssignmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = make_tree({"src/Pair.sol": PAIR_SRC, "foundry.toml": FOUNDRY_TOML})

    def test_regex_mode_detects_tuple_writes(self):
        out = os.path.join(tempfile.mkdtemp(), "facts.json")
        r = run(["bash", EXTRACT, self.project, out],
                env=dict(os.environ, CHAINSEC_PACK=PACK, CHAINSEC_NO_COMPILE="1"))
        self.assertEqual(r.returncode, 0, r.stderr)
        facts = load(out)
        self.assertEqual(facts["mode"], "regex")
        writes = {(w["function"], w["target"]) for w in facts["storage_writes"]}
        self.assertEqual(writes, {("_update", "reserve0"), ("_update", "reserve1"),
                                  ("_update", "blockTimestampLast")})

    @unittest.skipUnless(shutil.which("forge"), "forge not installed")
    def test_compiler_mode_detects_tuple_writes(self):
        out = os.path.join(tempfile.mkdtemp(), "facts.json")
        r = run(["bash", EXTRACT, self.project, out], env=dict(os.environ, CHAINSEC_PACK=PACK))
        self.assertEqual(r.returncode, 0, r.stderr)
        facts = load(out)
        self.assertEqual(facts["mode"], "compiler")
        writes = {(w["function"], w["target"]) for w in facts["storage_writes"]}
        self.assertEqual(writes, {("_update", "reserve0"), ("_update", "reserve1"),
                                  ("_update", "blockTimestampLast")})


if __name__ == "__main__":
    unittest.main()
