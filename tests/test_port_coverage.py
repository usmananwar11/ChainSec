import os
import re
import unittest

from helpers import CORE, FIXTURES

IDS = os.path.join(FIXTURES, "krait-ids.txt")
# cairo-auditor vulnerability DB the Cairo pack was ported from (starknet-agentic-skills 1.0.4).
# Override with CAIRO_AUDITOR_VULN_DB; the test skips when the source is not on this machine.
CAIRO_VULN_DB = os.environ.get("CAIRO_AUDITOR_VULN_DB", os.path.expanduser(
    "~/.claude/plugins/cache/starknet-agentic-skills/starknet-agentic-skills/1.0.4/"
    "skills/cairo-auditor/references/vulnerability-db"))
CAIRO_PATTERNS = os.path.join(CORE, "chains", "cairo", "patterns")


def corpus():
    text = []
    for dirpath, _, files in os.walk(CORE):
        for fn in files:
            if fn.endswith(".md"):
                with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                    text.append(f.read())
    return "\n".join(text)


class PortCoverageTest(unittest.TestCase):
    def test_every_krait_id_survives(self):
        with open(IDS, encoding="utf-8") as f:
            ids = [l.strip() for l in f if l.strip()]
        body = corpus()
        missing = [i for i in ids if not re.search(r"\b" + re.escape(i) + r"\b", body)]
        self.assertEqual(missing, [], f"{len(missing)} Krait IDs not found in ported content")

    def test_every_cairo_vuln_db_id_has_a_pattern(self):
        if not os.path.isdir(CAIRO_VULN_DB):
            self.skipTest(f"cairo-auditor source not found at {CAIRO_VULN_DB}")
        ids = sorted(fn[:-3] for fn in os.listdir(CAIRO_VULN_DB)
                     if fn.endswith(".md") and fn != "README.md")
        self.assertTrue(ids, "no vulnerability-db entries found in the source")
        missing = [i for i in ids if not os.path.isfile(os.path.join(CAIRO_PATTERNS, i + ".md"))]
        self.assertEqual(missing, [], f"{len(missing)} cairo-auditor IDs have no patterns/<ID>.md")


if __name__ == "__main__":
    unittest.main()
