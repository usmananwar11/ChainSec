import os
import tempfile
import unittest

from helpers import REPO, run

SKILLS = ["chainsec", "chainsec-audit", "chainsec-fuzz", "chainsec-init", "chainsec-poc", "chainsec-review"]


def install(*args):
    dest = os.path.join(tempfile.mkdtemp(), "skills")
    r = run(["bash", os.path.join(REPO, "install.sh"), "--dest", dest, *args])
    assert r.returncode == 0, r.stderr
    return dest


class InstallTest(unittest.TestCase):
    def test_copy_install(self):
        dest = install()
        self.assertEqual(sorted(os.listdir(dest)), SKILLS)
        self.assertTrue(os.path.isfile(os.path.join(dest, "chainsec-audit", "..", "chainsec", "engine", "pipeline.md")))
        self.assertFalse(os.path.islink(os.path.join(dest, "chainsec")))

    def test_link_install_and_reinstall(self):
        dest = install("--link")
        self.assertTrue(os.path.islink(os.path.join(dest, "chainsec-audit")))
        r = run(["bash", os.path.join(REPO, "install.sh"), "--dest", dest, "--link"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(os.listdir(dest)), SKILLS)

    def test_unknown_tool(self):
        r = run(["bash", os.path.join(REPO, "install.sh"), "--tool", "nope"])
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
