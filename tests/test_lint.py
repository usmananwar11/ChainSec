import os
import sys
import unittest

from helpers import REPO, make_tree

sys.path.insert(0, os.path.join(REPO, "tools"))
from lint_skills import lint  # noqa: E402

OA = "policy:\n  allow_implicit_invocation: false\n"
BASE = {
    "plugins/chainsec/skills/chainsec/SKILL.md": "---\nname: chainsec\ndescription: core\n---\nSee `engine/pipeline.md`.\n",
    "plugins/chainsec/skills/chainsec/agents/openai.yaml": OA,
    "plugins/chainsec/skills/chainsec/engine/pipeline.md": "# Pipeline\n",
    "plugins/chainsec/skills/chainsec-audit/SKILL.md": "---\nname: chainsec-audit\ndescription: audit\n---\nRead `../chainsec/engine/pipeline.md`.\n",
    "plugins/chainsec/skills/chainsec-audit/agents/openai.yaml": OA,
}


def tree(**changes):
    files = dict(BASE)
    for k, v in changes.items():
        path = k.replace("__", "/")
        if v is None:
            files.pop(path, None)
        else:
            files[path] = v
    return make_tree(files)


SK = "plugins__chainsec__skills__"


class LintTest(unittest.TestCase):
    def test_clean_tree(self):
        self.assertEqual(lint(tree()), [])

    def test_name_must_match_folder(self):
        errs = lint(tree(**{SK + "chainsec-audit__SKILL.md": "---\nname: audit\ndescription: x\n---\n"}))
        self.assertTrue(any("must match folder" in e for e in errs), errs)

    def test_openai_yaml_required(self):
        errs = lint(tree(**{SK + "chainsec-audit__agents__openai.yaml": None}))
        self.assertTrue(any("openai.yaml" in e for e in errs), errs)

    def test_unresolved_core_path(self):
        errs = lint(tree(**{SK + "chainsec__engine__x.md": "Use `engine/missing.md`.\n"}))
        self.assertTrue(any("unresolved path engine/missing.md" in e for e in errs), errs)

    def test_unresolved_entry_path(self):
        errs = lint(tree(**{SK + "chainsec-audit__SKILL.md": "---\nname: chainsec-audit\ndescription: a\n---\n`../chainsec/nope.md`\n"}))
        self.assertTrue(any("unresolved path ../chainsec/nope.md" in e for e in errs), errs)

    def test_placeholder_paths_ignored(self):
        self.assertEqual(lint(tree(**{SK + "chainsec__engine__x.md": "See `chains/<chain>/pack.json`.\n"})), [])

    def test_neutrality(self):
        errs = lint(tree(**{SK + "chainsec__engine__x.md": "Run forge test.\n"}))
        self.assertTrue(any("neutrality" in e for e in errs), errs)

    def test_neutrality_allow_marker(self):
        md = "Packs include Solidity. <!-- neutrality:allow -->\n"
        self.assertEqual(lint(tree(**{SK + "chainsec__engine__x.md": md})), [])

    def test_neutrality_not_applied_to_packs(self):
        self.assertEqual(lint(tree(**{SK + "chainsec__chains__solidity__notes.md": "Use forge.\n"})), [])

    def test_nested_skill_md(self):
        errs = lint(tree(**{SK + "chainsec__chains__solidity__poc__SKILL.md": "x\n"}))
        self.assertTrue(any("nested SKILL.md" in e for e in errs), errs)

    def test_legacy_krait_paths(self):
        errs = lint(tree(**{SK + "chainsec__engine__x.md": "Read ~/.claude/skills/krait/x.md\n"}))
        self.assertTrue(any("legacy" in e for e in errs), errs)

    def test_broken_markdown_link(self):
        errs = lint(tree(**{SK + "chainsec__engine__x.md": "[a](nope.md)\n"}))
        self.assertTrue(any("broken link" in e for e in errs), errs)

    def test_code_fence_not_parsed_as_link(self):
        body = "```solidity\nint256[] memory b = new int256[](toks.length);\n```\n"
        self.assertEqual(lint(tree(**{SK + "chainsec__chains__x.md": body})), [])

    def test_repository_is_clean(self):
        self.assertEqual(lint(REPO), [])

    def test_expected_skills_present(self):
        skills = os.path.join(REPO, "plugins", "chainsec", "skills")
        self.assertEqual(sorted(os.listdir(skills)),
                         ["chainsec", "chainsec-audit", "chainsec-fuzz", "chainsec-init", "chainsec-poc", "chainsec-review"])


if __name__ == "__main__":
    unittest.main()
