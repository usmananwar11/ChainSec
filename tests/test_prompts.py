import os
import re
import unittest

from helpers import CORE

PROMPTS = os.path.join(CORE, "prompts")
REQUIRED = {"{{CORE}}", "{{CHAIN}}", "{{ROOT}}", "{{A}}", "{{OUTPUT}}"}
EXTRA = {"lens-detector.md": {"{{LENS}}"}, "per-unit.md": {"{{CLUSTER_N}}", "{{CLUSTER_UNITS}}"}}
NAMES = [
    "pass1-detector.md",
    "lens-detector.md",
    "rescan.md",
    "per-unit.md",
    "state-auditor.md",
    "critic.md",
    "reviewer.md",
    "reporter.md",
]


class PromptTemplateTest(unittest.TestCase):
    def test_placeholders_and_done_line(self):
        for name in NAMES:
            with open(os.path.join(PROMPTS, name), encoding="utf-8") as f:
                text = f.read()
            found = set(re.findall(r"\{\{[A-Z_]+\}\}", text))
            self.assertTrue(REQUIRED | EXTRA.get(name, set()) <= found, f"{name}: missing {REQUIRED - found}")
            self.assertIn("DONE {{OUTPUT}}", text, name)
            self.assertIn("{{CORE}}/engine/phases/", text, name)


if __name__ == "__main__":
    unittest.main()
