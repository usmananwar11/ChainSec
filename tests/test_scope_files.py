import json
import os
import shutil
import unittest

from helpers import CORE, FIXTURES, make_tree, run_py

PACK = os.path.join(CORE, "chains", "solidity", "pack.json")


class ScopeFilesTest(unittest.TestCase):
    def scope(self, root):
        result = run_py("scope-files.py", "--root", root, "--pack", PACK)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def tree(self, files):
        root = make_tree({name: "" for name in files})
        self.addCleanup(shutil.rmtree, root)
        return root

    def test_smoke_fixture_counts_only_audited_sources(self):
        self.assertEqual(self.scope(os.path.join(FIXTURES, "solidity-basic")), {
            "scope_files": 2, "files": ["src/Base.sol", "src/Vault.sol"],
        })

    def test_primary_scope_excludes_nested_tests_mocks_and_scripts(self):
        root = self.tree(["src/Vault.sol", "src/nested/Helper.sol", "src/test/Test.sol",
                          "src/mocks/Mock.sol", "src/Check.t.sol", "src/Deploy.s.sol",
                          "contracts/scripts/Deploy.sol", "other/Outside.sol"])
        self.assertEqual(self.scope(root), {
            "scope_files": 2, "files": ["src/Vault.sol", "src/nested/Helper.sol"],
        })

    def test_fallback_after_exclusions_still_excludes_tests_and_dependencies(self):
        root = self.tree(["src/test/Test.sol", "Root.sol", "custom/Vault.sol",
                          "test/Test.sol", "lib/dep/Dep.sol", "node_modules/Dep.sol",
                          "out/Generated.sol", ".audit/poc/Exploit.sol"])
        self.assertEqual(self.scope(root), {
            "scope_files": 2, "files": ["Root.sol", "custom/Vault.sol"],
        })

    def test_only_excluded_files_means_zero_scope(self):
        root = self.tree(["test/Test.sol", "src/mocks/Mock.sol", "lib/Dep.sol"])
        self.assertEqual(self.scope(root), {"scope_files": 0, "files": []})

    def test_missing_root_is_an_error(self):
        root = self.tree([])
        result = run_py("scope-files.py", "--root", os.path.join(root, "missing"), "--pack", PACK)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
