import os
import re
import unittest

from helpers import CORE, FIXTURES

IDS = os.path.join(FIXTURES, "krait-ids.txt")


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


if __name__ == "__main__":
    unittest.main()
