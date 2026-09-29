import json
import os
import sys
import tempfile
import unittest

from helpers import CORE, FIXTURES, run

SCRIPT = os.path.join(CORE, "chains", "solidity", "recon", "slither-summary.py")
SAMPLE = os.path.join(FIXTURES, "slither", "sample.json")


def run_script(*args):
    return run([sys.executable, SCRIPT, *args])


class SlitherSummaryTest(unittest.TestCase):
    def test_missing_input_exits_1(self):
        missing = os.path.join(tempfile.mkdtemp(), "nope.json")
        out = os.path.join(tempfile.mkdtemp(), "out.md")
        r = run_script(missing, out)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"No Slither results found at {missing}", r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_no_detectors_exits_1(self):
        bad = os.path.join(tempfile.mkdtemp(), "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump({"success": True, "results": {}}, f)
        out = os.path.join(tempfile.mkdtemp(), "out.md")
        r = run_script(bad, out)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Invalid Slither JSON or no detectors found", r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_summary_rows_and_totals(self):
        out = os.path.join(tempfile.mkdtemp(), "out.md")
        r = run_script(SAMPLE, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"Slither summary written to {out}", r.stderr)

        with open(out, encoding="utf-8") as f:
            text = f.read()

        with open(SAMPLE, encoding="utf-8") as f:
            detectors = json.load(f)["results"]["detectors"]
        high_medium = [d for d in detectors if d["impact"] in ("High", "Medium")]
        self.assertEqual(len(high_medium), 3)

        rows = []
        for i, d in enumerate(high_medium, start=1):
            elements = d.get("elements") or []
            elem = elements[0] if elements else {}
            sm = elem.get("source_mapping", {})
            file_ = sm.get("filename_relative", "unknown")
            lines = sm.get("lines") or []
            line = lines[0] if lines else "?"
            desc = d["description"].split("\n")[0][:120]
            rows.append(f"| {i} | {d['check']} | {d['impact']} | {file_}:{line} | {desc} |")

        # Only High/Medium survive, in original order, numbered 1..n.
        self.assertEqual(rows[0], f"| 1 | reentrancy-eth | High | src/Vault.sol:40 | "
                                   f"Reentrancy in Vault.withdraw(uint256) (src/Vault.sol#40-52): |")
        self.assertEqual(rows[1], "| 2 | unchecked-transfer | Medium | src/Token.sol:42 | "
                                   "Token.sweep(address) (src/Token.sol#42) ignores return value of ERC20 transfer. |")
        # elements: [] falls back to unknown:? and the long description is truncated to 120 chars.
        self.assertTrue(rows[2].startswith("| 3 | arbitrary-send-eth | High | unknown:? | "))
        desc3 = rows[2].split("| unknown:? | ", 1)[1][:-2]
        self.assertEqual(len(desc3), 120)
        self.assertNotIn("Second line", text)

        expected_header = [
            "# Slither Pre-Scan Summary",
            f"> Source: {SAMPLE}",
            "> Filtered to: High and Medium severity only",
            "",
            "| # | Detector | Severity | File:Line | Description |",
            "|---|----------|----------|-----------|-------------|",
        ]
        expected = "\n".join(expected_header + rows) + "\n\n**Total**: 3 findings (2 High, 1 Medium)\n\n" \
            "These findings are ADDITIONAL SIGNAL for ChainSec's detection phase — they are NOT auto-reported.\n"
        self.assertEqual(text, expected)

    def test_defaults_to_audit_paths(self):
        cwd = tempfile.mkdtemp()
        os.makedirs(os.path.join(cwd, ".audit"))
        with open(SAMPLE, encoding="utf-8") as f:
            data = f.read()
        with open(os.path.join(cwd, ".audit", "slither-results.json"), "w", encoding="utf-8") as f:
            f.write(data)
        r = run([sys.executable, SCRIPT], cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(cwd, ".audit", "slither-summary.md")))


if __name__ == "__main__":
    unittest.main()
