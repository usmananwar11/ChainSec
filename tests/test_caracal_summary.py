import json
import os
import tempfile
import unittest

from helpers import CORE, run

import sys

SCRIPT = os.path.join(CORE, "chains", "cairo", "recon", "caracal-summary.py")
SAMPLE = ("controlled-library-call\nImpact: High\nConfidence: Medium\nlibrary call in Vault::upgrade\n\n"
          "unused-events\nImpact: Low\nConfidence: Medium\nEvent X never emitted\n")


def summarize(content):
    d = tempfile.mkdtemp()
    src, out = os.path.join(d, "caracal.json"), os.path.join(d, "caracal.md")
    with open(src, "w") as f:
        f.write(content)
    r = run([sys.executable, SCRIPT, src, out])
    return r, (open(out).read() if r.returncode == 0 else "")


class CaracalSummaryTest(unittest.TestCase):
    def test_json_wrapped_output(self):
        r, md = summarize(json.dumps({"output": SAMPLE}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("High/Medium impact blocks: 1", md)
        self.assertIn("controlled-library-call", md)

    def test_raw_text_and_empty(self):
        r, md = summarize(SAMPLE)
        self.assertIn("High/Medium impact blocks: 1", md)
        r, md = summarize(json.dumps({"output": ""}))
        self.assertIn("Caracal reported nothing.", md)

    def test_missing_input(self):
        r = run([sys.executable, SCRIPT, "/nonexistent/caracal.json", "/tmp/x.md"])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
