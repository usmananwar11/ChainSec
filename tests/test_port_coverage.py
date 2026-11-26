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

# CoinFabrik scout-soroban (MIT) at commit 53157fd and stellar/stellar-dev-skill (Apache-2.0) at
# commit 9098e8b, the sources the Soroban pack was ported from. Override with SCOUT_SOROBAN_SRC /
# STELLAR_DEV_SKILL_SRC; the tests skip when a source is not on this machine.
SCOUT_SRC = os.environ.get("SCOUT_SOROBAN_SRC", os.path.expanduser("~/src/scout-soroban"))
STELLAR_SRC = os.environ.get("STELLAR_DEV_SKILL_SRC", os.path.expanduser("~/src/stellar-dev-skill"))
SOROBAN_PATTERNS = os.path.join(CORE, "chains", "soroban", "patterns")
# stellar-dev-skill security.md "### <n>." classes -> pattern IDs. Class 5 (integer overflow) is
# covered by Scout's INTEGER-OVERFLOW-OR-UNDERFLOW and OVERFLOW-CHECK.
STELLAR_CLASSES = {1: "MISSING-AUTH", 2: "AUTH-REPLAY-MIDDLEWARE", 3: "REINITIALIZATION",
                   4: "ARBITRARY-CONTRACT-CALL", 5: "INTEGER-OVERFLOW-OR-UNDERFLOW",
                   6: "STORAGE-KEY-COLLISION", 7: "CHECK-THEN-ACT", 8: "TTL-ARCHIVAL",
                   9: "UNTRUSTED-RETURN-VALUE", 10: "RESOURCE-EXHAUSTION",
                   11: "CUSTOM-ACCOUNT-CHECK-AUTH", 12: "MALFORMED-BYTES"}


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

    def test_every_scout_class_has_a_pattern(self):
        cases = os.path.join(SCOUT_SRC, "test-cases")
        if not os.path.isdir(cases):
            self.skipTest(f"scout-soroban source not found at {SCOUT_SRC}")
        ids = sorted(d.upper() for d in os.listdir(cases) if os.path.isdir(os.path.join(cases, d)))
        self.assertEqual(len(ids), 23)
        missing = [i for i in ids if not os.path.isfile(os.path.join(SOROBAN_PATTERNS, i + ".md"))]
        self.assertEqual(missing, [], f"{len(missing)} Scout classes have no patterns/<ID>.md")

    def test_every_stellar_class_has_a_pattern(self):
        missing = [i for i in STELLAR_CLASSES.values()
                   if not os.path.isfile(os.path.join(SOROBAN_PATTERNS, i + ".md"))]
        self.assertEqual(missing, [], f"{len(missing)} Stellar classes have no patterns/<ID>.md")
        sec = os.path.join(STELLAR_SRC, "skills", "smart-contracts", "security.md")
        if not os.path.isfile(sec):
            self.skipTest(f"stellar-dev-skill source not found at {STELLAR_SRC}")
        with open(sec, encoding="utf-8") as f:
            numbers = [int(n) for n in re.findall(r"^### (\d+)\.", f.read(), re.M)]
        self.assertEqual(sorted(numbers), sorted(STELLAR_CLASSES), "source classes changed; update the map")


if __name__ == "__main__":
    unittest.main()
