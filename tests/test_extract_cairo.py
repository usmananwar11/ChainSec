import os
import shutil
import sys
import tempfile
import unittest

from helpers import CORE, FIXTURES, SCRIPTS, load, make_tree, run

sys.path.insert(0, SCRIPTS)
from _schema import validate  # noqa: E402

EXTRACT = os.path.join(CORE, "chains", "cairo", "recon", "extract.sh")
PROJECT = os.path.join(FIXTURES, "cairo-basic")
PACK = os.path.join(CORE, "chains", "cairo", "pack.json")


def extract(root=PROJECT, **env):
    out = os.path.join(tempfile.mkdtemp(), "facts.json")
    r = run(["bash", EXTRACT, root, out], env=dict(os.environ, CHAINSEC_PACK=PACK, **env))
    return r, (load(out) if r.returncode == 0 else None)


class ExtractCairoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r, cls.facts = extract(CHAINSEC_NO_COMPILE="1")
        assert r.returncode == 0, r.stderr

    def test_schema(self):
        self.assertEqual(validate(self.facts, load(os.path.join(CORE, "engine", "facts.schema.json"))), [])
        self.assertEqual((self.facts["chain"], self.facts["mode"]), ("cairo", "regex"))
        self.assertEqual(self.facts["compile"], "unknown")

    def test_scope(self):
        self.assertEqual(sorted(self.facts["counters"]),
                         ["src/bridge.cairo", "src/components.cairo", "src/components/ownable.cairo",
                          "src/lib.cairo"])

    def test_units(self):
        units = {u["name"]: u for u in self.facts["units"]}
        self.assertEqual(set(units), {"IBridge", "Bridge", "OwnableComponent"})
        self.assertEqual(units["Bridge"]["kind"], "contract")
        self.assertEqual(units["Bridge"]["parents"], ["OwnableComponent"])
        self.assertEqual(units["OwnableComponent"]["kind"], "component")
        self.assertEqual(units["IBridge"]["kind"], "interface")

    def test_entry_points(self):
        eps = {(e["unit"], e["name"]): e for e in self.facts["entry_points"]}
        self.assertEqual(set(eps), {("Bridge", "constructor"), ("Bridge", "deposit_from_l1"),
                                    ("Bridge", "balance_of"), ("Bridge", "withdraw_to_l1"),
                                    ("Bridge", "set_l1_bridge")})
        self.assertEqual(eps[("Bridge", "deposit_from_l1")]["visibility"], "l1_handler")
        self.assertEqual(eps[("Bridge", "balance_of")]["mutability"], "view")
        self.assertEqual(eps[("Bridge", "withdraw_to_l1")]["mutability"], "external")
        self.assertIn("assert_only_owner", eps[("Bridge", "set_l1_bridge")]["guards"])
        self.assertEqual(eps[("Bridge", "deposit_from_l1")]["guards"], [])

    def test_storage_writes(self):
        writes = {(w["function"], w["target"]) for w in self.facts["storage_writes"]}
        self.assertIn(("deposit_from_l1", "balances"), writes)
        self.assertIn(("set_l1_bridge", "l1_bridge"), writes)
        self.assertIn(("initializer", "owner"), writes)

    def test_external_calls_and_auth(self):
        calls = {(c["function"], c["kind"]) for c in self.facts["external_calls"]}
        self.assertEqual(calls, {("withdraw_to_l1", "send_message_to_l1_syscall")})
        auth = {(a["unit"], a["kind"]) for a in self.facts["auth_sites"]}
        self.assertIn(("OwnableComponent", "caller-check"), auth)
        self.assertIn(("Bridge", "assert_only"), auth)

    def test_counters(self):
        c = self.facts["counters"]["src/bridge.cairo"]
        self.assertEqual((c["l1_handlers"], c["syscalls"], c["external_calls"]), (1, 1, 1))
        self.assertEqual(c["state_writers"], 4)


class ExtractCairoEdgeTest(unittest.TestCase):
    def test_cairo0_rejected(self):
        root = make_tree({"Scarb.toml": "[package]\nname='x'\n[dependencies]\nstarknet='2'\n",
                          "src/legacy.cairo": "%lang starknet\n@external\nfunc f{}() {\n    return ();\n}\n"})
        r, _ = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 3)
        self.assertIn("Cairo 0", r.stderr)

    def test_comments_and_strings_ignored(self):
        root = make_tree({"Scarb.toml": "[package]\nname='x'\n",
                          "src/lib.cairo": (
                              "#[starknet::contract]\nmod C {\n"
                              "    // self.fake.write(1); call_contract_syscall\n"
                              "    #[storage]\n    struct Storage { x: u8 }\n"
                              "    #[external(v0)]\n    fn f(ref self: ContractState) {\n"
                              "        let _m = 'self.y.write(';\n        self.x.write(1);\n    }\n}\n")})
        r, facts = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([(w["function"], w["target"]) for w in facts["storage_writes"]], [("f", "x")])
        self.assertEqual(facts["external_calls"], [])
        self.assertEqual([(e["name"], e["visibility"]) for e in facts["entry_points"]], [("f", "external")])

    @unittest.skipUnless(shutil.which("scarb"), "scarb not installed")
    def test_compile_status_ok_without_touching_project(self):
        before = os.path.exists(os.path.join(PROJECT, "target"))
        r, facts = extract()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(facts["compile"], "ok")
        self.assertEqual(os.path.exists(os.path.join(PROJECT, "target")), before)


if __name__ == "__main__":
    unittest.main()
