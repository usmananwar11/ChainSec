"""Shared test helpers. Tests run with: python3 -m unittest discover -s tests"""
import copy
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(REPO, "plugins", "chainsec", "skills", "chainsec")
SCRIPTS = os.path.join(CORE, "scripts")
FIXTURES = os.path.join(REPO, "tests", "fixtures")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def run_py(script, *args, **kw):
    return run([sys.executable, os.path.join(SCRIPTS, script), *args], **kw)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_tmp_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def make_tree(files):
    root = tempfile.mkdtemp()
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return root


VALID_FINDING = {
    "id": "SOL-001",
    "chain": "solidity",
    "title": "Anyone can sweep the vault's native balance",
    "severity": "High",
    "category": "access-control",
    "status": "verified",
    "locations": [{"file": "src/Vault.sol", "line_start": 33, "line_end": 35}],
    "description": "sweep() has no access control.",
    "root_cause": "missing access control on sweep",
    "recommendation": "Restrict sweep() to the owner.",
    "harm": {"who": "vault depositors", "loses_what": "all native ETH held by the vault", "magnitude": "full native balance"},
    "exploit_trace": ["attacker calls sweep(attacker)", "vault transfers its whole balance to attacker"],
    "discovery": {"phase": "detect", "lens": "A", "mindset": "attacker", "consensus": "strong"},
    "verdict": {"gate": None, "reason": "trace confirmed", "evidence_tag": "[CODE-TRACE]", "method": "A"},
}


def valid_finding(**overrides):
    f = copy.deepcopy(VALID_FINDING)
    f.update(overrides)
    return f
