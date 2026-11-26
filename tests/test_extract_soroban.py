import os
import shutil
import sys
import tempfile
import unittest

from helpers import CORE, FIXTURES, SCRIPTS, load, make_tree, run

sys.path.insert(0, SCRIPTS)
from _schema import validate  # noqa: E402

EXTRACT = os.path.join(CORE, "chains", "soroban", "recon", "extract.sh")
PROJECT = os.path.join(FIXTURES, "soroban-basic")
PACK = os.path.join(CORE, "chains", "soroban", "pack.json")
SLOW = os.environ.get("CHAINSEC_SLOW_TESTS") == "1"


def extract(root=PROJECT, **env):
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "facts.json")
    r = run(["bash", EXTRACT, root, out], env=dict(os.environ, CHAINSEC_PACK=PACK, **env))
    facts = load(out) if r.returncode == 0 else None
    shutil.rmtree(tmp, ignore_errors=True)
    return r, facts


def crate(lib, extra=None, toml='[package]\nname = "x"\n[dependencies]\nsoroban-sdk = "22.0.1"\n'):
    files = {"Cargo.toml": toml, "src/lib.rs": lib}
    files.update(extra or {})
    return make_tree(files)


class ExtractSorobanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r, cls.facts = extract(CHAINSEC_NO_COMPILE="1")
        assert r.returncode == 0, r.stderr

    def test_schema_and_header(self):
        self.assertEqual(validate(self.facts, load(os.path.join(CORE, "engine", "facts.schema.json"))), [])
        self.assertEqual((self.facts["chain"], self.facts["mode"], self.facts["compile"]),
                         ("soroban", "regex", "unknown"))
        self.assertTrue(self.facts["sdk"].startswith("26."), self.facts["sdk"])

    def test_scope_excludes_tests(self):
        self.assertEqual(sorted(self.facts["counters"]), ["src/lib.rs", "src/storage.rs"])

    def test_units(self):
        self.assertEqual([(u["name"], u["kind"], u["parents"]) for u in self.facts["units"]],
                         [("Vault", "contract", [])])

    def test_entry_points(self):
        eps = {e["name"]: e for e in self.facts["entry_points"]}
        self.assertEqual(set(eps), {"__constructor", "deposit", "withdraw", "balance", "set_admin", "upgrade"})
        self.assertEqual(eps["__constructor"]["visibility"], "constructor")
        self.assertEqual(eps["balance"]["mutability"], "view")
        self.assertEqual(eps["deposit"]["mutability"], "mutating")
        self.assertEqual(eps["deposit"]["guards"], ["require_auth(from)"])
        self.assertEqual(eps["withdraw"]["guards"], [])
        self.assertEqual(eps["set_admin"]["guards"], ["require_auth(read_admin()) via require_admin"])
        self.assertEqual(eps["upgrade"]["guards"], ["require_auth(read_admin()) via require_admin"])

    def test_storage_writes_ignore_comments_and_test_mods(self):
        writes = sorted((w["unit"], w["function"], w["target"]) for w in self.facts["storage_writes"])
        self.assertEqual(writes, [("Vault", "__constructor", "instance:DataKey::Admin"),
                                  ("Vault", "__constructor", "instance:DataKey::Token"),
                                  ("Vault", "set_admin", "instance:DataKey::Admin"),
                                  ("Vault", "write_balance", "persistent:DataKey::Balance")])

    def test_calls_transfers_auth(self):
        calls = sorted((c["function"], c["kind"]) for c in self.facts["external_calls"])
        self.assertEqual(calls, [("deposit", "client"), ("upgrade", "upgrade"), ("withdraw", "client")])
        self.assertEqual(sorted(v["function"] for v in self.facts["value_transfers"]), ["deposit", "withdraw"])
        self.assertEqual(sorted(a["kind"] for a in self.facts["auth_sites"]), ["require_auth", "require_auth"])

    def test_counters(self):
        c = self.facts["counters"]["src/lib.rs"]
        self.assertEqual((c["external_calls"], c["state_writers"], c["upgrades"], c["token_transfers"],
                          c["unguarded_mutators"]), (3, 4, 1, 2, 1))


class ExtractSorobanEdgeTest(unittest.TestCase):
    def test_traits_macros_and_literals(self):
        root = crate(
            "#![no_std]\n"
            "/* env.storage().instance().set(&K::A, &1); */\n"
            "#[contract]\npub struct Tok;\n"
            "#[contractimpl(contracttrait)]\nimpl FungibleToken for Tok {\n    type ContractType = Base;\n}\n"
            "#[contractimpl]\nimpl Ownable for Tok {}\n"
            "#[contractclient(name = \"OracleClient\")]\npub trait Oracle { fn price(env: Env) -> i128; }\n"
            "#[contractimpl]\nimpl Tok {\n"
            "    #[only_owner]\n"
            "    pub fn mint_to<'a>(e: &'a Env, to: Address, amt: i128) {\n"
            "        let _c = '\"';\n"
            "        let _r = r#\"env.storage().persistent().set(&K::B, &2)\"#;\n"
            "        let _q = '\\'';\n"
            "        e.storage().persistent().set(&K::Bal(to), &(amt as u64));\n"
            "    }\n}\n"
            "#[cfg(not(test))]\nmod real { pub fn f(e: &Env) { e.storage().temporary().set(&1u32, &2u32); } }\n")
        r, facts = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        units = {u["name"]: u for u in facts["units"]}
        self.assertEqual(units["Tok"]["parents"], ["FungibleToken", "Ownable"])
        self.assertEqual(units["Oracle"]["kind"], "interface")
        self.assertEqual([(e["name"], e["guards"]) for e in facts["entry_points"]], [("mint_to", ["only_owner"])])
        self.assertEqual(sorted((w["function"], w["target"]) for w in facts["storage_writes"]),
                         [("f", "temporary:1u32"), ("mint_to", "persistent:K::Bal")])
        self.assertEqual([a["kind"] for a in facts["auth_sites"]], ["auth_macro"])
        self.assertEqual(facts["counters"]["src/lib.rs"]["unchecked_math"], 1)
        self.assertEqual(facts["sdk"], "22.0.1")

    def test_workspace_scope_and_unit_attribution(self):
        root = make_tree({
            "Cargo.toml": '[workspace]\nmembers = ["contracts/*"]\n[workspace.dependencies]\nsoroban-sdk = "23.0.2"\n',
            "contracts/a/Cargo.toml": '[package]\nname = "a"\n[dependencies]\nsoroban-sdk = { workspace = true }\n',
            "contracts/a/src/lib.rs": "#[contract]\npub struct A;\n#[contract]\npub struct B;\n"
                                      "#[contractimpl]\nimpl A { pub fn go(e: Env) { helper(&e); } }\n",
            "contracts/a/src/helpers.rs": "pub fn helper(e: &Env) { e.storage().instance().set(&K::X, &1); }\n",
            "contracts/a/src/test.rs": "fn t(e: &Env) { e.storage().instance().set(&K::T, &1); }\n",
            "contracts/a/tests/it.rs": "fn t(e: &Env) { e.storage().instance().set(&K::T, &1); }\n",
        })
        r, facts = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(facts["counters"]), ["contracts/a/src/helpers.rs", "contracts/a/src/lib.rs"])
        self.assertEqual([(w["unit"], w["function"]) for w in facts["storage_writes"]], [("helpers", "helper")])
        self.assertEqual([(e["name"], e["mutability"]) for e in facts["entry_points"]], [("go", "mutating")])
        self.assertEqual(facts["sdk"], "23.0.2")

    def _facts(self, root):
        r, facts = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        return facts

    def test_same_name_delegation_is_not_view(self):
        facts = self._facts(crate(
            "mod logic { pub fn withdraw(e: &Env, amt: i128) { e.storage().persistent().set(&K::Bal, &amt); } }\n"
            "#[contract]\npub struct V;\n#[contractimpl]\nimpl V {\n"
            "    pub fn withdraw(e: Env, amt: i128) { logic::withdraw(&e, amt); }\n}\n"))
        ep = facts["entry_points"][0]
        self.assertEqual((ep["mutability"], facts["counters"]["src/lib.rs"]["unguarded_mutators"]), ("mutating", 1))

    def test_helpers_resolve_within_same_crate_only(self):
        facts = self._facts(make_tree({
            "Cargo.toml": '[workspace]\nmembers = ["contracts/*"]\n',
            "contracts/a/Cargo.toml": '[package]\nname = "a"\n',
            "contracts/b/Cargo.toml": '[package]\nname = "b"\n',
            "contracts/a/src/lib.rs": "#[contract]\npub struct A;\nfn require_admin(e: &Env) { read_admin(e).require_auth(); }\n"
                                      "#[contractimpl]\nimpl A { pub fn set_fee(e: Env, f: u32) { require_admin(&e); "
                                      "e.storage().instance().set(&K::Fee, &f); } }\n",
            "contracts/b/src/lib.rs": "#[contract]\npub struct B;\nfn require_admin(e: &Env, c: &Address) "
                                      "{ if *c != read_admin(e) { panic!(); } }\n"
                                      "#[contractimpl]\nimpl B { pub fn drain(e: Env, c: Address) { require_admin(&e, &c); "
                                      "e.storage().instance().set(&K::Owner, &c); } }\n"}))
        eps = {e["name"]: e for e in facts["entry_points"]}
        self.assertEqual(eps["set_fee"]["guards"], ["require_auth(read_admin()) via require_admin"])
        self.assertEqual(eps["drain"]["guards"], [])
        self.assertEqual(facts["counters"]["contracts/b/src/lib.rs"]["unguarded_mutators"], 1)

    def test_same_crate_name_clash_guards_are_intersected(self):
        facts = self._facts(crate(
            "#[contract]\npub struct V;\n"
            "fn check(e: &Env) { read_admin(e).require_auth(); }\n"
            "mod other { pub fn check(e: &Env, c: &Address) { if *c != read_admin(e) { panic!(); } } }\n"
            "#[contractimpl]\nimpl V { pub fn go(e: Env, c: Address) { check(&e); "
            "e.storage().instance().set(&K::A, &1); } }\n"))
        self.assertEqual(facts["entry_points"][0]["guards"], [])

    def test_storage_write_turbofish_and_stored_handle(self):
        facts = self._facts(crate(
            "#[contract]\npub struct V;\n#[contractimpl]\nimpl V {\n"
            "    pub fn set_fee(e: Env, fee: u32) {\n"
            "        let store = e.storage().instance();\n"
            "        store.set(&DataKey::Fee, &fee);\n    }\n"
            "    pub fn set_cap(e: Env, cap: u32) {\n"
            "        e.storage().instance().set::<DataKey, u32>(&DataKey::Cap, &cap);\n    }\n"
            "    pub fn rm(e: Env) {\n"
            "        let mut s = e.storage().persistent();\n"
            "        s.remove::<DataKey>(&DataKey::Old);\n    }\n}\n"))
        self.assertEqual(sorted((w["function"], w["target"]) for w in facts["storage_writes"]),
                         [("rm", "persistent:DataKey::Old"), ("set_cap", "instance:DataKey::Cap"),
                          ("set_fee", "instance:DataKey::Fee")])
        self.assertTrue(all(e["mutability"] == "mutating" for e in facts["entry_points"]))

    def test_qualified_soroban_sdk_attributes(self):
        facts = self._facts(crate(
            "#[soroban_sdk::contract]\npub struct V;\n"
            "#[soroban_sdk::contractimpl]\nimpl V { pub fn a(e: Env) { e.storage().instance().set(&K::A, &1); } }\n"
            "#[soroban_sdk::contractclient(name = \"OC\")]\npub trait Oracle { fn price(env: Env) -> i128; }\n"
            "#[soroban_sdk::contracttrait]\npub trait Ext { fn x(env: Env); }\n"))
        self.assertEqual(sorted((u["name"], u["kind"]) for u in facts["units"]),
                         [("Ext", "interface"), ("Oracle", "interface"), ("V", "contract")])
        self.assertEqual([e["name"] for e in facts["entry_points"]], ["a"])

    def test_fn_with_semicolon_in_parameter_type(self):
        facts = self._facts(crate(
            "#[contract]\npub struct V;\n#[contractimpl]\nimpl V {\n"
            "    pub fn set_tag(e: Env, tag: [u8; 4]) { e.storage().instance().set(&K::Tag, &tag); }\n}\n"))
        self.assertEqual([(e["name"], e["mutability"]) for e in facts["entry_points"]],
                         [("set_tag", "mutating")])

    @unittest.skipUnless(shutil.which("cargo") and SLOW, "needs cargo and CHAINSEC_SLOW_TESTS=1")
    def test_stale_cargo_lock_is_left_byte_identical(self):
        stale = ('# This file is automatically @generated by Cargo.\n# It is not intended for manual editing.\n'
                 'version = 3\n\n[[package]]\nname = "x"\nversion = "0.0.1"\n')
        root = make_tree({"Cargo.toml": '[package]\nname = "x"\nversion = "0.1.0"\nedition = "2021"\n',
                          "Cargo.lock": stale, "src/lib.rs": "pub fn f() {}\n"})
        r, facts = extract(root)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(root, "Cargo.lock"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), stale)

    @unittest.skipUnless(shutil.which("cargo") and SLOW, "needs cargo and CHAINSEC_SLOW_TESTS=1")
    def test_compile_status_ok_without_touching_project(self):
        before = sorted(os.listdir(PROJECT))
        r, facts = extract()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(facts["compile"], "ok")
        self.assertEqual(sorted(os.listdir(PROJECT)), before)


if __name__ == "__main__":
    unittest.main()
