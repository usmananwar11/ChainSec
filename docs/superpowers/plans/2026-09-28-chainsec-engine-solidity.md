# ChainSec Engine + Solidity Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship ChainSec v0.1: a chain-agnostic audit engine extracted from Krait, with Solidity as the first pack. It is packaged as a Claude Code plugin and installs as plain Agent Skills for OpenCode, Codex and Antigravity.

**Architecture:** One core skill (`skills/chainsec/`) holds the engine (methodology markdown + JSON schemas), chain packs, DeFi domain knowledge, subagent prompt templates, runtime adapters and stdlib-Python scripts. Thin entry skills (`chainsec-audit`, `-review`, `-poc`, `-fuzz`, `-init`) point into the core via `../chainsec/`. Phases exchange JSON validated by scripts. Subagent fan-out is per-runtime, with a sequential fallback.

**Tech Stack:** Markdown (Agent Skills format, agentskills.io), JSON Schema (draft 2020-12 subset), Python 3.11+ standard library only, bash, `unittest`, GitHub Actions. Optional: Foundry `forge` (compiler-mode facts, PoC, fuzz) and `slither`.

**Spec:** `docs/superpowers/specs/2026-09-28-chainsec-engine-solidity-design.md` (see its §11 Amendments, added in Task 1).

**Krait source:** `~/krait` (MIT, Zealynx Security). Skill files are in `~/krait/.claude/skills/krait/` and `~/krait/.claude/skills/krait-poc/`, and commands in `~/krait/.claude/commands/`. Below, `K/` = `~/krait/.claude/skills/krait/` and `KP/` = `~/krait/.claude/skills/krait-poc/`.

## Global Constraints

- Scripts: Python ≥ 3.11 **standard library only** (no pip installs); shell wrappers in bash. No `jq` dependency.
- Path convention in markdown: inside the core skill, every path is written **relative to the core skill folder** (`engine/...`, `chains/solidity/...`). Inside entry skills, paths are `../chainsec/...`. `pack.json` paths are relative to the pack folder.
- Forbidden in `plugins/chainsec/skills/**`: `~/.claude/skills` paths and `/krait` command references (except in ATTRIBUTION files). `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` may appear only in `runtimes/claude-code.md`.
- Skill `name` = folder name, lowercase letters, digits and hyphens, ≤ 64 characters. Every entry skill is prefixed `chainsec-`. `description` is one line of ≤ 1024 characters.
- No file named `SKILL.md` below a skill's top folder. Tools may load nested ones as separate skills.
- `engine/`, `prompts/`, `runtimes/` and `domains/` contain no chain-specific terms. The lint list is `solidity`, `forge`, `foundry`, `slither`, `openzeppelin`, `solmate`, `.sol`, `msg.sender`. A line may opt out with `<!-- neutrality:allow -->`.
- Statuses: only `candidate`, `verified`, `verified-conditional`, `downgraded`, `killed`.
- Porting Krait content: **relocate and re-path, don't rewrite.** Allowed edits:
  - path changes;
  - output-format changes (markdown → JSON findings);
  - verdict vocabulary changes;
  - "Krait" → "ChainSec" in running text (not in attribution);
  - moving chain-specific passages into the pack.
  Heuristic, module, question and gate wording stays verbatim.
- `bash tests/run.sh` must pass at the end of every task.
- Git: commit at the end of every task and push `origin main`. **Never add a `Co-Authored-By: Claude` trailer or a "Generated with Claude Code" line.** Commit messages read as the user's own.

## File Map

```
ChainSec/
├── .claude-plugin/marketplace.json                          T1
├── .github/workflows/test.yml                               T1
├── .gitignore  LICENSE  README.md  ATTRIBUTION.md  INSTALL.md   T1 (README/INSTALL finished T14)
├── install.sh                                               T14
├── tools/lint_skills.py                                     T1
├── tools/score_benchmark.py                                 T15
├── benchmarks/solidity/{registry.yaml,scoring.md,baselines/krait-v8.json,results/}   T15
├── tests/run.sh, tests/helpers.py, tests/test_*.py, tests/fixtures/**                 T1–T15
└── plugins/chainsec/
    ├── .claude-plugin/plugin.json                           T1
    └── skills/
        ├── chainsec/
        │   ├── SKILL.md, agents/openai.yaml                 T1 (placeholder) → T13
        │   ├── ATTRIBUTION.md                               T1
        │   ├── scripts/_common.py, _schema.py               T2
        │   ├── scripts/validate-findings.py                 T3
        │   ├── scripts/score-risk.py                        T4
        │   ├── scripts/detect-chain.py                      T5
        │   ├── scripts/merge-findings.py                    T6
        │   ├── engine/{finding,facts,pack}.schema.json      T2
        │   ├── engine/{pipeline,verdicts,kill-gates,mindsets,report-template,fuzz}.md, engine/poc/*   T10
        │   ├── engine/phases/*.md                           T11
        │   ├── prompts/*.md, runtimes/*.md                  T12
        │   ├── domains/defi/{modules,primers}/*.md, heuristics.md, triggers.md   T8
        │   └── chains/solidity/
        │       ├── recon/extract.sh, recon/extract.py       T7
        │       ├── modules/*.md, primers/*.md (Solidity halves)   T8
        │       └── pack.json, heuristics.md, fp-patterns.md, module-triggers.md,
        │           recon/{clustering.md,slither-summary.sh}, poc/**, fuzz/**, patterns/**   T9
        ├── chainsec-audit/ chainsec-review/ chainsec-poc/ chainsec-fuzz/ chainsec-init/   T13
```

---

### Task 1: Repo scaffold, test harness, structure lint

**Files:**
- Create: `.gitignore`, `LICENSE`, `README.md`, `ATTRIBUTION.md`, `INSTALL.md`, `.claude-plugin/marketplace.json`, `plugins/chainsec/.claude-plugin/plugin.json`
- Create: `plugins/chainsec/skills/chainsec/SKILL.md` (placeholder), `plugins/chainsec/skills/chainsec/agents/openai.yaml`, `plugins/chainsec/skills/chainsec/ATTRIBUTION.md`
- Create: `tools/lint_skills.py`, `tests/run.sh`, `tests/helpers.py`, `tests/test_lint.py`, `.github/workflows/test.yml`
- Modify: `docs/superpowers/specs/2026-09-28-chainsec-engine-solidity-design.md` (append §11 Amendments)

**Interfaces:**
- Produces: `tools/lint_skills.py` with `lint(repo_root: str) -> list[str]` (the list of error strings) and CLI `python3 tools/lint_skills.py [--root DIR]` (exit 1 if any errors). `tests/helpers.py` provides `REPO`, `CORE`, `SCRIPTS`, `FIXTURES`, `run(cmd, **kw) -> CompletedProcess`, `run_py(script_name, *args, **kw)`, `write_tmp_json(data) -> path`, `load(path)`, `make_tree(files: dict[str, str]) -> tmpdir`, `valid_finding(**overrides) -> dict`.

- [ ] **Step 1: Write the top-level files**

`.gitignore`:
```
.audit/
__pycache__/
*.pyc
.DS_Store
out/
cache/
```

`LICENSE`: the standard MIT license text with the line `Copyright (c) 2026 Usman Anwar`.

`ATTRIBUTION.md` (repo root):
```markdown
# Attribution

ChainSec's engine and Solidity pack are derived from **Krait** by Zealynx Security (MIT),
https://github.com/zealynx/krait. Krait itself integrates MIT-licensed work from pashov/skills,
PlamenTSV/plamen and forefy/.context.

The canonical attribution, including Krait's full license text and third-party source list,
travels with the skills in [plugins/chainsec/skills/chainsec/ATTRIBUTION.md](plugins/chainsec/skills/chainsec/ATTRIBUTION.md).
```

`plugins/chainsec/skills/chainsec/ATTRIBUTION.md`: build it from these parts, in order:
1. The heading `# ChainSec — Sources & Attribution`, then one paragraph saying ChainSec's engine, Solidity pack and DeFi domain content are derived from Krait by Zealynx Security under the MIT License, relocated into a multi-chain layout.
2. `## Krait license`, then the full text of `~/krait/LICENSE`, verbatim, in a fenced block.
3. `## Sources integrated by Krait`, then the full body of `K/ATTRIBUTION.md` verbatim. Change only its relative link `../krait-poc/references/ATTRIBUTION.md` to `chains/solidity/poc/ATTRIBUTION.md`.

That target file is created in Task 9, so until then the lint would flag a broken link. In this task write it as plain text, **with no markdown link and no backticks**: `see chains/solidity/poc/ATTRIBUTION.md (added with the Solidity pack)`. Turn it into a link in Task 9.

`.claude-plugin/marketplace.json`:
```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "chainsec",
  "owner": { "name": "Usman Anwar", "url": "https://github.com/usmananwar11" },
  "metadata": {
    "description": "Multi-chain smart-contract security audits: one engine, one pack per chain.",
    "version": "0.1.0"
  },
  "plugins": [
    {
      "name": "chainsec",
      "source": "./plugins/chainsec",
      "description": "Smart-contract security audit pipeline (recon, multi-lens detection, state analysis, kill-gate verification, report) with per-chain packs. Solidity today; Cairo and Soroban planned.",
      "category": "security",
      "keywords": ["security", "audit", "smart-contracts", "solidity", "defi", "multi-chain"]
    }
  ]
}
```

`plugins/chainsec/.claude-plugin/plugin.json`:
```json
{
  "name": "chainsec",
  "version": "0.1.0",
  "description": "Multi-chain smart-contract security audit skills: shared engine plus per-chain packs.",
  "author": { "name": "Usman Anwar", "url": "https://github.com/usmananwar11" },
  "homepage": "https://github.com/usmananwar11/ChainSec",
  "repository": "https://github.com/usmananwar11/ChainSec",
  "license": "MIT",
  "keywords": ["security", "audit", "smart-contracts", "solidity", "defi"]
}
```

`README.md` (finished in Task 14; for now):
```markdown
# ChainSec

Multi-chain smart-contract security audits for AI coding agents (Claude Code, OpenCode, Codex, Antigravity).
One audit engine, one pack per chain. Solidity first; Cairo and Soroban next.

Status: under construction (v0.1). See `docs/superpowers/specs/` for the design.

License: MIT. Derived from Krait by Zealynx Security — see ATTRIBUTION.md.
```

`INSTALL.md` (finished in Task 14): `# Installing ChainSec` followed by `Instructions land with v0.1.`

Core placeholder `plugins/chainsec/skills/chainsec/SKILL.md`:
```markdown
---
name: chainsec
description: ChainSec core library (audit engine, chain packs, prompts, scripts) used by the chainsec-* skills. Do not invoke directly.
user-invocable: false
disable-model-invocation: true
---

# ChainSec core

Placeholder — completed in a later task.
```

`plugins/chainsec/skills/chainsec/agents/openai.yaml`:
```yaml
interface:
  display_name: "ChainSec core"
  short_description: "Library used by the chainsec-* skills"
policy:
  allow_implicit_invocation: false
```

- [ ] **Step 2: Write test helpers and runner**

`tests/run.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/lint_skills.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`tests/helpers.py`:
```python
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
```

- [ ] **Step 3: Write the failing lint tests**

`tests/test_lint.py`:
```python
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

    def test_repository_is_clean(self):
        self.assertEqual(lint(REPO), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -p 'test_lint.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'lint_skills'`.

- [ ] **Step 5: Implement `tools/lint_skills.py`**

```python
#!/usr/bin/env python3
"""Structure lint for the ChainSec plugin.

Usage: lint_skills.py [--root REPO]    (exit 1 when any error is found)

Checks every skill under plugins/chainsec/skills/:
  - SKILL.md frontmatter: name == folder, valid name, one-line description <= 1024 chars
  - agents/openai.yaml sets allow_implicit_invocation: false
  - no nested SKILL.md
  - backticked core paths (engine/, prompts/, runtimes/, domains/, chains/, scripts/)
    resolve against the core skill; ../chainsec/... resolves against the entry skill
  - markdown links resolve against the file's folder
  - no legacy Krait paths or commands (except ATTRIBUTION files)
  - engine/, prompts/, runtimes/, domains/ contain no chain-specific terms
  - every chains/<chain>/pack.json validates and its referenced files exist
    (pack checks run once at least one pack.json exists)
"""
import argparse
import glob
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CORE_DIRS = ("engine", "prompts", "runtimes", "domains", "chains", "scripts")
NEUTRAL_DIRS = ("engine", "prompts", "runtimes", "domains")
BANNED = re.compile(r"\bsolidity\b|\bforge\b|\bfoundry\b|\bslither\b|openzeppelin|solmate|\.sol\b|msg\.sender", re.I)
ALLOW_MARK = "<!-- neutrality:allow -->"
LEGACY = re.compile(r"~/\.claude/skills|(?<![\w/-])/krait\b")
BACKTICK = re.compile(r"`([^`\s]+)`")
MDLINK = re.compile(r"\]\(([^)\s]+)\)")
PACK_FILES = ("heuristics.md", "fp-patterns.md", "module-triggers.md")


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    meta = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def resolve_backtick(sdir, ref):
    if any(c in ref for c in "<>{}*$|"):
        return None
    ref = ref.rstrip(".,:;")
    if ref.startswith("../chainsec/"):
        return os.path.normpath(os.path.join(sdir, ref))
    if "/" in ref and ref.split("/")[0] in CORE_DIRS:
        return os.path.normpath(os.path.join(os.path.dirname(sdir), "chainsec", ref))
    return None


def lint_markdown(name, sdir, path, relp):
    errors = []
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    neutral = name == "chainsec" and relp.split(os.sep)[0] in NEUTRAL_DIRS
    attribution = os.path.basename(path).upper().startswith("ATTRIBUTION")
    for i, line in enumerate(lines, 1):
        where = f"{name}/{relp}:{i}"
        if not attribution and LEGACY.search(line):
            errors.append(f"{where}: legacy Krait path or command")
        if neutral and ALLOW_MARK not in line:
            hit = BANNED.search(line)
            if hit:
                errors.append(f"{where}: neutrality: chain-specific term {hit.group(0)!r} in engine/domain file")
        for ref in BACKTICK.findall(line):
            target = resolve_backtick(sdir, ref)
            if target and not os.path.exists(target):
                errors.append(f"{where}: unresolved path {ref.rstrip('.,:;')}")
        for ref in MDLINK.findall(line):
            if re.match(r"^(https?:|mailto:|#)", ref):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(path), ref.split("#")[0]))
            if not os.path.exists(target):
                errors.append(f"{where}: broken link {ref}")
    return errors


def lint_skill(name, sdir):
    skill_md = os.path.join(sdir, "SKILL.md")
    meta = frontmatter(skill_md) if os.path.isfile(skill_md) else None
    if meta is None:
        return [f"{name}: SKILL.md missing or has no frontmatter"]
    errors = []
    if meta.get("name") != name:
        errors.append(f"{name}: frontmatter name {meta.get('name')!r} must match folder")
    if not NAME_RE.match(name) or len(name) > 64:
        errors.append(f"{name}: invalid skill name")
    desc = meta.get("description", "")
    if not desc or len(desc) > 1024:
        errors.append(f"{name}: description missing or over 1024 chars")
    oa = os.path.join(sdir, "agents", "openai.yaml")
    if not os.path.isfile(oa) or "allow_implicit_invocation: false" not in open(oa, encoding="utf-8").read():
        errors.append(f"{name}: agents/openai.yaml must set allow_implicit_invocation: false")
    for dirpath, dirnames, files in os.walk(sdir):
        dirnames.sort()
        for fn in sorted(files):
            path = os.path.join(dirpath, fn)
            relp = os.path.relpath(path, sdir)
            if fn == "SKILL.md" and dirpath != sdir:
                errors.append(f"{name}/{relp}: nested SKILL.md (tools may load it as a separate skill)")
            if fn.endswith(".md"):
                errors += lint_markdown(name, sdir, path, relp)
    return errors


def lint_packs(core):
    sys.path.insert(0, os.path.join(core, "scripts"))
    from _schema import load, validate  # noqa: E402
    schema_path = os.path.join(core, "engine", "pack.schema.json")
    if not os.path.isfile(schema_path):
        return ["chainsec/engine/pack.schema.json missing"]
    schema = load(schema_path)
    errors = []
    chains = os.path.join(core, "chains")
    for chain in sorted(os.listdir(chains)):
        pdir = os.path.join(chains, chain)
        if not os.path.isdir(pdir):
            continue
        pj = os.path.join(pdir, "pack.json")
        if not os.path.isfile(pj):
            errors.append(f"chains/{chain}: pack.json missing")
            continue
        pack = load(pj)
        errors += [f"chains/{chain}/pack.json: {e}" for e in validate(pack, schema)]
        if pack.get("chain") != chain:
            errors.append(f"chains/{chain}/pack.json: chain must be {chain!r}")
        refs = list(PACK_FILES)
        refs += [pack.get("extractor"), pack.get("clustering"),
                 (pack.get("poc") or {}).get("guide"), (pack.get("fuzz") or {}).get("guide")]
        refs += [a.get("run") for a in pack.get("analyzers", [])]
        refs += [p for paths in (pack.get("modules_by_protocol") or {}).values() for p in paths]
        for ref in refs:
            if ref and not os.path.exists(os.path.normpath(os.path.join(pdir, ref))):
                errors.append(f"chains/{chain}: missing {ref}")
    return errors


def lint(repo):
    skills_dir = os.path.join(repo, "plugins", "chainsec", "skills")
    if not os.path.isdir(skills_dir):
        return [f"missing {skills_dir}"]
    errors = []
    for name in sorted(os.listdir(skills_dir)):
        sdir = os.path.join(skills_dir, name)
        if os.path.isdir(sdir):
            errors += lint_skill(name, sdir)
    core = os.path.join(skills_dir, "chainsec")
    if glob.glob(os.path.join(core, "chains", "*", "pack.json")):
        errors += lint_packs(core)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="ChainSec structure lint")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args(argv)
    errors = lint(args.root)
    for e in errors:
        print(e)
    print(f"lint: {len(errors)} error(s)", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `bash tests/run.sh`
Expected: `lint: 0 error(s)`, then all 13 tests in `test_lint.py` pass (`OK`).

- [ ] **Step 7: Add CI**

`.github/workflows/test.yml`:
```yaml
name: test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: bash tests/run.sh
```

- [ ] **Step 8: Append spec amendments**

Append to the spec, as a new last section:
```markdown
## 11. Amendments (from implementation planning, 2026-09-28)

1. `detect-chain.sh` → `scripts/detect-chain.py` (stdlib glob handling; removes the jq dependency).
2. `pack.json` gains:
   - `extensions` (file extensions owned by the chain, used for boundary tagging);
   - `id_prefix` (finding ID prefix, e.g. `SOL`);
   - `analyzers` (optional static-analyzer adapters);
   - `detect.markers` / `detect.fallback_glob`;
   - `scope.fallback_include`.
   `tools.required` / `tools.optional` become objects `{name, check, install, purpose}` so preflight can print install hints.
3. Solidity extractor = `recon/extract.sh` (build wrapper) + `recon/extract.py` (facts). `forge build --ast` writes to a temp dir, so the user's `out/` and `cache/` are untouched. Krait's macOS-incompatible `timeout` call is dropped.
4. `counters.external_calls` counts only value/call primitives (`call`, `delegatecall`, `staticcall`, `send`, `transfer`, `transferFrom`, `safeTransfer*`) in both modes. Krait's compiler mode counted every member-access call. This is recorded in the benchmark notes because it can move risk tiers.
5. `merge-findings.py --concat` concatenates per-unit/per-lens outputs without dedup.
6. Solidity required tools: `python3`, `forge`. `jq` is no longer required.
7. The canonical ATTRIBUTION lives in the core skill folder so it travels with copied skills. The root ATTRIBUTION.md points to it.
8. Domain layer additions:
   - `domains/defi/heuristics.md` (generic Krait heuristics) and `domains/defi/triggers.md` (domain module triggers);
   - the pack's `module-triggers.md` (pack modules + chain-specific trigger evidence);
   - the generic half of `erc4626-vault-deep.md` is named `vault-share-accounting.md`.
```

- [ ] **Step 9: Commit and push**

```bash
git add -A
git commit -m "Scaffold ChainSec plugin, structure lint and CI"
git push origin main
```

---

### Task 2: Shared script library and JSON schemas

**Files:**
- Create: `plugins/chainsec/skills/chainsec/scripts/_common.py`, `.../scripts/_schema.py`
- Create: `plugins/chainsec/skills/chainsec/engine/finding.schema.json`, `.../engine/facts.schema.json`, `.../engine/pack.schema.json`
- Test: `tests/test_common_schema.py`

**Interfaces:**
- Produces (`_common.py`):
  - `SEVERITY_ORDER = ["Critical","High","Medium","Low","Info"]`
  - `load_json(path)`, `write_json(path, data)` (creates parent dirs)
  - `glob_match(relpath: str, pattern: str) -> bool`, where `**/` matches zero or more directories and `*` never crosses `/`
  - `matches_any(relpath, patterns) -> bool`
- Produces (`_schema.py`): `load(path)` and `validate(instance, schema) -> list[str]`, where each error is `"<json path>: <message>"`. Supported keywords: `type` (string or list), `enum`, `required`, `properties`, `additionalProperties` (bool or schema), `items`, `minItems`, `minLength`, `minimum`, `$ref` (`#/$defs/<name>`).
- Produces the schemas used by every later task. Field names are exactly as below.

- [ ] **Step 1: Write the failing tests**

`tests/test_common_schema.py`:
```python
import os
import sys
import unittest

from helpers import CORE, SCRIPTS, load, valid_finding

sys.path.insert(0, SCRIPTS)
from _common import glob_match, matches_any  # noqa: E402
from _schema import validate  # noqa: E402

SCHEMAS = os.path.join(CORE, "engine")


class GlobTest(unittest.TestCase):
    def test_double_star_matches_zero_dirs(self):
        self.assertTrue(glob_match("src/A.sol", "src/**/*.sol"))
        self.assertTrue(glob_match("src/a/b/A.sol", "src/**/*.sol"))

    def test_leading_double_star(self):
        self.assertTrue(glob_match("test/A.sol", "**/test/**"))
        self.assertTrue(glob_match("pkg/test/x/A.sol", "**/test/**"))
        self.assertTrue(glob_match("A.t.sol", "**/*.t.sol"))

    def test_single_star_does_not_cross_dirs(self):
        self.assertFalse(glob_match("src/a/A.sol", "src/*.sol"))

    def test_matches_any(self):
        self.assertTrue(matches_any("lib/x/A.sol", ["src/**", "lib/**"]))
        self.assertFalse(matches_any("x/A.sol", []))


class SchemaEngineTest(unittest.TestCase):
    def test_type_and_required(self):
        s = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
        self.assertEqual(validate({"a": 1}, s), [])
        self.assertIn("$: missing required 'a'", validate({}, s))
        self.assertTrue(validate({"a": "x"}, s)[0].startswith("$.a: expected integer"))

    def test_bool_is_not_integer(self):
        self.assertTrue(validate(True, {"type": "integer"}))

    def test_enum_items_minitems_ref(self):
        s = {"$defs": {"sev": {"enum": ["High", "Low"]}},
             "type": "array", "minItems": 1, "items": {"$ref": "#/$defs/sev"}}
        self.assertEqual(validate(["High"], s), [])
        self.assertTrue(validate([], s))
        self.assertTrue(any("not in" in e for e in validate(["Mid"], s)))

    def test_additional_properties(self):
        closed = {"type": "object", "properties": {"a": {}}, "additionalProperties": False}
        self.assertIn("$: unexpected property 'b'", validate({"a": 1, "b": 2}, closed))
        typed = {"type": "object", "additionalProperties": {"type": "number"}}
        self.assertEqual(validate({"x": 1.5}, typed), [])
        self.assertTrue(validate({"x": "no"}, typed))


class ProjectSchemasTest(unittest.TestCase):
    def test_valid_finding_passes(self):
        self.assertEqual(validate(valid_finding(), load(os.path.join(SCHEMAS, "finding.schema.json"))), [])

    def test_finding_rejects_unknown_status(self):
        errs = validate(valid_finding(status="TP"), load(os.path.join(SCHEMAS, "finding.schema.json")))
        self.assertTrue(errs)

    def test_minimal_facts_pass(self):
        facts = {"chain": "solidity", "mode": "regex", "units": [], "entry_points": [], "auth_sites": [],
                 "storage_writes": [], "external_calls": [], "value_transfers": [],
                 "counters": {"src/A.sol": {"loc": 10, "external_calls": 1}}}
        self.assertEqual(validate(facts, load(os.path.join(SCHEMAS, "facts.schema.json"))), [])

    def test_pack_schema_requires_chain(self):
        errs = validate({}, load(os.path.join(SCHEMAS, "pack.schema.json")))
        self.assertIn("$: missing required 'chain'", errs)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_common_schema.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named '_common'`.

- [ ] **Step 3: Implement `_common.py`**

```python
"""Shared helpers for ChainSec scripts. Python 3 standard library only."""
import json
import os
import re

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Info"]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


_GLOB_CACHE = {}


def _translate(pattern):
    i, out = 0, []
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(relpath, pattern):
    """Match a /-separated relative path; ** spans directories, * does not."""
    rx = _GLOB_CACHE.get(pattern)
    if rx is None:
        rx = _GLOB_CACHE[pattern] = _translate(pattern)
    return bool(rx.match(relpath.replace(os.sep, "/")))


def matches_any(relpath, patterns):
    return any(glob_match(relpath, p) for p in patterns)
```

- [ ] **Step 4: Implement `_schema.py`**

```python
"""Minimal JSON Schema (draft 2020-12 subset) validator. Python 3 standard library only.

Supports: type, enum, required, properties, additionalProperties (bool or schema),
items, minItems, minLength, minimum, $ref ("#/$defs/<name>").
"""
import json

_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(instance, schema, root=None, path="$"):
    root = schema if root is None else root
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ValueError(f"unsupported $ref {ref}")
        return validate(instance, root["$defs"][ref[len("#/$defs/"):]], root, path)
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](instance) for x in types):
            return [f"{path}: expected {'|'.join(types)}, got {type(instance).__name__}"]
    errors = []
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str) and len(instance) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than {schema['minLength']}")
    if _TYPES["number"](instance) and "minimum" in schema and instance < schema["minimum"]:
        errors.append(f"{path}: below minimum {schema['minimum']}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], root, f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unexpected property '{key}'")
            elif isinstance(extra, dict):
                errors += validate(value, extra, root, f"{path}.{key}")
    return errors
```

- [ ] **Step 5: Write `engine/finding.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "chainsec/finding.schema.json",
  "title": "ChainSec finding (candidate files and verdict files are JSON arrays of these)",
  "type": "object",
  "required": ["id", "chain", "title", "severity", "category", "status", "locations", "description"],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "string", "minLength": 1 },
    "chain": { "type": "string", "minLength": 1 },
    "title": { "type": "string", "minLength": 1 },
    "severity": { "enum": ["Critical", "High", "Medium", "Low", "Info"] },
    "category": { "type": "string", "minLength": 1 },
    "status": { "enum": ["candidate", "verified", "verified-conditional", "downgraded", "killed"] },
    "locations": { "type": "array", "items": { "$ref": "#/$defs/location" } },
    "discovery": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "phase": { "enum": ["detect", "rescan", "per-unit", "state", "review"] },
        "lens": { "type": ["string", "null"] },
        "mindset": { "enum": ["attacker", "accountant", "spec-auditor", "edge-case", null] },
        "consensus": { "enum": ["strong", "moderate", "single", null] },
        "unit": { "type": ["string", "null"] }
      }
    },
    "description": { "type": "string", "minLength": 1 },
    "root_cause": { "type": "string" },
    "recommendation": { "type": "string" },
    "vulnerable_code": { "type": "string" },
    "harm": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "who": { "type": "string" },
        "loses_what": { "type": "string" },
        "magnitude": { "type": "string" }
      }
    },
    "exploit_trace": { "type": "array", "items": { "type": "string" } },
    "preconditions": { "type": "array", "items": { "$ref": "#/$defs/condition" } },
    "postconditions": { "type": "array", "items": { "$ref": "#/$defs/condition" } },
    "verdict": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "gate": { "type": ["string", "null"] },
        "reason": { "type": "string" },
        "evidence_tag": { "type": ["string", "null"] },
        "method": { "type": ["string", "null"] },
        "original_severity": { "enum": ["Critical", "High", "Medium", "Low", "Info", null] }
      }
    },
    "audit_trail": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "step_execution": { "type": "string" },
        "rules_applied": { "type": "array", "items": { "type": "string" } },
        "depth_evidence": { "type": "array", "items": { "type": "string" } },
        "missing_precondition": { "type": "string" },
        "postconditions_created": { "type": "array", "items": { "type": "string" } },
        "who_benefits": { "type": "string" }
      }
    },
    "boundary": { "type": "boolean" },
    "merged_from": { "type": "array", "items": { "type": "string" } }
  },
  "$defs": {
    "location": {
      "type": "object",
      "required": ["file"],
      "additionalProperties": false,
      "properties": {
        "file": { "type": "string", "minLength": 1 },
        "line_start": { "type": "integer", "minimum": 1 },
        "line_end": { "type": "integer", "minimum": 1 },
        "unit": { "type": "string" },
        "function": { "type": "string" }
      }
    },
    "condition": {
      "type": "object",
      "required": ["text", "type"],
      "additionalProperties": false,
      "properties": {
        "text": { "type": "string", "minLength": 1 },
        "type": { "enum": ["STATE", "ACCESS", "TIMING", "EXTERNAL", "BALANCE"] }
      }
    }
  }
}
```

- [ ] **Step 6: Write `engine/facts.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "chainsec/facts.schema.json",
  "title": "ChainSec code facts, written by a pack's extractor",
  "type": "object",
  "required": ["chain", "mode", "units", "entry_points", "auth_sites", "storage_writes", "external_calls", "value_transfers", "counters"],
  "properties": {
    "chain": { "type": "string", "minLength": 1 },
    "mode": { "enum": ["compiler", "regex"] },
    "root": { "type": "string" },
    "units": { "type": "array", "items": {
      "type": "object", "required": ["name", "file", "loc", "parents"],
      "properties": {
        "name": { "type": "string" }, "kind": { "type": "string" }, "file": { "type": "string" },
        "line": { "type": "integer" }, "loc": { "type": "integer", "minimum": 0 },
        "parents": { "type": "array", "items": { "type": "string" } } } } },
    "entry_points": { "type": "array", "items": {
      "type": "object", "required": ["unit", "name", "file", "line"],
      "properties": {
        "unit": { "type": "string" }, "name": { "type": "string" }, "file": { "type": "string" },
        "line": { "type": "integer" }, "visibility": { "type": "string" }, "mutability": { "type": "string" },
        "guards": { "type": "array", "items": { "type": "string" } } } } },
    "auth_sites": { "type": "array", "items": {
      "type": "object", "required": ["unit", "file", "line", "kind"],
      "properties": { "unit": { "type": "string" }, "file": { "type": "string" },
                      "line": { "type": "integer" }, "kind": { "type": "string" } } } },
    "storage_writes": { "type": "array", "items": {
      "type": "object", "required": ["unit", "function", "file", "line", "target"],
      "properties": { "unit": { "type": "string" }, "function": { "type": ["string", "null"] },
                      "file": { "type": "string" }, "line": { "type": "integer" }, "target": { "type": "string" } } } },
    "external_calls": { "type": "array", "items": {
      "type": "object", "required": ["unit", "function", "file", "line", "kind"],
      "properties": { "unit": { "type": "string" }, "function": { "type": ["string", "null"] },
                      "file": { "type": "string" }, "line": { "type": "integer" }, "kind": { "type": "string" } } } },
    "value_transfers": { "type": "array", "items": {
      "type": "object", "required": ["unit", "function", "file", "line", "asset"],
      "properties": { "unit": { "type": "string" }, "function": { "type": ["string", "null"] },
                      "file": { "type": "string" }, "line": { "type": "integer" },
                      "asset": { "enum": ["native", "token", "unknown"] } } } },
    "counters": { "type": "object", "additionalProperties": {
      "type": "object", "required": ["loc"], "additionalProperties": { "type": "number" } } }
  }
}
```

- [ ] **Step 7: Write `engine/pack.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "chainsec/pack.schema.json",
  "title": "ChainSec chain pack manifest (paths are relative to the pack folder)",
  "type": "object",
  "required": ["chain", "id_prefix", "extensions", "detect", "scope", "tools", "extractor", "risk_weights",
               "loc_weight", "novelty_bonus", "value_bonus", "novelty_allowlist", "unit_of_analysis",
               "clustering", "value_unit", "code_fence", "modules_by_protocol", "poc", "fuzz"],
  "additionalProperties": false,
  "properties": {
    "chain": { "type": "string", "minLength": 1 },
    "id_prefix": { "type": "string", "minLength": 1 },
    "extensions": { "type": "array", "minItems": 1, "items": { "type": "string" } },
    "detect": { "type": "object", "required": ["markers"], "additionalProperties": false, "properties": {
      "markers": { "type": "array", "items": { "type": "string" } },
      "contains": { "type": "array", "items": { "type": "string" } },
      "fallback_glob": { "type": "string" } } },
    "scope": { "type": "object", "required": ["include", "exclude"], "additionalProperties": false, "properties": {
      "include": { "type": "array", "minItems": 1, "items": { "type": "string" } },
      "exclude": { "type": "array", "items": { "type": "string" } },
      "fallback_include": { "type": "array", "items": { "type": "string" } } } },
    "tools": { "type": "object", "required": ["required", "optional"], "additionalProperties": false, "properties": {
      "required": { "type": "array", "items": { "$ref": "#/$defs/tool" } },
      "optional": { "type": "array", "items": { "$ref": "#/$defs/tool" } } } },
    "extractor": { "type": "string", "minLength": 1 },
    "analyzers": { "type": "array", "items": { "type": "object", "required": ["name", "run", "requires"],
      "additionalProperties": false, "properties": {
        "name": { "type": "string" }, "run": { "type": "string" }, "requires": { "type": "string" } } } },
    "risk_weights": { "type": "object", "additionalProperties": { "type": "number" } },
    "loc_weight": { "type": "number" },
    "novelty_bonus": { "type": "number" },
    "value_bonus": { "type": "number" },
    "novelty_allowlist": { "type": "array", "items": { "type": "string" } },
    "unit_of_analysis": { "type": "string" },
    "clustering": { "type": "string" },
    "value_unit": { "type": "object", "required": ["name", "decimals"], "additionalProperties": false, "properties": {
      "name": { "type": "string" }, "decimals": { "type": "integer", "minimum": 0 } } },
    "code_fence": { "type": "string" },
    "modules_by_protocol": { "type": "object", "additionalProperties": { "type": "array", "items": { "type": "string" } } },
    "poc": { "type": "object", "required": ["framework", "run", "guide"], "additionalProperties": false, "properties": {
      "framework": { "type": "string" }, "run": { "type": "string" }, "guide": { "type": "string" } } },
    "fuzz": { "type": "object", "required": ["framework", "run", "guide"], "additionalProperties": false, "properties": {
      "framework": { "type": "string" }, "run": { "type": "string" }, "guide": { "type": "string" } } }
  },
  "$defs": {
    "tool": { "type": "object", "required": ["name", "check", "install"], "additionalProperties": false, "properties": {
      "name": { "type": "string" }, "check": { "type": "string" }, "install": { "type": "string" },
      "purpose": { "type": "string" } } }
  }
}
```

- [ ] **Step 8: Run tests**

Run: `bash tests/run.sh`
Expected: lint 0 errors; all tests pass.

- [ ] **Step 9: Commit and push**

```bash
git add -A
git commit -m "Add script helpers, stdlib JSON Schema validator and engine schemas"
git push origin main
```

---

### Task 3: `validate-findings.py`

**Files:**
- Create: `plugins/chainsec/skills/chainsec/scripts/validate-findings.py`
- Test: `tests/test_validate_findings.py`

**Interfaces:**
- Consumes: `_common.load_json/write_json`, `_schema.validate`, `engine/finding.schema.json`.
- Produces: CLI `validate-findings.py <findings.json> [--schema PATH] [--downgrade]`.
  - stdout: a JSON list of `{"id", "rule", "detail"}`, where `rule` is one of `schema | location | harm | exploit_trace | input`.
  - Exit 0: no rejects, or `--downgrade` resolved all hard-rule rejects.
  - Exit 1: rejects remain.
  - Exit 2: bad input.
  - `--downgrade` rewrites the file in place. Each hard-rule reject becomes `status: "downgraded"`, `severity: "Low"`, with `verdict.original_severity` set and `verdict.reason` appended.

- [ ] **Step 1: Write the failing tests**

`tests/test_validate_findings.py`:
```python
import json
import unittest

from helpers import load, run_py, valid_finding, write_tmp_json


def check(findings, *flags):
    path = write_tmp_json(findings)
    r = run_py("validate-findings.py", path, *flags)
    return r, (json.loads(r.stdout) if r.stdout.strip() else None), path


class ValidateFindingsTest(unittest.TestCase):
    def test_valid(self):
        r, out, _ = check([valid_finding()])
        self.assertEqual((r.returncode, out), (0, []), r.stderr)

    def test_missing_line_on_verified_high(self):
        r, out, _ = check([valid_finding(locations=[{"file": "src/Vault.sol"}])])
        self.assertEqual(r.returncode, 1)
        self.assertEqual([x["rule"] for x in out], ["location"])

    def test_missing_harm(self):
        r, out, _ = check([valid_finding(harm={"who": " ", "loses_what": "funds"})])
        self.assertEqual([x["rule"] for x in out], ["harm"])

    def test_empty_trace(self):
        r, out, _ = check([valid_finding(exploit_trace=[])])
        self.assertEqual([x["rule"] for x in out], ["exploit_trace"])

    def test_rules_skip_candidates_and_low(self):
        r, out, _ = check([valid_finding(status="candidate", exploit_trace=[], harm={}),
                           valid_finding(id="SOL-002", severity="Low", exploit_trace=[])])
        self.assertEqual((r.returncode, out), (0, []))

    def test_schema_error(self):
        r, out, _ = check([valid_finding(severity="Severe")])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(out[0]["rule"], "schema")

    def test_top_level_must_be_array(self):
        r, out, _ = check(valid_finding())
        self.assertEqual(r.returncode, 2)

    def test_downgrade_rewrites_file(self):
        r, out, path = check([valid_finding(exploit_trace=[])], "--downgrade")
        self.assertEqual((r.returncode, out), (0, []), r.stdout)
        f = load(path)[0]
        self.assertEqual((f["status"], f["severity"]), ("downgraded", "Low"))
        self.assertEqual(f["verdict"]["original_severity"], "High")
        self.assertIn("exploit_trace", f["verdict"]["reason"])

    def test_downgrade_keeps_schema_errors(self):
        r, out, _ = check([valid_finding(severity="Severe")], "--downgrade")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_validate_findings.py' -v`
Expected: FAIL. Returncode 2 with "No such file" on stderr, because the script doesn't exist yet.

- [ ] **Step 3: Implement**

`plugins/chainsec/skills/chainsec/scripts/validate-findings.py`:
```python
#!/usr/bin/env python3
"""Validate ChainSec findings before the report.

Usage:
  validate-findings.py <findings.json> [--schema PATH] [--downgrade]

Prints a JSON list of rejects ({"id", "rule", "detail"}) to stdout.
Exit 0: no rejects (or --downgrade resolved them). Exit 1: rejects remain. Exit 2: bad input.

Hard rules apply to findings with status verified / verified-conditional and
severity Critical, High or Medium:
  location       at least one location with file and line_start
  harm           non-empty harm.who and harm.loses_what (the Impact Premise)
  exploit_trace  non-empty exploit_trace
With --downgrade, hard-rule rejects are rewritten in place to status "downgraded",
severity "Low", with the reason recorded. Schema errors are never auto-fixed.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import load_json, write_json  # noqa: E402
from _schema import validate  # noqa: E402

DEFAULT_SCHEMA = os.path.join(HERE, "..", "engine", "finding.schema.json")
ENFORCED_STATUS = {"verified", "verified-conditional"}
ENFORCED_SEVERITY = {"Critical", "High", "Medium"}


def hard_rule_failures(f):
    if f.get("status") not in ENFORCED_STATUS or f.get("severity") not in ENFORCED_SEVERITY:
        return []
    fails = []
    locs = f.get("locations") or []
    if not any(isinstance(l, dict) and l.get("file") and isinstance(l.get("line_start"), int)
               and l["line_start"] >= 1 for l in locs):
        fails.append(("location", "needs at least one location with file and line_start"))
    harm = f.get("harm") or {}
    if not (str(harm.get("who", "")).strip() and str(harm.get("loses_what", "")).strip()):
        fails.append(("harm", "needs harm.who and harm.loses_what (Impact Premise)"))
    if not [s for s in (f.get("exploit_trace") or []) if str(s).strip()]:
        fails.append(("exploit_trace", "needs a non-empty exploit_trace"))
    return fails


def check(findings, schema):
    rejects = []
    for i, f in enumerate(findings):
        fid = f.get("id", f"#{i}") if isinstance(f, dict) else f"#{i}"
        for err in validate(f, schema):
            rejects.append({"id": fid, "rule": "schema", "detail": err})
        if isinstance(f, dict):
            for rule, detail in hard_rule_failures(f):
                rejects.append({"id": fid, "rule": rule, "detail": detail})
    return rejects


def downgrade(findings, rejects):
    hard = {}
    for r in rejects:
        if r["rule"] != "schema":
            hard.setdefault(r["id"], []).append(r["rule"])
    for f in findings:
        rules = hard.get(f.get("id")) if isinstance(f, dict) else None
        if not rules:
            continue
        verdict = f.setdefault("verdict", {})
        verdict.setdefault("original_severity", f.get("severity"))
        f["status"] = "downgraded"
        f["severity"] = "Low"
        note = "auto-downgraded by validate-findings: missing " + ", ".join(rules)
        verdict["reason"] = f"{verdict.get('reason', '')} | {note}".strip(" |")
    return [r for r in rejects if r["rule"] == "schema"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate ChainSec findings")
    ap.add_argument("findings")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--downgrade", action="store_true")
    args = ap.parse_args(argv)
    try:
        findings = load_json(args.findings)
        schema = load_json(args.schema)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps([{"id": None, "rule": "input", "detail": str(e)}]))
        return 2
    if not isinstance(findings, list):
        print(json.dumps([{"id": None, "rule": "input", "detail": "top level must be a JSON array"}]))
        return 2
    rejects = check(findings, schema)
    if args.downgrade and rejects:
        rejects = downgrade(findings, rejects)
        write_json(args.findings, findings)
    print(json.dumps(rejects, indent=2))
    return 1 if rejects else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `bash tests/run.sh`
Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
git add -A
git commit -m "Add validate-findings: schema plus hard rules for verified H/M findings"
git push origin main
```

---

### Task 4: `score-risk.py`

**Files:**
- Create: `plugins/chainsec/skills/chainsec/scripts/score-risk.py`
- Test: `tests/test_score_risk.py`

**Interfaces:**
- Consumes: the facts shape (`counters`, `value_transfers`, `units`), and from the pack: `risk_weights`, `loc_weight`, `novelty_bonus`, `value_bonus`, `novelty_allowlist`.
- Produces: CLI `score-risk.py <facts.json> <pack.json> [-o risk.json]`. Output:
  ```
  {"chain", "mode", "size": "SMALL|MEDIUM|LARGE",
   "files": [{"file", "score", "tier": "DEEP|STANDARD|SCAN", "breakdown": {...}, "promoted"?: true}]}
  ```
  sorted by score descending, then file ascending.

- [ ] **Step 1: Write the failing tests**

`tests/test_score_risk.py`:
```python
import unittest

from helpers import load, run_py, write_tmp_json

PACK = {"risk_weights": {"external_calls": 5, "state_writers": 4}, "loc_weight": 0.05,
        "novelty_bonus": 15, "value_bonus": 10, "novelty_allowlist": ["lib/**"]}


def facts(counters, units=(), value_files=()):
    return {"chain": "solidity", "mode": "regex", "units": list(units), "entry_points": [], "auth_sites": [],
            "storage_writes": [], "external_calls": [],
            "value_transfers": [{"unit": "U", "function": "f", "file": f, "line": 1, "asset": "token"} for f in value_files],
            "counters": counters}


def score(f, pack=PACK):
    r = run_py("score-risk.py", write_tmp_json(f), write_tmp_json(pack))
    assert r.returncode == 0, r.stderr
    import json
    return json.loads(r.stdout)


class ScoreRiskTest(unittest.TestCase):
    def test_hand_computed_scores(self):
        out = score(facts({"src/A.sol": {"loc": 100, "external_calls": 2, "state_writers": 3},
                           "lib/B.sol": {"loc": 40, "external_calls": 0, "state_writers": 1}},
                          value_files=["src/A.sol"]))
        by = {r["file"]: r for r in out["files"]}
        self.assertEqual(by["src/A.sol"]["score"], 52.0)   # 10 + 12 + 5 + 15 + 10
        self.assertEqual(by["lib/B.sol"]["score"], 6.0)    # 0 + 4 + 2 + 0 + 0
        self.assertEqual([r["file"] for r in out["files"]], ["src/A.sol", "lib/B.sol"])
        self.assertEqual(out["size"], "SMALL")
        self.assertEqual({r["tier"] for r in out["files"]}, {"DEEP"})

    def test_tiers_and_parent_promotion(self):
        counters = {f"src/F{i:02d}.sol": {"loc": i * 100} for i in range(20)}
        units = [{"name": "Child", "file": "src/F19.sol", "loc": 1, "parents": ["Base"]},
                 {"name": "Base", "file": "src/F00.sol", "loc": 1, "parents": []}]
        out = score(facts(counters, units), {**PACK, "novelty_bonus": 0})
        tiers = [r["tier"] for r in out["files"]]
        self.assertEqual(tiers[:5], ["DEEP"] * 5)
        self.assertEqual(tiers[5:15], ["STANDARD"] * 10)
        self.assertEqual(tiers[15:19], ["SCAN"] * 4)
        last = out["files"][-1]
        self.assertEqual((last["file"], last["tier"], last.get("promoted")), ("src/F00.sol", "STANDARD", True))
        self.assertEqual(out["size"], "MEDIUM")

    def test_output_file(self):
        import os, tempfile
        dest = os.path.join(tempfile.mkdtemp(), "risk.json")
        r = run_py("score-risk.py", write_tmp_json(facts({"a.sol": {"loc": 1}})), write_tmp_json(PACK), "-o", dest)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(load(dest)["files"][0]["file"], "a.sol")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_score_risk.py' -v`
Expected: FAIL (AssertionError from `r.returncode == 0`, because the script is missing).

- [ ] **Step 3: Implement**

`plugins/chainsec/skills/chainsec/scripts/score-risk.py`:
```python
#!/usr/bin/env python3
"""Deterministic file risk scoring from facts.json and a pack's weights.

Usage: score-risk.py <facts.json> <pack.json> [-o risk.json]

score(file) = sum(counters[file][k] * risk_weights[k])
            + counters[file]["loc"] * loc_weight
            + novelty_bonus  if the file is not matched by novelty_allowlist
            + value_bonus    if the file has at least one value_transfers entry
Tiers: <= 15 files -> all DEEP; otherwise top 5 DEEP, next 10 STANDARD, rest SCAN.
Files holding a parent unit of a unit in a DEEP file are promoted to at least STANDARD.
Size: SMALL <= 15 files, MEDIUM <= 40, LARGE > 40.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import load_json, matches_any, write_json  # noqa: E402

TIER_RANK = {"SCAN": 0, "STANDARD": 1, "DEEP": 2}


def size_class(n):
    if n <= 15:
        return "SMALL"
    return "MEDIUM" if n <= 40 else "LARGE"


def score_files(facts, pack):
    weights = pack.get("risk_weights", {})
    allow = pack.get("novelty_allowlist", [])
    value_files = {v["file"] for v in facts.get("value_transfers", [])}
    rows = []
    for file, counters in facts.get("counters", {}).items():
        breakdown = {k: counters.get(k, 0) * w for k, w in weights.items()}
        breakdown["loc"] = counters.get("loc", 0) * pack.get("loc_weight", 0)
        breakdown["novelty"] = 0 if matches_any(file, allow) else pack.get("novelty_bonus", 0)
        breakdown["value"] = pack.get("value_bonus", 0) if file in value_files else 0
        breakdown = {k: round(v, 2) for k, v in breakdown.items()}
        rows.append({"file": file, "score": round(sum(breakdown.values()), 2), "breakdown": breakdown})
    rows.sort(key=lambda r: (-r["score"], r["file"]))
    return rows


def assign_tiers(rows, units):
    n = len(rows)
    for i, r in enumerate(rows):
        r["tier"] = "DEEP" if n <= 15 or i < 5 else ("STANDARD" if i < 15 else "SCAN")
    unit_file = {u["name"]: u["file"] for u in units}
    deep = {r["file"] for r in rows if r["tier"] == "DEEP"}
    promote = {unit_file[p] for u in units if u["file"] in deep for p in u.get("parents", []) if p in unit_file}
    for r in rows:
        if r["file"] in promote and TIER_RANK[r["tier"]] < TIER_RANK["STANDARD"]:
            r["tier"] = "STANDARD"
            r["promoted"] = True
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score file risk")
    ap.add_argument("facts")
    ap.add_argument("pack")
    ap.add_argument("-o", dest="out")
    args = ap.parse_args(argv)
    facts, pack = load_json(args.facts), load_json(args.pack)
    rows = assign_tiers(score_files(facts, pack), facts.get("units", []))
    result = {"chain": facts.get("chain"), "mode": facts.get("mode"), "size": size_class(len(rows)), "files": rows}
    if args.out:
        write_json(args.out, result)
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `bash tests/run.sh`
Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
git add -A
git commit -m "Add score-risk: pack-weighted deterministic file tiering"
git push origin main
```

---

### Task 5: `detect-chain.py`

**Files:**
- Create: `plugins/chainsec/skills/chainsec/scripts/detect-chain.py`
- Create fixtures:
  - `tests/fixtures/detect/chains/solidity/pack.json`
  - `tests/fixtures/detect/chains/cairo/pack.json`
  - `tests/fixtures/detect/sol-only/{foundry.toml,src/A.sol,lib/forge-std/foundry.toml}`
  - `tests/fixtures/detect/mixed/{evm/foundry.toml,evm/src/A.sol,starknet/Scarb.toml,starknet/src/lib.cairo,other/Scarb.toml}`
  - `tests/fixtures/detect/fallback/contracts/X.sol`
  - `tests/fixtures/detect/none/README.md`
- Test: `tests/test_detect_chain.py`

**Interfaces:**
- Consumes: from each pack, `chain` and `detect{markers, contains, fallback_glob}`.
- Produces: CLI `detect-chain.py [repo_root] [--chains-dir DIR] [-o chains.json]`, which writes `{"chains": [{"chain", "root"}]}`. `root` is relative to repo_root, with `"."` for the root itself. `--chains-dir` defaults to `<script dir>/../chains`.

- [ ] **Step 1: Create fixtures**

`tests/fixtures/detect/chains/solidity/pack.json`:
```json
{ "chain": "solidity", "detect": { "markers": ["foundry.toml", "hardhat.config.js", "hardhat.config.ts"], "contains": [], "fallback_glob": "**/*.sol" } }
```
`tests/fixtures/detect/chains/cairo/pack.json`:
```json
{ "chain": "cairo", "detect": { "markers": ["Scarb.toml"], "contains": ["starknet"] } }
```
File contents:
- `sol-only/foundry.toml`: `[profile.default]`
- `sol-only/src/A.sol`: `contract A {}`
- `sol-only/lib/forge-std/foundry.toml`: `[profile.default]`
- `mixed/evm/foundry.toml`: `[profile.default]`
- `mixed/evm/src/A.sol`: `contract A {}`
- `mixed/starknet/Scarb.toml`: `[dependencies]\nstarknet = "2.8.0"\n`
- `mixed/starknet/src/lib.cairo`: `mod a;`
- `mixed/other/Scarb.toml`: `[package]\nname = "plain"\n` (no `starknet`, so it must not match)
- `fallback/contracts/X.sol`: `contract X {}`
- `none/README.md`: `# nothing`

- [ ] **Step 2: Write the failing tests**

`tests/test_detect_chain.py`:
```python
import json
import os
import unittest

from helpers import FIXTURES, run_py

D = os.path.join(FIXTURES, "detect")


def detect(name):
    r = run_py("detect-chain.py", os.path.join(D, name), "--chains-dir", os.path.join(D, "chains"))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["chains"]


class DetectChainTest(unittest.TestCase):
    def test_solidity_only_ignores_lib(self):
        self.assertEqual(detect("sol-only"), [{"chain": "solidity", "root": "."}])

    def test_mixed_repo(self):
        self.assertEqual(detect("mixed"), [{"chain": "cairo", "root": "starknet"},
                                           {"chain": "solidity", "root": "evm"}])

    def test_fallback_glob(self):
        self.assertEqual(detect("fallback"), [{"chain": "solidity", "root": "."}])

    def test_nothing(self):
        self.assertEqual(detect("none"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_detect_chain.py' -v`
Expected: FAIL (the script is missing).

- [ ] **Step 4: Implement**

`plugins/chainsec/skills/chainsec/scripts/detect-chain.py`:
```python
#!/usr/bin/env python3
"""Detect which chain packs apply to a repository.

Usage: detect-chain.py [repo_root] [--chains-dir DIR] [-o chains.json]

For each <chains-dir>/*/pack.json:
  - a file whose basename matches detect.markers (and, when detect.contains is
    non-empty, whose text contains every listed string) marks its folder as a root;
  - nested roots collapse into the outermost one;
  - if no marker matched and detect.fallback_glob matches any file, "." is a root.
Vendored/build folders are skipped. Prints {"chains": [{"chain", "root"}, ...]}.
"""
import argparse
import fnmatch
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import glob_match, load_json, write_json  # noqa: E402

SKIP_DIRS = {".git", ".audit", "node_modules", "lib", "target", "out", "build",
             "artifacts", "cache", "dist", ".venv", "venv"}


def walk(repo):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel_dir = os.path.relpath(dirpath, repo).replace(os.sep, "/")
        for name in sorted(filenames):
            yield (name if rel_dir == "." else f"{rel_dir}/{name}"), name


def collapse(roots):
    kept = []
    for r in sorted(roots, key=lambda x: (0 if x == "." else x.count("/") + 1, x)):
        if not any(k == "." or r == k or r.startswith(k + "/") for k in kept):
            kept.append(r)
    return sorted(kept)


def detect(repo, chains_dir):
    files = list(walk(repo))
    found = []
    for pack_path in sorted(glob.glob(os.path.join(chains_dir, "*", "pack.json"))):
        pack = load_json(pack_path)
        det = pack.get("detect", {})
        markers, contains = det.get("markers", []), det.get("contains", [])
        roots = set()
        for rel, name in files:
            if not any(fnmatch.fnmatch(name, m) for m in markers):
                continue
            if contains:
                try:
                    with open(os.path.join(repo, rel), encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                if not all(c in text for c in contains):
                    continue
            roots.add(os.path.dirname(rel) or ".")
        fallback = det.get("fallback_glob")
        if not roots and fallback and any(glob_match(rel, fallback) for rel, _ in files):
            roots.add(".")
        found += [{"chain": pack["chain"], "root": r} for r in collapse(roots)]
    return {"chains": sorted(found, key=lambda c: (c["chain"], c["root"]))}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Detect chain packs for a repository")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--chains-dir", default=os.path.join(HERE, "..", "chains"))
    ap.add_argument("-o", dest="out")
    args = ap.parse_args(argv)
    result = detect(os.path.abspath(args.repo), os.path.abspath(args.chains_dir))
    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests**

Run: `bash tests/run.sh`
Expected: all pass.

- [ ] **Step 6: Commit and push**

```bash
git add -A
git commit -m "Add detect-chain: pack-driven chain and root detection"
git push origin main
```

---

### Task 6: `merge-findings.py`

**Files:**
- Create: `plugins/chainsec/skills/chainsec/scripts/merge-findings.py`
- Create fixtures: `tests/fixtures/merge/chains/solidity/pack.json`, `tests/fixtures/merge/chains/cairo/pack.json`
- Test: `tests/test_merge_findings.py`

**Interfaces:**
- Consumes: finding arrays, and from each pack, `chain` and `extensions`.
- Produces: CLI `merge-findings.py -o OUT [--chains-dir DIR] [--concat] IN...`.
  - Default mode: drop `killed`, dedup, tag `boundary`, rank.
  - `--concat`: concatenate only, keeping order and everything.

- [ ] **Step 1: Fixtures**

`tests/fixtures/merge/chains/solidity/pack.json`: `{"chain": "solidity", "extensions": [".sol"]}`
`tests/fixtures/merge/chains/cairo/pack.json`: `{"chain": "cairo", "extensions": [".cairo"]}`

- [ ] **Step 2: Write the failing tests**

`tests/test_merge_findings.py`:
```python
import os
import tempfile
import unittest

from helpers import FIXTURES, load, run_py, valid_finding, write_tmp_json

CHAINS = os.path.join(FIXTURES, "merge", "chains")


def merge(*lists, concat=False):
    out = os.path.join(tempfile.mkdtemp(), "merged.json")
    args = ["-o", out, "--chains-dir", CHAINS] + (["--concat"] if concat else [])
    r = run_py("merge-findings.py", *args, *[write_tmp_json(l) for l in lists])
    assert r.returncode == 0, r.stderr
    return load(out)


def loc(file, a, b):
    return [{"file": file, "line_start": a, "line_end": b}]


class MergeFindingsTest(unittest.TestCase):
    def test_dedup_keeps_more_severe(self):
        hi = valid_finding(id="SOL-001", severity="High", locations=loc("src/V.sol", 10, 20))
        med = valid_finding(id="SOL-009", severity="Medium", locations=loc("src/V.sol", 15, 16),
                            root_cause="  Missing ACCESS control on sweep ")
        out = merge([med], [hi])
        self.assertEqual([f["id"] for f in out], ["SOL-001"])
        self.assertEqual(out[0]["merged_from"], ["SOL-009"])

    def test_different_root_cause_not_merged(self):
        a = valid_finding(id="A", locations=loc("src/V.sol", 1, 5))
        b = valid_finding(id="B", locations=loc("src/V.sol", 1, 5), root_cause="rounding")
        self.assertEqual(len(merge([a, b])), 2)

    def test_killed_dropped_and_ranking(self):
        low = valid_finding(id="L", severity="Low", locations=loc("a.sol", 1, 1), root_cause="x")
        crit = valid_finding(id="C", severity="Critical", locations=loc("b.sol", 1, 1), root_cause="y")
        dead = valid_finding(id="K", status="killed", locations=loc("c.sol", 1, 1), root_cause="z")
        self.assertEqual([f["id"] for f in merge([low, dead, crit])], ["C", "L"])

    def test_boundary_tag(self):
        f = valid_finding(id="X", locations=loc("evm/Bridge.sol", 1, 2) + loc("starknet/src/bridge.cairo", 3, 4))
        self.assertTrue(merge([f])[0]["boundary"])
        self.assertNotIn("boundary", merge([valid_finding()])[0])

    def test_concat(self):
        a, b = valid_finding(id="A"), valid_finding(id="B", status="killed")
        self.assertEqual([f["id"] for f in merge([a], [b], concat=True)], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_merge_findings.py' -v`
Expected: FAIL (the script is missing).

- [ ] **Step 4: Implement**

`plugins/chainsec/skills/chainsec/scripts/merge-findings.py`:
```python
#!/usr/bin/env python3
"""Merge ChainSec finding arrays.

Usage: merge-findings.py -o OUT [--chains-dir DIR] [--concat] IN.json [IN.json ...]

Default mode (final cross-chain merge):
  - drops status "killed"
  - dedupes findings sharing a file with overlapping lines and the same normalized
    root_cause; keeps the most severe, records the others' ids in merged_from
  - sets boundary=true when a finding's location extensions map to 2+ chains
    (via each pack's "extensions")
  - ranks by severity, then consensus (strong > moderate > single > none), then id
--concat: concatenate inputs in order, nothing else (per-lens / per-unit outputs).
"""
import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import SEVERITY_ORDER, load_json, write_json  # noqa: E402

CONSENSUS_RANK = {"strong": 0, "moderate": 1, "single": 2}


def norm(text):
    return " ".join(str(text or "").lower().split())


def overlaps(a, b):
    if a.get("file") != b.get("file") or a.get("line_start") is None or b.get("line_start") is None:
        return False
    a1 = a.get("line_end") or a["line_start"]
    b1 = b.get("line_end") or b["line_start"]
    return a["line_start"] <= b1 and b["line_start"] <= a1


def same_issue(f, g):
    rc = norm(f.get("root_cause"))
    return bool(rc) and rc == norm(g.get("root_cause")) and any(
        overlaps(x, y) for x in f.get("locations", []) for y in g.get("locations", []))


def rank_key(f):
    sev = f.get("severity")
    return (SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else len(SEVERITY_ORDER),
            CONSENSUS_RANK.get((f.get("discovery") or {}).get("consensus"), 3), str(f.get("id")))


def extension_map(chains_dir):
    exts = {}
    for path in sorted(glob.glob(os.path.join(chains_dir, "*", "pack.json"))):
        pack = load_json(path)
        for ext in pack.get("extensions", []):
            exts[ext] = pack["chain"]
    return exts


def merge(lists, exts):
    pool = sorted((f for lst in lists for f in lst if f.get("status") != "killed"), key=rank_key)
    kept = []
    for f in pool:
        dup = next((k for k in kept if same_issue(k, f)), None)
        if dup is not None:
            dup.setdefault("merged_from", []).append(f["id"])
        else:
            kept.append(f)
    for f in kept:
        chains = {exts.get(os.path.splitext(l.get("file", ""))[1]) for l in f.get("locations", [])} - {None}
        if len(chains) >= 2:
            f["boundary"] = True
    return sorted(kept, key=rank_key)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge ChainSec findings")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--chains-dir", default=os.path.join(HERE, "..", "chains"))
    ap.add_argument("--concat", action="store_true")
    args = ap.parse_args(argv)
    lists = [load_json(p) for p in args.inputs]
    if args.concat:
        result = [f for lst in lists for f in lst]
    else:
        result = merge(lists, extension_map(args.chains_dir))
    write_json(args.out, result)
    print(f"{len(result)} findings -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests**

Run: `bash tests/run.sh`
Expected: all pass.

- [ ] **Step 6: Commit and push**

```bash
git add -A
git commit -m "Add merge-findings: cross-chain dedup, ranking, boundary tagging, concat"
git push origin main
```

---

### Task 7: Solidity facts extractor

**Files:**
- Create: `plugins/chainsec/skills/chainsec/chains/solidity/recon/extract.sh`, `.../recon/extract.py`
- Create: `plugins/chainsec/skills/chainsec/chains/solidity/pack.json`. It's needed here for `scope`, and the lint requires the referenced files. So this task writes only a **temporary** `tests/fixtures/solidity-pack-scope.json`, and the real `pack.json` lands in Task 9. The extractor takes `--pack`, and `extract.sh` defaults to `../pack.json`, so the test passes the fixture pack explicitly via the `CHAINSEC_PACK` env var.
- Create the fixture project `tests/fixtures/solidity-basic/`:
  - `foundry.toml`
  - `src/Base.sol`, `src/Vault.sol`
  - `test/VaultTest.sol`
  - `lib/dep/src/Dep.sol`
- Test: `tests/test_extract_solidity.py`

**Interfaces:**
- Consumes: `_common.load_json/write_json/matches_any`, `engine/facts.schema.json`.
- Produces:
  - `extract.sh <project-root> <facts.json>`. Env: `CHAINSEC_NO_COMPILE=1` forces regex mode, and `CHAINSEC_PACK=<path>` overrides the pack.
  - `extract.py --root DIR --pack PACK --out FACTS [--artifacts DIR --foundry-dir DIR]`.
  - Facts counters per file: `loc`, `external_calls`, `state_writers`, `payable`, `assembly_blocks`, `unchecked_blocks`.

- [ ] **Step 1: Create the fixture project**

`tests/fixtures/solidity-pack-scope.json`:
```json
{
  "scope": {
    "include": ["src/**/*.sol", "contracts/**/*.sol"],
    "exclude": ["**/test/**", "**/tests/**", "**/mock/**", "**/mocks/**", "**/script/**", "**/scripts/**",
                "**/lib/**", "**/node_modules/**", "**/out/**", "**/artifacts/**", "**/forge-std/**",
                "**/*.t.sol", "**/*.s.sol"],
    "fallback_include": ["**/*.sol"]
  }
}
```

`tests/fixtures/solidity-basic/foundry.toml`:
```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
```

`tests/fixtures/solidity-basic/src/Base.sol`:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

abstract contract Owned {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address next) external onlyOwner {
        owner = next;
    }
}
```

`tests/fixtures/solidity-basic/src/Vault.sol`:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Owned} from "./Base.sol";

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract Vault is Owned {
    IERC20 public immutable token;
    mapping(address => uint256) public balances;
    uint256 public totalDeposits;
    uint256 public constant FEE_BPS = 30;

    constructor(IERC20 token_) {
        token = token_;
    }

    function deposit(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
        totalDeposits += amount;
    }

    function depositEth() external payable {
        balances[msg.sender] += msg.value;
    }

    // BUG (planted for smoke tests): no access control, anyone can drain the native balance.
    function sweep(address payable to) external {
        to.transfer(address(this).balance);
    }

    function withdraw(uint256 amount) external {
        balances[msg.sender] -= amount;
        unchecked {
            totalDeposits -= amount;
        }
        token.transfer(msg.sender, amount);
    }

    function setFee(uint256) external onlyOwner {}

    function balanceOf(address who) external view returns (uint256) {
        return balances[who];
    }

    function _selfBalance() internal view returns (uint256 b) {
        assembly {
            b := selfbalance()
        }
    }
}
```

`tests/fixtures/solidity-basic/test/VaultTest.sol`:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VaultTest {
    function testNothing() external {}
}
```

`tests/fixtures/solidity-basic/lib/dep/src/Dep.sol`:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Dep {
    function x() external {}
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_extract_solidity.py`:
```python
import os
import shutil
import sys
import tempfile
import unittest

from helpers import CORE, FIXTURES, SCRIPTS, load, run

sys.path.insert(0, SCRIPTS)
from _schema import validate  # noqa: E402

EXTRACT = os.path.join(CORE, "chains", "solidity", "recon", "extract.sh")
PROJECT = os.path.join(FIXTURES, "solidity-basic")
PACK = os.path.join(FIXTURES, "solidity-pack-scope.json")


def extract(**env):
    out = os.path.join(tempfile.mkdtemp(), "facts.json")
    r = run(["bash", EXTRACT, PROJECT, out], env=dict(os.environ, CHAINSEC_PACK=PACK, **env))
    assert r.returncode == 0, r.stderr
    return load(out)


class Common:
    facts = None

    def test_schema(self):
        self.assertEqual(validate(self.facts, load(os.path.join(CORE, "engine", "facts.schema.json"))), [])

    def test_scope_excludes_tests_and_libs(self):
        self.assertEqual(sorted(self.facts["counters"]), ["src/Base.sol", "src/Vault.sol"])

    def test_units(self):
        units = {u["name"]: u for u in self.facts["units"]}
        self.assertEqual(set(units), {"Owned", "IERC20", "Vault"})
        self.assertEqual(units["Vault"]["parents"], ["Owned"])
        self.assertEqual(units["IERC20"]["kind"], "interface")

    def test_entry_points(self):
        eps = {(e["unit"], e["name"]) for e in self.facts["entry_points"]}
        self.assertEqual(eps, {("Owned", "transferOwnership"), ("Vault", "deposit"), ("Vault", "depositEth"),
                               ("Vault", "sweep"), ("Vault", "withdraw"), ("Vault", "setFee"), ("Vault", "balanceOf")})

    def test_counters(self):
        strip = lambda c: {k: v for k, v in c.items() if k != "loc"}
        self.assertEqual(strip(self.facts["counters"]["src/Vault.sol"]),
                         {"external_calls": 3, "state_writers": 5, "payable": 1, "assembly_blocks": 1, "unchecked_blocks": 1})
        self.assertEqual(strip(self.facts["counters"]["src/Base.sol"]),
                         {"external_calls": 0, "state_writers": 1, "payable": 0, "assembly_blocks": 0, "unchecked_blocks": 0})

    def test_storage_writes(self):
        writes = {(w["function"], w["target"]) for w in self.facts["storage_writes"]}
        self.assertEqual(writes, {("constructor", "owner"), ("transferOwnership", "owner"),
                                  ("deposit", "balances"), ("deposit", "totalDeposits"), ("depositEth", "balances"),
                                  ("withdraw", "balances"), ("withdraw", "totalDeposits")})

    def test_value_transfers(self):
        vt = {(v["function"], v["asset"]) for v in self.facts["value_transfers"]}
        self.assertEqual(vt, {("deposit", "token"), ("sweep", "native"), ("withdraw", "token")})

    def test_auth_sites(self):
        sites = sorted((a["unit"], a["kind"]) for a in self.facts["auth_sites"])
        self.assertEqual(sites, [("Owned", "inline"), ("Owned", "modifier:onlyOwner"), ("Vault", "modifier:onlyOwner")])


class RegexModeTest(Common, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = extract(CHAINSEC_NO_COMPILE="1")

    def test_mode(self):
        self.assertEqual(self.facts["mode"], "regex")


@unittest.skipUnless(shutil.which("forge"), "forge not installed")
class CompilerModeTest(Common, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = extract()

    def test_mode(self):
        self.assertEqual(self.facts["mode"], "compiler")

    def test_fixture_untouched(self):
        self.assertFalse(os.path.exists(os.path.join(PROJECT, "out")))
        self.assertFalse(os.path.exists(os.path.join(PROJECT, "cache")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_extract_solidity.py' -v`
Expected: ERROR in `setUpClass` (`extract.sh` not found, non-zero return).

- [ ] **Step 4: Implement `extract.sh`**

`plugins/chainsec/skills/chainsec/chains/solidity/recon/extract.sh`:
```bash
#!/usr/bin/env bash
# Solidity facts extractor. Usage: extract.sh <project-root> <facts.json>
# Tries `forge build --ast` into a temp dir (compiler mode); falls back to regex mode.
# Env: CHAINSEC_NO_COMPILE=1 forces regex mode; CHAINSEC_PACK overrides the pack manifest.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${1:-.}" && pwd)"
OUT="${2:-$ROOT/.audit/solidity/facts.json}"
PACK="${CHAINSEC_PACK:-$HERE/../pack.json}"
mkdir -p "$(dirname "$OUT")"
BUILD=""
cleanup() { if [ -n "$BUILD" ]; then rm -rf "$BUILD"; fi; }
trap cleanup EXIT
set -- --root "$ROOT" --pack "$PACK" --out "$OUT"
if [ "${CHAINSEC_NO_COMPILE:-0}" != "1" ] && command -v forge >/dev/null 2>&1; then
  TOML="$(find "$ROOT" -maxdepth 2 -name foundry.toml -not -path '*/lib/*' 2>/dev/null | head -1)"
  if [ -n "$TOML" ]; then
    FDIR="$(dirname "$TOML")"
    BUILD="$(mktemp -d)"
    if (cd "$FDIR" && forge build --ast --out "$BUILD/out" --cache-path "$BUILD/cache" >/dev/null 2>&1); then
      set -- "$@" --artifacts "$BUILD/out" --foundry-dir "$FDIR"
    else
      echo "forge build failed; using regex mode" >&2
    fi
  fi
fi
python3 "$HERE/extract.py" "$@"
```

- [ ] **Step 5: Implement `extract.py`**

`plugins/chainsec/skills/chainsec/chains/solidity/recon/extract.py`:
```python
#!/usr/bin/env python3
"""Solidity facts extractor for ChainSec.

Usage:
  extract.py --root DIR --pack PACK_JSON --out FACTS_JSON [--artifacts DIR --foundry-dir DIR]

With --artifacts (output of `forge build --ast`) facts come from the compiler AST
(mode "compiler"). Without it, or if any in-scope file lacks an AST, facts come
from regex over comment-stripped source (mode "regex").
Output conforms to engine/facts.schema.json.
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
from _common import load_json, matches_any, write_json  # noqa: E402

CALL_KINDS = ("call", "delegatecall", "staticcall", "send", "transfer", "transferFrom",
              "safeTransfer", "safeTransferFrom", "safeTransferETH")
TOKEN_KINDS = {"transferFrom", "safeTransfer", "safeTransferFrom"}
AUTH_CALLS = ("_checkOwner", "_checkRole", "hasRole")
SKIP_DIRS = {".git", ".audit", "node_modules", "out", "cache", "artifacts", "build"}
VIS = ("external", "public", "internal", "private")
MUT = ("pure", "view", "payable")


# ------------------------------------------------------------------ shared

def scope_files(root, scope):
    rels = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            rels.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    exclude = scope.get("exclude", [])
    for key in ("include", "fallback_include"):
        chosen = [r for r in rels if matches_any(r, scope.get(key, [])) and not matches_any(r, exclude)]
        if chosen:
            return chosen
    return []


def empty_facts(root, mode):
    return {"chain": "solidity", "mode": mode, "root": root, "units": [], "entry_points": [],
            "auth_sites": [], "storage_writes": [], "external_calls": [], "value_transfers": [],
            "counters": {}}


def new_counters(loc):
    return {"loc": loc, "external_calls": 0, "state_writers": 0, "payable": 0,
            "assembly_blocks": 0, "unchecked_blocks": 0}


def classify_value(kind, n_args, has_value_opt):
    if kind in ("send", "safeTransferETH") or (kind == "call" and has_value_opt):
        return "native"
    if kind == "transfer":
        return "native" if n_args == 1 else "token"
    if kind in TOKEN_KINDS:
        return "token"
    return None


# ------------------------------------------------------------------ regex mode

_STRIP = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)
UNIT_RE = re.compile(r'\b(abstract\s+contract|contract|library|interface)\s+([A-Za-z_]\w*)\s*(?:is\s+([^{]+?))?\s*\{')
FUNC_RE = re.compile(r'(?<![.\w])(?:function\s+([A-Za-z_]\w*)|(constructor|receive|fallback))\s*\(')
MOD_DEF_RE = re.compile(r'\bmodifier\s+([A-Za-z_]\w*)')
STATE_RE = re.compile(r'(?<![\w.])(?:mapping\s*\(.*?\)|[A-Za-z_][\w.]*(?:\s*\[[^\]]*\])*)\s+'
                      r'((?:(?:public|private|internal|constant|immutable|override|transient)\s+)*)'
                      r'([A-Za-z_]\w*)\s*(?:=[^;]*)?;', re.S)
CALL_RE = re.compile(r'\.\s*(' + "|".join(CALL_KINDS) + r')\s*(\{[^}]*\})?\s*\(')
AUTH_RE = re.compile(r'msg\.sender\s*[!=]=|[!=]=\s*msg\.sender|\b(?:' + "|".join(AUTH_CALLS) + r')\s*\(')
WRITE_OPS = r'(?:=(?!=)|\+=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=|\+\+|--)'


def strip_comments(src):
    def repl(m):
        s = m.group(0)
        return re.sub(r"[^\n]", " ", s) if s.startswith("/") else s
    return _STRIP.sub(repl, src)


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def match_close(text, open_idx, open_ch, close_ch):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def top_level_args(text, open_idx):
    inner = text[open_idx + 1:match_close(text, open_idx, "(", ")")]
    if not inner.strip():
        return 0
    depth, count = 0, 1
    for c in inner:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            count += 1
    return count


def drop_parens(text):
    prev = None
    while prev != text:
        prev, text = text, re.sub(r'\([^()]*\)', '', text)
    return text


def parse_header(rest):
    words = re.findall(r'[A-Za-z_]\w*', drop_parens(re.split(r'\breturns\b', rest)[0]))
    vis = next((w for w in words if w in VIS), None)
    mut = next((w for w in words if w in MUT), "nonpayable")
    mods = [w for w in words if w not in VIS and w not in MUT and w not in ("virtual", "override")]
    return vis, mut, mods


def regex_units(rel, text):
    units = []
    for m in UNIT_RE.finditer(text):
        open_idx = m.end() - 1
        close = match_close(text, open_idx, "{", "}")
        parents = [p.strip() for p in drop_parens(m.group(3) or "").split(",") if p.strip()]
        first = line_of(text, m.start())
        units.append({"name": m.group(2), "kind": "contract" if "contract" in m.group(1) else m.group(1),
                      "file": rel, "line": first, "loc": line_of(text, close) - first + 1, "parents": parents,
                      "_start": m.start(), "_open": open_idx, "_close": close})
    return units


def unit_at(units, pos):
    return next((u for u in units if u["_start"] <= pos <= u["_close"]), None)


def regex_state_vars(text, unit):
    body = text[unit["_open"] + 1:unit["_close"]]
    segments, depth, seg_start = [], 0, 0
    for i, c in enumerate(body):
        if c == "{":
            if depth == 0:
                segments.append(body[seg_start:i])
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                seg_start = i + 1
    segments.append(body[seg_start:] if depth == 0 else "")
    names = set()
    for seg in segments:
        for m in STATE_RE.finditer(seg):
            mods = m.group(1).split()
            if "constant" not in mods and "immutable" not in mods:
                names.add(m.group(2))
    return names


def regex_file(facts, rel, src, text, units, state_vars, parents_of):
    counters = new_counters(src.count("\n"))
    counters["assembly_blocks"] = len(re.findall(r'\bassembly\b[^{;]*\{', text))
    counters["unchecked_blocks"] = len(re.findall(r'\bunchecked\s*\{', text))
    regions = []
    for m in FUNC_RE.finditer(text):
        unit = unit_at(units, m.start())
        if unit is None:
            continue
        p_close = match_close(text, m.end() - 1, "(", ")")
        term = re.compile(r'[{;]').search(text, p_close + 1)
        vis, mut, mods = parse_header(text[p_close + 1:term.start() if term else len(text)])
        kind = "function" if m.group(1) else m.group(2)
        name = m.group(1) or m.group(2)
        if kind in ("receive", "fallback"):
            vis = vis or "external"
        vis = vis or "internal"
        has_body = bool(term) and text[term.start()] == "{"
        line = line_of(text, m.start())
        if has_body:
            regions.append({"unit": unit["name"], "name": name,
                            "body": (term.start(), match_close(text, term.start(), "{", "}"))})
        if mut == "payable":
            counters["payable"] += 1
        if kind != "constructor" and vis in ("external", "public") and has_body and unit["kind"] != "interface":
            facts["entry_points"].append({"unit": unit["name"], "name": name, "file": rel, "line": line,
                                          "visibility": vis, "mutability": mut, "guards": mods})
            if mut not in ("view", "pure"):
                counters["state_writers"] += 1
        for g in mods:
            if g.startswith("only"):
                facts["auth_sites"].append({"unit": unit["name"], "file": rel, "line": line, "kind": "modifier:" + g})
    for m in MOD_DEF_RE.finditer(text):
        unit = unit_at(units, m.start())
        brace = text.find("{", m.end())
        if unit is not None and brace >= 0:
            regions.append({"unit": unit["name"], "name": m.group(1),
                            "body": (brace, match_close(text, brace, "{", "}"))})

    def region_name(pos):
        return next((r["name"] for r in regions if r["body"][0] <= pos <= r["body"][1]), None)

    for m in AUTH_RE.finditer(text):
        unit = unit_at(units, m.start())
        if unit is not None:
            facts["auth_sites"].append({"unit": unit["name"], "file": rel, "line": line_of(text, m.start()), "kind": "inline"})
    for m in CALL_RE.finditer(text):
        unit = unit_at(units, m.start())
        if unit is None:
            continue
        kind = m.group(1)
        entry = {"unit": unit["name"], "function": region_name(m.start()), "file": rel,
                 "line": line_of(text, m.start()), "kind": kind}
        facts["external_calls"].append(entry)
        counters["external_calls"] += 1
        asset = classify_value(kind, top_level_args(text, m.end() - 1), bool(m.group(2) and "value" in m.group(2)))
        if asset:
            facts["value_transfers"].append(dict(entry, asset=asset))
    for unit in units:
        names, stack, seen = set(), [unit["name"]], set()
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                names |= state_vars.get(n, set())
                stack += parents_of.get(n, [])
        if not names:
            continue
        alt = "|".join(sorted(map(re.escape, names), key=len, reverse=True))
        patterns = [re.compile(r'(?<![\w.])(' + alt + r')\b\s*(?:\[[^\]]*\]\s*)*(?:\.\s*\w+\s*)*' + WRITE_OPS),
                    re.compile(r'(?:\+\+|--|\bdelete\s+)\s*(' + alt + r')\b')]
        written = set()
        for r in regions:
            if r["unit"] != unit["name"]:
                continue
            for pat in patterns:
                for m in pat.finditer(text, r["body"][0], r["body"][1]):
                    key = (r["name"], line_of(text, m.start()), m.group(1))
                    if key not in written:
                        written.add(key)
                        facts["storage_writes"].append({"unit": unit["name"], "function": key[0], "file": rel,
                                                        "line": key[1], "target": key[2]})
    facts["counters"][rel] = counters


def regex_extract(root, files):
    facts = empty_facts(root, "regex")
    parsed = []
    for rel in files:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        text = strip_comments(src)
        parsed.append((rel, src, text, regex_units(rel, text)))
    state_vars = {u["name"]: regex_state_vars(text, u) for _, _, text, units in parsed for u in units}
    parents_of = {u["name"]: u["parents"] for _, _, _, units in parsed for u in units}
    for rel, src, text, units in parsed:
        regex_file(facts, rel, src, text, units, state_vars, parents_of)
        facts["units"] += [{k: v for k, v in u.items() if not k.startswith("_")} for u in units]
    return facts


# ------------------------------------------------------------------ compiler mode

def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            if isinstance(v, (dict, list)):
                yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def load_asts(artifacts_dir, foundry_dir, root):
    asts = {}
    for path in sorted(glob.glob(os.path.join(artifacts_dir, "**", "*.json"), recursive=True)):
        try:
            data = load_json(path)
        except (OSError, ValueError):
            continue
        ast = data.get("ast") if isinstance(data, dict) else None
        if not isinstance(ast, dict) or ast.get("nodeType") != "SourceUnit":
            continue
        abs_path = ast.get("absolutePath", "")
        full = abs_path if os.path.isabs(abs_path) else os.path.join(foundry_dir, abs_path)
        asts.setdefault(os.path.relpath(os.path.normpath(full), root).replace(os.sep, "/"), ast)
    return asts


def base_identifier(expr):
    while isinstance(expr, dict):
        t = expr.get("nodeType")
        if t == "Identifier":
            return expr
        if t == "IndexAccess":
            expr = expr.get("baseExpression")
        elif t == "MemberAccess":
            expr = expr.get("expression")
        else:
            return None
    return None


def is_msg_sender(e):
    return (isinstance(e, dict) and e.get("nodeType") == "MemberAccess" and e.get("memberName") == "sender"
            and (e.get("expression") or {}).get("name") == "msg")


def compiler_extract(root, files, asts):
    facts = empty_facts(root, "compiler")
    state_ids = {}
    for rel in files:
        for node in walk(asts[rel]):
            if (node.get("nodeType") == "VariableDeclaration" and node.get("stateVariable")
                    and not node.get("constant") and node.get("mutability") not in ("immutable", "constant")):
                state_ids[node["id"]] = node["name"]
    for rel in files:
        with open(os.path.join(root, rel), "rb") as fh:
            src = fh.read()

        def line(node, _src=src):
            return _src.count(b"\n", 0, int(node["src"].split(":")[0])) + 1

        counters = new_counters(src.count(b"\n"))
        for node in walk(asts[rel]):
            if node.get("nodeType") == "InlineAssembly":
                counters["assembly_blocks"] += 1
            elif node.get("nodeType") == "UncheckedBlock":
                counters["unchecked_blocks"] += 1
        for contract in asts[rel].get("nodes", []):
            if contract.get("nodeType") != "ContractDefinition":
                continue
            cname, ckind = contract["name"], contract.get("contractKind", "contract")
            start, length = (int(x) for x in contract["src"].split(":")[:2])
            first = line(contract)
            parents = [(b.get("baseName") or {}).get("name") or (b.get("baseName") or {}).get("namePath", "")
                       for b in contract.get("baseContracts", [])]
            facts["units"].append({"name": cname, "kind": ckind, "file": rel, "line": first,
                                   "loc": src.count(b"\n", 0, start + length) + 1 - first + 1, "parents": parents})
            for member in contract.get("nodes", []):
                mt = member.get("nodeType")
                if mt == "FunctionDefinition":
                    kind = member.get("kind", "function")
                    fname = member.get("name") or kind
                    vis, mut = member.get("visibility"), member.get("stateMutability", "nonpayable")
                    guards = [(mi.get("modifierName") or {}).get("name", "") for mi in member.get("modifiers", [])]
                    if mut == "payable":
                        counters["payable"] += 1
                    if (kind != "constructor" and vis in ("external", "public") and member.get("implemented")
                            and ckind != "interface"):
                        facts["entry_points"].append({"unit": cname, "name": fname, "file": rel, "line": line(member),
                                                      "visibility": vis, "mutability": mut, "guards": guards})
                        if mut not in ("view", "pure"):
                            counters["state_writers"] += 1
                    for g in guards:
                        if g.startswith("only"):
                            facts["auth_sites"].append({"unit": cname, "file": rel, "line": line(member),
                                                        "kind": "modifier:" + g})
                elif mt == "ModifierDefinition":
                    fname = member.get("name")
                else:
                    continue
                if not member.get("body"):
                    continue
                written = set()
                for node in walk(member["body"]):
                    t = node.get("nodeType")
                    if t == "BinaryOperation" and node.get("operator") in ("==", "!=") and (
                            is_msg_sender(node.get("leftExpression")) or is_msg_sender(node.get("rightExpression"))):
                        facts["auth_sites"].append({"unit": cname, "file": rel, "line": line(node), "kind": "inline"})
                    elif t == "FunctionCall":
                        expr, opts = node.get("expression") or {}, []
                        if expr.get("nodeType") == "FunctionCallOptions":
                            opts, expr = expr.get("names", []), expr.get("expression") or {}
                        if expr.get("nodeType") == "Identifier" and expr.get("name") in AUTH_CALLS:
                            facts["auth_sites"].append({"unit": cname, "file": rel, "line": line(node), "kind": "inline"})
                        elif expr.get("nodeType") == "MemberAccess" and expr.get("memberName") in CALL_KINDS:
                            kind = expr["memberName"]
                            entry = {"unit": cname, "function": fname, "file": rel, "line": line(node), "kind": kind}
                            facts["external_calls"].append(entry)
                            counters["external_calls"] += 1
                            asset = classify_value(kind, len(node.get("arguments", [])), "value" in opts)
                            if asset:
                                facts["value_transfers"].append(dict(entry, asset=asset))
                    targets = []
                    if t == "Assignment":
                        lhs = node.get("leftHandSide") or {}
                        comps = lhs.get("components", []) if lhs.get("nodeType") == "TupleExpression" else [lhs]
                        targets = [base_identifier(c) for c in comps if c]
                    elif t == "UnaryOperation" and node.get("operator") in ("++", "--", "delete"):
                        targets = [base_identifier(node.get("subExpression"))]
                    for ident in targets:
                        ref = ident.get("referencedDeclaration") if ident else None
                        if ref in state_ids:
                            key = (fname, line(node), state_ids[ref])
                            if key not in written:
                                written.add(key)
                                facts["storage_writes"].append({"unit": cname, "function": fname, "file": rel,
                                                                "line": key[1], "target": key[2]})
        facts["counters"][rel] = counters
    return facts


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract Solidity facts")
    ap.add_argument("--root", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--artifacts")
    ap.add_argument("--foundry-dir")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    files = scope_files(root, load_json(args.pack)["scope"])
    facts = None
    if args.artifacts:
        asts = load_asts(args.artifacts, os.path.abspath(args.foundry_dir or root), root)
        if files and all(f in asts for f in files):
            facts = compiler_extract(root, files, asts)
    if facts is None:
        facts = regex_extract(root, files)
    write_json(args.out, facts)
    print(f"facts: {len(files)} files, mode={facts['mode']} -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run tests**

Run: `bash tests/run.sh`
Expected: all pass. On this machine (forge 1.7.1) `CompilerModeTest` runs too. In CI it is skipped.

If a compiler-mode assertion fails, debug before changing expectations. Inspect the AST with `forge build --ast --out /tmp/x` in the fixture, then `python3 -c "import json;print(json.load(open('/tmp/x/Vault.sol/Vault.json'))['ast']['nodes'][-1]['nodes'][0].keys())"`. The expectations encode real facts about the fixture. Use superpowers:systematic-debugging.

- [ ] **Step 7: Commit and push**

```bash
git add -A
git commit -m "Add Solidity facts extractor (compiler AST + regex fallback) with fixture tests"
git push origin main
```

---

### Task 8: DeFi domain layer + Solidity halves of mixed modules/primers

**Files:**
- Create in `plugins/chainsec/skills/chainsec/domains/defi/`:
  - `modules/`: `access-control-state.md`, `economic-design.md`, `multi-tx-attack.md`, `lending-liquidation-deep.md`, `amm-mev-deep.md`, `governance-voting.md`, `flash-loan-interaction.md`, `oracle-analysis.md`, `token-flow-tracing.md`, `external-protocol-integration.md`, `cross-chain-bridge.md`, `vault-share-accounting.md`
  - `primers/`: `defi-dex-amm.md`, `defi-lending.md`, `defi-staking-governance.md`, `gamefi-nft.md`, `bridge-crosschain.md`
  - `heuristics.md`, `triggers.md`, `README.md`
- Create in `plugins/chainsec/skills/chainsec/chains/solidity/`:
  - `modules/`: `oracle-analysis.md`, `token-flow-tracing.md`, `external-protocol-integration.md`, `cross-chain-bridge.md`, `erc4626-vault-deep.md`, `eip-standard-compliance.md`, `eip7702-delegation.md`, `account-abstraction-erc4337.md`
  - `primers/`: `proxy-upgrades.md`, `wallet-safe-aa.md`, plus a Solidity half for each domain primer that has Solidity-specific content (same file name)
- Create: `tests/fixtures/krait-ids.txt`, `tests/test_port_coverage.py`

**Interfaces:**
- Produces:
  - Domain module/primer file names, which Task 9's `pack.json` `modules_by_protocol` references.
  - `domains/defi/triggers.md`, with a table `| Module | Tier | Trigger (chain-agnostic) |`.
  - `domains/defi/heuristics.md`, which keeps Krait heuristic IDs verbatim.
  - `tests/fixtures/krait-ids.txt`, the ID snapshot every later port task must keep covered.

**Split rule (applies to every file in this task):**
- Read the Krait source file in full.
- Chain-agnostic content (economic reasoning, invariants, attack narratives, checklists phrased in protocol terms) goes to the `domains/defi/` file, **verbatim**.
- Content that names EVM/Solidity mechanics goes to the Solidity pack file with the same name, **verbatim**, under the same heading it had. That includes:
  - Solidity code blocks;
  - the `msg.sender` / `delegatecall` / `EXTCODESIZE` / `slot0` / `latestRoundData` / ERC-x API specifics;
  - OpenZeppelin, Solmate and Safe references;
  - forge commands.
- In the domain file, where text moved out, leave one line: `Chain-specific checks: see the pack's modules/<file>.md.` <!-- neutrality:allow --> (write it without naming a chain). If a whole file is pure Solidity, it moves entirely to the pack.
- In both files, replace `~/.claude/skills/krait/detector/modules/` references with core-relative paths (`domains/defi/modules/x.md` or `chains/solidity/modules/x.md`).
- The lint's neutrality check is the gate. Every banned term left in a domain file is either moved or, if genuinely generic in context (for example a sentence listing "Solidity, Cairo, Rust" as examples), marked with `<!-- neutrality:allow -->`. Prefer moving.

**Source → destination map:**

| Krait source | Domain file | Solidity pack file |
|---|---|---|
| `K/detector/modules/access-control-state.md` | `modules/access-control-state.md` | `modules/access-control-state.md` only if it has Solidity passages |
| `.../economic-design.md`, `multi-tx-attack.md`, `lending-liquidation-deep.md`, `amm-mev-deep.md`, `governance-voting.md`, `flash-loan-interaction.md` | same names | same names, only for moved passages |
| `.../oracle-analysis.md` | `modules/oracle-analysis.md` | `modules/oracle-analysis.md` (Chainlink `latestRoundData`, sequencer feed, Solidity snippets) |
| `.../token-flow-tracing.md` | `modules/token-flow-tracing.md` | `modules/token-flow-tracing.md` |
| `.../external-protocol-integration.md` | `modules/external-protocol-integration.md` | `modules/external-protocol-integration.md` |
| `.../cross-chain-bridge.md` | `modules/cross-chain-bridge.md` | `modules/cross-chain-bridge.md` (LayerZero/CCIP EVM APIs) |
| `.../erc4626-vault-deep.md` | `modules/vault-share-accounting.md` (share inflation, rounding direction, donation: concepts) | `modules/erc4626-vault-deep.md` (ERC-4626 API specifics) |
| `.../eip-standard-compliance.md`, `eip7702-delegation.md`, `account-abstraction-erc4337.md` | — | whole file |
| `K/detector/primers/defi-dex-amm.md`, `defi-lending.md`, `defi-staking-governance.md`, `gamefi-nft.md`, `bridge-crosschain.md` | same names under `primers/` | same names, for moved passages |
| `K/detector/primers/proxy-upgrades.md`, `wallet-safe-aa.md` | — | whole file |
| `K/detector/heuristics-core.md`: sections BL, ECON, MISSING, GOV, PR (and any other section whose heuristics are protocol-level) | `heuristics.md` | — (Solidity sections go to Task 9) |
| `K/recon/instructions.md` Step 6 table | `triggers.md`: rows for domain modules, with trigger conditions reworded only to drop code identifiers (the identifiers move to Task 9's `module-triggers.md`) | — |

`domains/defi/README.md`:
```markdown
# DeFi domain layer

Chain-agnostic DeFi knowledge shared by every chain pack. Engine phases load these files; each
pack adds chain-specific halves under `chains/<chain>/modules/` and `chains/<chain>/primers/`
with the same file names.

- `modules/` — deep-dive detection modules, selected during recon (see `domains/defi/triggers.md`).
- `primers/` — protocol-type priorities.
- `heuristics.md` — trigger-based heuristics that do not depend on the chain.
```

- [ ] **Step 1: Snapshot Krait IDs (the failing test's data)**

Run:
```bash
grep -rhoE '\b(BL|ECON|MISSING|GOV|PR|PRX|TS|MRV|ORC|SIG|ETH|TOK|C2|LOOP|CURVE|UNI|CHAINLINK|FP)-[0-9]{1,3}\b' \
  ~/krait/.claude/skills/krait/detector ~/krait/.claude/skills/krait/critic | sort -u > tests/fixtures/krait-ids.txt
wc -l tests/fixtures/krait-ids.txt
```
Expected: a non-empty list (dozens of IDs). Then open `K/detector/heuristics-core.md` and `K/detector/heuristics-extended.md` and check that every heuristic ID prefix used there is in the regex. If a prefix is missing, add it to the regex and re-run.

- [ ] **Step 2: Write the coverage test**

`tests/test_port_coverage.py`:
```python
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
```

Run: `python3 -m unittest discover -s tests -p 'test_port_coverage.py' -v`
Expected: FAIL, listing missing IDs.

This test stays red until Tasks 9–11 finish the port. To keep `tests/run.sh` green between tasks, mark it `@unittest.expectedFailure` now, and remove the decorator in Task 11 Step 9.

- [ ] **Step 3: Port the domain modules and the Solidity module halves**

Apply the split rule to every module row of the map. For each file: read the source, write the domain file, write the pack file (if any), then run `python3 tools/lint_skills.py` and fix what it reports before moving to the next file.

- [ ] **Step 4: Port primers**

Same procedure for the primer rows.

- [ ] **Step 5: Write `domains/defi/heuristics.md` and `domains/defi/triggers.md`**

- `heuristics.md`: header `# DeFi heuristics (chain-agnostic)`, one line of provenance ("Ported from Krait heuristics-core; IDs unchanged."), then the generic sections verbatim.
- `triggers.md`:
  - header `# Domain module triggers`;
  - the tier explanation from Krait recon Step 6 (Tier 0 always, Tier 1 protocol-type, Tier 2 feature-detected);
  - the selection rules (select all whose trigger is met, record trigger evidence);
  - the table limited to modules that live in `domains/defi/modules/`, using core-relative paths in the Module column (e.g. `` `domains/defi/modules/oracle-analysis.md` ``);
  - a final line: `Each pack's module-triggers.md adds its own modules and the code-level evidence strings for these triggers.`

- [ ] **Step 6: Run the full suite**

Run: `bash tests/run.sh`
Expected: lint 0 errors (neutrality clean, all backtick paths resolve), and all tests pass (coverage is an expected failure).

- [ ] **Step 7: Commit and push**

```bash
git add -A
git commit -m "Port DeFi modules and primers into a chain-agnostic domain layer plus Solidity halves"
git push origin main
```

---

### Task 9: Rest of the Solidity pack

**Files (all under `plugins/chainsec/skills/chainsec/chains/solidity/`):**
- Create: `pack.json`, `heuristics.md`, `fp-patterns.md`, `module-triggers.md`
- Create: `recon/clustering.md`, `recon/slither-summary.sh`
- Create: `poc/guide.md`, `poc/references/*.md`, `poc/ATTRIBUTION.md`
- Create: `fuzz/guide.md`
- Create: `patterns/schema.yaml`, `patterns/*.yaml`
- Modify: `plugins/chainsec/skills/chainsec/ATTRIBUTION.md` (turn the plain-text poc attribution reference into a link)
- Modify: `tests/test_extract_solidity.py` (use the real pack; delete `tests/fixtures/solidity-pack-scope.json`)
- Modify: `tests/test_detect_chain.py` (add a real-pack test)

**Interfaces:**
- Consumes: the Task 8 file names; the `pack.schema.json` fields.
- Produces: `pack.json` exactly as below, except that `modules_by_protocol` must list only files that exist after Task 8. The lint enforces this.

- [ ] **Step 1: Write `pack.json`**

```json
{
  "chain": "solidity",
  "id_prefix": "SOL",
  "extensions": [".sol"],
  "detect": {
    "markers": ["foundry.toml", "hardhat.config.js", "hardhat.config.ts", "truffle-config.js"],
    "contains": [],
    "fallback_glob": "**/*.sol"
  },
  "scope": {
    "include": ["src/**/*.sol", "contracts/**/*.sol"],
    "exclude": ["**/test/**", "**/tests/**", "**/mock/**", "**/mocks/**", "**/script/**", "**/scripts/**",
                "**/lib/**", "**/node_modules/**", "**/out/**", "**/artifacts/**", "**/forge-std/**",
                "**/*.t.sol", "**/*.s.sol"],
    "fallback_include": ["**/*.sol"]
  },
  "tools": {
    "required": [
      { "name": "python3", "check": "python3 --version", "install": "https://www.python.org/downloads/", "purpose": "ChainSec scripts" },
      { "name": "forge", "check": "forge --version", "install": "curl -L https://foundry.paradigm.xyz | bash && foundryup", "purpose": "compiler-mode facts, PoC, fuzz" }
    ],
    "optional": [
      { "name": "slither", "check": "slither --version", "install": "pipx install slither-analyzer", "purpose": "static-analysis signal table during recon" }
    ]
  },
  "extractor": "recon/extract.sh",
  "analyzers": [ { "name": "slither", "run": "recon/slither-summary.sh", "requires": "slither" } ],
  "risk_weights": { "external_calls": 5, "state_writers": 4, "payable": 4, "assembly_blocks": 6, "unchecked_blocks": 3 },
  "loc_weight": 0.05,
  "novelty_bonus": 15,
  "value_bonus": 10,
  "novelty_allowlist": ["**/openzeppelin*/**", "**/@openzeppelin/**", "**/solmate/**", "**/solady/**"],
  "unit_of_analysis": "inheritance_cluster",
  "clustering": "recon/clustering.md",
  "value_unit": { "name": "wei", "decimals": 18 },
  "code_fence": "solidity",
  "modules_by_protocol": {
    "always": ["../../domains/defi/modules/access-control-state.md"],
    "dex-amm": ["../../domains/defi/modules/amm-mev-deep.md", "../../domains/defi/modules/economic-design.md",
                "../../domains/defi/modules/flash-loan-interaction.md", "../../domains/defi/primers/defi-dex-amm.md"],
    "lending": ["../../domains/defi/modules/lending-liquidation-deep.md", "../../domains/defi/modules/oracle-analysis.md",
                "modules/oracle-analysis.md", "../../domains/defi/modules/economic-design.md",
                "../../domains/defi/primers/defi-lending.md"],
    "vault": ["../../domains/defi/modules/vault-share-accounting.md", "modules/erc4626-vault-deep.md",
              "../../domains/defi/modules/flash-loan-interaction.md"],
    "governance": ["../../domains/defi/modules/governance-voting.md", "../../domains/defi/primers/defi-staking-governance.md"],
    "staking": ["../../domains/defi/modules/economic-design.md", "../../domains/defi/primers/defi-staking-governance.md"],
    "nft-gamefi": ["../../domains/defi/primers/gamefi-nft.md", "modules/eip-standard-compliance.md"],
    "bridge": ["../../domains/defi/modules/cross-chain-bridge.md", "modules/cross-chain-bridge.md",
               "../../domains/defi/primers/bridge-crosschain.md"],
    "proxy-upgradeable": ["primers/proxy-upgrades.md"],
    "wallet-aa": ["primers/wallet-safe-aa.md", "modules/account-abstraction-erc4337.md", "modules/eip7702-delegation.md"]
  },
  "poc": { "framework": "foundry", "run": "forge test --match-test <test> -vvv", "guide": "poc/guide.md" },
  "fuzz": { "framework": "foundry-invariant", "run": "forge test --match-contract <contract> -vvv", "guide": "fuzz/guide.md" }
}
```

- [ ] **Step 2: Write `heuristics.md`**

Structure, all passages verbatim from Krait:
```
# Solidity heuristics
Ported from Krait (heuristics-core Solidity sections + heuristics-extended). IDs unchanged.
Load together with `domains/defi/heuristics.md`.

## Core heuristics (Solidity)        ← heuristics-core sections not moved to the domain in Task 8 (PRX, TS, MRV, ORC, SIG, ETH, TOK, C2, LOOP, CURVE/UNI/CHAINLINK…)
## Extended heuristics               ← all of heuristics-extended.md
## Lens D additions                  ← filled in Task 10 (mindsets)
## Detector modules (Solidity)       ← filled in Task 11 (detect)
## Recon additions                   ← filled in Task 11 (recon)
## Security strengths examples       ← filled in Task 11 (report)
```
Leave each "filled in Task N" section with the single line `(ported in a later task)`. Those tasks replace it.

- [ ] **Step 3: Write `fp-patterns.md`**

```
# Solidity false-positive patterns and gate overrides
## FP patterns            ← critic FP-3 (OpenZeppelin/Solmate), FP-7 (Solidity 0.8+ arithmetic incl. downcast exception), FP-8 (view/staticcall), verbatim
## Gate overrides and examples   ← filled in Task 10 (kill-gates): Gate A SafeERC20 / .transfer() gas examples
## Masking code examples  ← filled in Task 11 (state): try/catch, SafeMath
```

- [ ] **Step 4: Write `module-triggers.md`**

This is the Krait recon Step 6 table rows for the modules now in `chains/solidity/modules/`, verbatim. Then add a section `## Code evidence for domain module triggers`, which lists for each domain module the Solidity identifiers Krait used as evidence: `latestRoundData`, `convertToShares`, `balanceOf(address(this))`, `EXTCODESIZE`, `validateUserOp`, LayerZero/CCIP names, and so on, copied from the Step 6 "Select If..." column.

- [ ] **Step 5: `recon/clustering.md` and `recon/slither-summary.sh`**

- `clustering.md`:
  - title `# Solidity clustering: inheritance clusters`;
  - the cluster-building rules from `K/detector/per-contract.md` (build clusters from inheritance, max 8 clusters, ~1500 LOC, ≤ 5 findings per cluster, Tier-1 first), verbatim;
  - a paragraph mapping inputs: parents come from `facts.json` `units[].parents`, and LOC from `units[].loc`.
- `slither-summary.sh`: copy `K/recon/slither-summary.sh` verbatim, then add a first comment line after the shebang: `# Usage: slither-summary.sh <slither-json> <out.md>  (called during recon when slither is installed)`. Check the script's actual argument handling and make the usage line match it.

- [ ] **Step 6: PoC and fuzz material**

- `poc/guide.md`: the Foundry-specific parts of `KP/SKILL.md`, verbatim. That means environment/fork setup, `forge` commands and the harness usage. Drop the YAML frontmatter, which must not be a skill. Start the file with `# Solidity PoC guide (Foundry)` and one line: `Follow engine/poc/workflow.md; this file supplies the Foundry specifics.` The generic parts go to `engine/poc/workflow.md` in Task 10.
- `poc/references/`: copy the Foundry-specific references verbatim: `cheatsheet.md`, `debug-ladder.md`, `deploy-shapes.md`, `environment-recon.md`, `flashloan.md`, `fork-setup.md`, `harness.md`, `local-harness.md`, `reproduce-incident.md`. Fix any cross-links so the lint passes.
- `poc/ATTRIBUTION.md`: copy `KP/references/ATTRIBUTION.md` verbatim.
- `fuzz/guide.md`: from `K/fuzzer/SKILL.md`, take the "Test Generation Patterns" (Basic, Handler, Multi-Contract) and the "Iterative Fix Loop". Add the forge-specific pipeline steps from `~/krait/.claude/commands/krait-fuzz.md`. Start with `# Solidity fuzz guide (Foundry invariants)` and one line: `Follow engine/fuzz.md for invariant extraction; this file supplies the Foundry test patterns.` Replace output paths `.audit/invariant-tests/` with `.audit/solidity/fuzz/tests/`, and `.audit/krait-fuzz-report.md` with `.audit/solidity/fuzz/report.md`.
- `patterns/`: `cp ~/krait/patterns/schema.yaml ~/krait/patterns/solidity/*.yaml plugins/chainsec/skills/chainsec/chains/solidity/patterns/`
- In `plugins/chainsec/skills/chainsec/ATTRIBUTION.md`, make the PoC attribution reference a markdown link: `[chains/solidity/poc/ATTRIBUTION.md](chains/solidity/poc/ATTRIBUTION.md)`.

- [ ] **Step 7: Switch the extractor test to the real pack**

In `tests/test_extract_solidity.py`, change `PACK` to `os.path.join(CORE, "chains", "solidity", "pack.json")`. Then run `git rm tests/fixtures/solidity-pack-scope.json`.

- [ ] **Step 8: Add the real-pack detection test**

Append to `tests/test_detect_chain.py`, inside `DetectChainTest`:
```python
    def test_real_solidity_pack_detects_fixture(self):
        from helpers import FIXTURES as F
        r = run_py("detect-chain.py", os.path.join(F, "solidity-basic"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["chains"], [{"chain": "solidity", "root": "."}])
```

- [ ] **Step 9: Run and commit**

Run: `bash tests/run.sh`
Expected: lint 0 errors, with pack.json validated and every referenced file present. All tests pass.

```bash
git add -A
git commit -m "Add Solidity pack manifest, heuristics, FP patterns, triggers, PoC/fuzz guides and patterns"
git push origin main
```

---

### Task 10: Engine core documents

**Files (under `plugins/chainsec/skills/chainsec/engine/`):**
- Create: `verdicts.md`, `pipeline.md`, `kill-gates.md`, `mindsets.md`, `report-template.md`, `fuzz.md`
- Create: `poc/workflow.md`, `poc/assertion-protocol.md`, `poc/batch-triage.md`, `poc/falsification-gate.md`, `poc/fix-and-report.md`
- Modify: `chains/solidity/heuristics.md` ("Lens D additions"), `chains/solidity/fp-patterns.md` ("Gate overrides and examples")

**Interfaces:**
- Produces:
  - `pipeline.md`, which the entry skills follow, with sections `Inputs`, `Step 0 — Detect chains`, `Per chain`, `Validation and repair`, `After all chains`, `Dispatch`, `Failures`, `Final message`.
  - `kill-gates.md`, whose gate letters A–H plus `DoS exception` and `Impact Premise` headings are referenced by `phases/verify.md`.
  - `verdicts.md`, with evidence tags `[POC-PASS]`, `[POC-PASS · FIX-INSUFFICIENT]`, `[POC-UNPINNED]`, `[POC-FAIL]`, `[CODE-TRACE]`.

- [ ] **Step 1: Write `verdicts.md`** (new content)

```markdown
# Statuses, verdicts and evidence

Every finding carries exactly one `status` (see `engine/finding.schema.json`):

| status | Meaning | Reported? |
|---|---|---|
| `candidate` | Produced by a detection phase, not yet verified | No |
| `verified` | Exploitable; concrete exploit trace and harm statement present | Yes |
| `verified-conditional` | Mechanism confirmed but depends on stated conditions (listed in `preconditions`) | Yes |
| `downgraded` | Real issue, severity lowered (`verdict.original_severity` keeps the old one) | Yes, at the new severity |
| `killed` | Disproven, excluded by a kill gate, or insufficient evidence | No (reviewable by chainsec-review) |

`verdict.gate` records why a finding was killed: a gate letter `A`–`H`, `impact-premise`,
`fp-pattern:<id>`, or `insufficient-evidence`.

## Mapping from Krait's vocabularies

| Krait critic | Krait orchestrator | Krait reporter | ChainSec `status` |
|---|---|---|---|
| TRUE POSITIVE (TP) | VERIFIED | TRUE POSITIVE | `verified` |
| LIKELY TRUE (LT) | VERIFIED-CONDITIONAL | LIKELY TRUE | `verified-conditional` |
| DOWNGRADE | DOWNGRADE | — | `downgraded` |
| FALSE POSITIVE (FP) | KILLED | — | `killed` (gate = FP pattern or gate letter) |
| INSUFFICIENT EVIDENCE (IE) | KILLED | — | `killed` (gate = `insufficient-evidence`) |

## Evidence tags (`verdict.evidence_tag`)
```

Then append Krait's Evidence Tier table from `K/reporter/instructions.md` Step 2.75 **verbatim**, with its rules. Replace `krait-poc` with `chainsec-poc`.

- [ ] **Step 2: Write `kill-gates.md`** (ported)

Structure:
```
# Kill gates and the Impact Premise
Applied by the verify phase to every candidate, and as a pre-filter by detection phases.
Before applying gates, read the pack's fp-patterns.md, section "Gate overrides and examples".

## Step 0: Automatic kill gates        ← K/critic/instructions.md "Step 0: AUTOMATIC KILL GATE" verbatim (Gates A–H + DoS exception)
## Gate F in chain units               ← new paragraph (below)
## Step 0.5: Impact Premise            ← K/critic/instructions.md "Step 0.5" verbatim
## Detection pre-filter                ← K/detector/instructions.md "PRE-FILTER: Do NOT Generate Candidates For These" verbatim
```
New paragraph for "Gate F in chain units":
```markdown
Gate F thresholds are in USD. Convert on-chain amounts with the pack's `value_unit`
(`amount / 10^decimals` native units) and a price stated in `recon.md`; if recon recorded no
price, state the assumed price in `verdict.reason`.
```
Move the Solidity-specific examples inside the gates (SafeERC20, `.transfer()` 2300 gas, and any other Solidity API example) to `chains/solidity/fp-patterns.md` → "Gate overrides and examples", keyed by gate letter. In their place leave the gate's generic statement.

- [ ] **Step 3: Write `mindsets.md`** (ported)

Source: `K/detector/instructions.md` lines under "Step 1: Load Context" (the lens definitions "Lens A"–"Lens D", with their 4 mindset questions each), plus the Core Philosophy section. Title `# Lenses and mindsets`. Keep lens letters and the mindset tags `[Attacker]`, `[Accountant]`, `[Spec Auditor]`, `[Edge Case]`. Add a line mapping the tags to the schema enum: `attacker`, `accountant`, `spec-auditor`, `edge-case`. Move Lens D's Solidity items (EIP-712, `uint128` casts, `type(uint256).max`, and similar) to `chains/solidity/heuristics.md` → "Lens D additions", and leave `Plus the pack's heuristics.md "Lens D additions".` in their place.

- [ ] **Step 4: Write `report-template.md`** (ported)

Source: `K/reporter/instructions.md` Step 4 template, Step 5 findings index and "After Report: What's Next". Changes:
- Title becomes `# ChainSec Security Audit Report`.
- Finding headings become `### [<ID>] <Title> — <SEVERITY>`, where IDs are `<pack id_prefix>-NNN`.
- The code fence language is the pack's `code_fence`.
- The Zealynx web banner is removed. Krait credit is kept in a footer line: `Methodology derived from Krait by Zealynx Security.`
- "Security Strengths" examples (Ownable2Step, Solidity 0.8, SafeCast, OZ, UUPS) move to `chains/solidity/heuristics.md` → "Security strengths examples". The template says `examples: see the pack's heuristics.md "Security strengths examples"`.
- "What's Next" suggestions name `chainsec-review`, `chainsec-poc <ID>` and `chainsec-fuzz`.

Add a final section `## Combined report (multiple chains)`. It lists one summary table per chain, then all findings from `.audit/findings.json` in ranked order, then `## Boundary findings` listing every finding with `boundary: true`, then per-chain mode notes (compiler/regex, full/degraded, incomplete phases).

- [ ] **Step 5: Write `engine/poc/*` and `engine/fuzz.md`** (ported)

- `poc/workflow.md`: the chain-agnostic parts of `KP/SKILL.md`:
  - "assert harm, not mechanism";
  - the 9-step workflow, phrased without Foundry;
  - evidence tags;
  - triage lanes.
  Each Foundry step becomes `(pack: see the pack's poc guide, pack.json poc.guide)`.
  Output location: `.audit/<chain>/poc/<ID>/`. After a run, update the finding's `verdict.evidence_tag` in `.audit/<chain>/findings.json`.
- `poc/assertion-protocol.md`, `poc/batch-triage.md`, `poc/falsification-gate.md`, `poc/fix-and-report.md`: copy from `KP/references/`, then move any forge/cheatcode specifics into `chains/solidity/poc/references/<same name>.md` (append if it exists). The neutrality lint is the gate.
- `fuzz.md`: from `K/fuzzer/SKILL.md`, take Core Principle, Invariant Categories, Invariant Extraction Methodology Steps 1–5 and Priority Guidelines, verbatim. Replace any Solidity snippets with a pointer to the pack's fuzz guide. Outputs go to `.audit/<chain>/fuzz/invariants.md`, `.audit/<chain>/fuzz/tests/` and `.audit/<chain>/fuzz/report.md`.

- [ ] **Step 6: Write `pipeline.md`** (new content, exactly)

````markdown
# ChainSec pipeline

All paths in this file are relative to the core skill folder (CORE). `<chain>` is a pack name,
`A` = `TARGET/.audit/<chain>/`, `P` = `chains/<chain>/`.

## Inputs
- `TARGET`: directory being audited (default: the current working directory). Make it absolute.
- Flags: `--quick` (skip per-unit and state phases), `--chain <name>`, `--fresh` (discard previous state).
- `CORE`: absolute path of the core skill folder (the entry skill resolved it).

## Step 0 — Detect chains
Run `python3 CORE/scripts/detect-chain.py TARGET -o TARGET/.audit/chains.json`.
- With `--chain X`: keep only entries for X; if none remain, use `[{"chain": "X", "root": "."}]`
  and confirm `chains/<X>/pack.json` exists (otherwise stop: unsupported chain).
- Empty list: stop with "No supported chain detected. Supported packs: <folders in chains/>".

## Per chain
Process chains one after another. For each: `ROOT = TARGET/<root>`, `A = TARGET/.audit/<chain>`.
With `--fresh`, delete `A` first. **Resume:** skip a phase whose output already exists (JSON outputs
must also parse and, for findings files, pass `scripts/validate-findings.py` schema checks); say
`resumed: <phase>`.

| # | Phase | How | Output |
|---|---|---|---|
| 1 | preflight | follow `engine/phases/preflight.md` (gate mode) | `A/preflight.json` |
| 2 | extract | `bash CORE/P/<pack.extractor> ROOT A/facts.json` | `A/facts.json` |
| 3 | score | `python3 CORE/scripts/score-risk.py A/facts.json CORE/P/pack.json -o A/risk.json` | `A/risk.json` |
| 4 | recon | follow `engine/phases/recon.md` | `A/recon.md`, `A/known-issues.md` |
| 5 | detect | **parallel**: one subagent per lens A, B, C, D using `prompts/lens-detector.md`, each writing `A/candidates/detect-<lens>.json`; then follow the "Consensus merge" section of `engine/phases/detect.md` | `A/candidates/detect.json` |
| 6 | rescan | one subagent, `prompts/rescan.md` | `A/candidates/rescan.json` |
| 7 | per-unit (skip if `--quick`) | build clusters per `engine/phases/per-unit.md`; **parallel**: one subagent per cluster (max 8), `prompts/per-unit.md`, each writing `A/candidates/per-unit-<n>.json`; then `python3 CORE/scripts/merge-findings.py --concat -o A/candidates/per-unit.json A/candidates/per-unit-*.json` | `A/candidates/per-unit.json` |
| 8 | state (skip if `--quick`) | one subagent, `prompts/state-auditor.md` | `A/candidates/state.json` |
| 9 | verify | one subagent, `prompts/critic.md` | `A/verdicts.json` |
| 10 | validate | see "Validation and repair" | `A/verdicts.json` passes |
| 11 | report | one subagent, `prompts/reporter.md` | `A/report.md`, `A/findings.json` |

## Validation and repair
1. `python3 CORE/scripts/validate-findings.py A/verdicts.json`. Exit 0 → continue.
2. Exit 1 → run the "Repair pass" section of `engine/phases/verify.md` on the listed ids (edit
   `A/verdicts.json` in place), then re-run step 1.
3. Still exit 1 → `python3 CORE/scripts/validate-findings.py A/verdicts.json --downgrade`.
4. Still exit 1 (schema errors) → fix the JSON mechanically once more; if it still fails, mark the
   chain's report phase `incomplete` and continue with the next chain.

## After all chains
Run `python3 CORE/scripts/merge-findings.py -o TARGET/.audit/findings.json TARGET/.audit/*/findings.json`
(only chains that produced one). If one chain ran, copy `A/report.md` to `TARGET/.audit/report.md`;
otherwise write `TARGET/.audit/report.md` following "Combined report" in `engine/report-template.md`.

## Dispatch
Work out your runtime from the subagent tool you have, then read the matching file and follow it
for every **parallel** or **one subagent** row:

| You have | Runtime file |
|---|---|
| `Agent` or `Task` tool (Claude Code) | `runtimes/claude-code.md` |
| `task` or `subagent` tool (OpenCode) | `runtimes/opencode.md` |
| a Codex sub-agent tool | `runtimes/codex.md` |
| `invoke_subagent` (Antigravity) | `runtimes/antigravity.md` |
| none of these, or unsure | `runtimes/generic.md` (sequential, in this conversation) |

Fill prompt templates by replacing `{{CORE}}`, `{{CHAIN}}`, `{{ROOT}}`, `{{A}}`, `{{OUTPUT}}`
and the template-specific placeholders with absolute paths/values. Pass paths, never file contents.
After each subagent returns, confirm its output file exists and parses as JSON
(`python3 -c "import json,sys; json.load(open(sys.argv[1]))" <file>`).

## Failures
| Failure | Do |
|---|---|
| Required tool missing | preflight stops the chain; print the pack's install command |
| Optional tool missing | continue; `preflight.json` mode `degraded`; say so in the report |
| Extractor fails | it falls back to regex mode itself; if it exits non-zero, stop the chain and show stderr |
| Subagent output missing/invalid | re-run that unit once sequentially in this conversation; if still bad, record the phase as `incomplete` in `A/preflight.json` → `incomplete_phases` and continue |
| Validation still failing | see "Validation and repair" step 4 |

## Final message
Report: chains audited; per chain the facts mode (`compiler`/`regex`), preflight mode
(`full`/`degraded`) and incomplete phases; finding counts by severity; the path
`TARGET/.audit/report.md`; next steps `chainsec-review`, `chainsec-poc <ID>`, `chainsec-fuzz`.
````

- [ ] **Step 7: Create stubs for files referenced ahead of time**

`pipeline.md` references phase, prompt and runtime files that Tasks 11–12 write. Create each as a one-line stub `# <name> (in progress)` so every path resolves now:
- `engine/phases/{preflight,recon,detect,rescan,per-unit,state,verify,review,report}.md`
- `prompts/{lens-detector,rescan,per-unit,state-auditor,critic,reviewer,reporter}.md`
- `runtimes/{claude-code,opencode,codex,antigravity,generic}.md`

- [ ] **Step 8: Run and commit**

Run: `bash tests/run.sh`
Expected: lint 0 errors, all tests pass (coverage is still an expected failure).

```bash
git add -A
git commit -m "Add engine core: pipeline, verdicts, kill gates, mindsets, report template, PoC and fuzz method"
git push origin main
```

---

### Task 11: Engine phase files

**Files (under `plugins/chainsec/skills/chainsec/engine/phases/`):**
- Create (replacing stubs): `preflight.md`, `recon.md`, `detect.md`, `rescan.md`, `per-unit.md`, `state.md`, `verify.md`, `review.md`, `report.md`
- Modify: `chains/solidity/heuristics.md` ("Detector modules (Solidity)", "Recon additions", "Security strengths examples" if not done), `chains/solidity/fp-patterns.md` ("Masking code examples")
- Modify: `tests/test_port_coverage.py` (remove `@unittest.expectedFailure`)

**Common port rules for every phase file:**
1. **Header block.** Replace Krait's "Trigger" and "Prerequisites" sections with two lines: `Reads:` (the exact `A/...` files) and `Writes:` (exact `A/...` files), copied from the `pipeline.md` table.
2. **Output format.** Every markdown candidate/verdict template becomes: "Write a JSON array to `<file>`; each element conforms to `engine/finding.schema.json`." Then show one complete JSON example element. Map Krait candidate fields as follows:

   | Krait field | Schema field |
   |---|---|
   | Severity | `severity` |
   | File / Lines | `locations[]` |
   | Category | `category` |
   | Discovery Method | `discovery` |
   | Description | `description` |
   | Scenario | `exploit_trace` |
   | Vulnerable Code | `vulnerable_code` |
   | Why This Is a Bug | `root_cause` |
   | consensus | `discovery.consensus` |
   | Status | `status` |
   | Harm | `harm` |
   | Verification Method | `verdict.method` |
   | Proof | `exploit_trace` |
   | evidence tag | `verdict.evidence_tag` |
   | Missing Precondition | `preconditions` + `audit_trail.missing_precondition` |
   | Postconditions Created | `postconditions` + `audit_trail.postconditions_created` |
   | Who Benefits | `audit_trail.who_benefits` |
   | Step Execution | `audit_trail.step_execution` |
   | Rules Applied | `audit_trail.rules_applied` |
   | Depth Evidence | `audit_trail.depth_evidence` |

   Candidate IDs:
   - detect: `D<lens>-<n>`
   - rescan: `RS-<n>`
   - per-unit: `PC<cluster>-<n>`
   - state: `STATE-<n>`
   - review: `RV-<n>`

   The reporter assigns final IDs `<id_prefix>-NNN`.
3. **Paths.** `.audit/findings/*.md` and `.audit/*.md` become the `A/...` paths from `pipeline.md`, and `ast-facts.md` becomes `A/facts.json` (name the fields used). `~/.claude/skills/krait/...` becomes core-relative paths.
4. **Verdict names.** Use `engine/verdicts.md` only.
5. **Chain-specific passages.** Move them to the Solidity pack file named in the per-file notes, and leave a pointer sentence that doesn't name the chain.
6. **Everything else stays verbatim.** That covers questions Q1–Q9, pass strategy, anti-anchoring, gates, rules and quality gates.

- [ ] **Step 1: `preflight.md`** ← `K/preflight/instructions.md`
  - Keep: Modes (gate/report) and the Hard vs soft concept.
  - Hard checks: every `pack.json` `tools.required` entry (run its `check`), and ≥ 1 source file with a pack `extensions` suffix under ROOT (use `find ROOT -type f -name '*<ext>' -not -path '*/node_modules/*' -not -path '*/lib/*' -not -path '*/target/*' | head -20`).
  - Soft checks: `tools.optional`; the core folder being reachable; `.audit/` present in `.gitignore`.
  - Drop Krait's Step 4 (MCP wiring) and Step 5 (`~/.claude` sync). Mention the drop in one line under "Non-goals".
  - Output is `A/preflight.json`:
    ```json
    {"chain":"solidity","mode":"full","tools":{"forge":"OK forge 1.7.1","slither":"MISSING"},"scope_files":12,"warnings":[],"incomplete_phases":[]}
    ```
    Report mode prints the Krait summary table built from these fields.
  - Install hints come from `pack.json` `install`.

- [ ] **Step 2: `recon.md`** ← `K/recon/instructions.md` + the `~/krait/.claude/commands/krait.md` Phase 0 notes
  - Step 1: keep.
  - Step 2 becomes "Read `A/facts.json`. If `mode` is `regex`, note lower confidence in recon.md". List which facts fields feed which recon sections.
  - Step 2b becomes "For each `pack.json` `analyzers` entry whose `requires` tool is OK in preflight, run it and write `A/analyzers/<name>.md`; signal only, never auto-reported".
  - Step 3 scoring becomes "Read `A/risk.json`; copy tiers into the File Risk Table; judge immaturity (+10, Krait's rule, verbatim) and record adjustments". The formula text moves to a note: "Weights come from pack.json; see `scripts/score-risk.py`".
  - Steps 3a–3e, 3b, 3c and 4: keep. Solidity recipients (ERC-2981, onERC721Received) move to the pack's "Recon additions".
  - Step 3e "Inheritance & Import Graph" becomes "Unit graph: `facts.units[].parents`; cluster strategy per the pack's clustering file".
  - Step 5: keep the protocol-type list. Chainlink/Uniswap integration checklists move to the pack's "Recon additions". Protocol types must use the `modules_by_protocol` keys (`dex-amm`, `lending`, `vault`, `governance`, `staking`, `nft-gamefi`, `bridge`, `proxy-upgradeable`, `wallet-aa`).
  - Step 6 becomes: "Select modules: always `modules_by_protocol.always`; the lists for each protocol type chosen in Step 5; plus any module whose trigger fires per `domains/defi/triggers.md` and the pack's `module-triggers.md`. Record trigger evidence."
  - The output template (recon.md sections) is kept. The "Activated Modules" list uses core-relative paths.

- [ ] **Step 3: `detect.md`** ← `K/detector/instructions.md` + `krait.md` Phase 1
  - Sections:
    - `## Lens run`: what one lens subagent does. This is Steps 2–6 restricted to its lens, plus the Adaptive Pass Strategy for its tier files, using `A/risk.json` tiers and `size`.
    - `## Consensus merge`: the orchestrator combines `detect-A..D.json` into `detect.json`, sets `discovery.consensus` by how many lenses reported the same root cause at overlapping lines (3+ strong, 2 moderate, 1 single), and keeps the richest description.
    - `## Pass 3 sweep`: Krait's mechanical "What's Missing" sweep; its results are appended to `detect.json`.
  - Modules B (type cast), F (token compatibility) and G (factory/CREATE2) move to the pack's "Detector modules (Solidity)". Module O's `owner()`/`ownerOf` example also moves there. Q6.3 (ERC20 returns false) moves there under "Question additions".
  - PRE-FILTER becomes "Apply the Detection pre-filter in `engine/kill-gates.md`".
  - Load heuristics from `domains/defi/heuristics.md` plus the pack's `heuristics.md`.
  - The "Track OZ/Solmate" instruction moves to the pack.
  - The ```` ```solidity ```` candidate fence becomes `vulnerable_code` plus the note "use the pack's code_fence when rendering".

- [ ] **Step 4: `rescan.md`** ← `K/detector/rescan.md`
  - Replace the SafeERC20 example with a generic one ("a safe-transfer wrapper").
  - Output: `A/candidates/rescan.json`.

- [ ] **Step 5: `per-unit.md`** ← `K/detector/per-contract.md`
  - "Contract" becomes "unit"; cluster construction follows the pack's clustering file.
  - The orchestrator section says how to write `A/clusters.json`: `[{"n":1,"units":["Vault","Owned"],"files":[...]}]`.
  - Per-cluster output: `A/candidates/per-unit-<n>.json`.

- [ ] **Step 6: `state.md`** ← `K/state-auditor/instructions.md`
  - The masking examples (try/catch, SafeMath) move to the pack's `fp-patterns.md` "Masking code examples", with a pointer left behind.
  - Keep Phases 1–8 verbatim. Keep the state-auditor extra fields (Coupled Pair, Breaking Operation, Invariant, Masking Code, Cross-Feed) inside `description` as labeled lines, and the invariant in `root_cause`.

- [ ] **Step 7: `verify.md`** ← `K/critic/instructions.md` + `krait.md` Phase 3
  - Step 0 becomes "Apply `engine/kill-gates.md` Step 0". Step 0.5 becomes "Apply `engine/kill-gates.md` Step 0.5". Keep Consensus-Aware Verification, Methods A–C and the Verification Checklist verbatim.
  - Method D becomes "Executable PoC: optional escalation via the `chainsec-poc` skill using the pack's PoC guide".
  - FP-1, 2, 4, 5, 6, 9 and 10 stay. FP-3, 7 and 8 are already in the pack's `fp-patterns.md` (Task 9). Leave "FP-3, FP-7, FP-8: see the pack's fp-patterns.md".
  - Cross-Feed stays (max 2 cycles). The Verdict Format becomes the status mapping from `engine/verdicts.md`.
  - Output: `A/verdicts.json`, containing **all** candidates with final status (killed ones included, with `verdict.gate`).
  - Add a new final section:
    ```markdown
    ## Repair pass
    Input: the reject list printed by `scripts/validate-findings.py`. For each rejected id, re-open the
    code and either supply the missing field (a `file` + `line_start` location, a one-sentence
    `harm.who`/`harm.loses_what`, or a concrete step-by-step `exploit_trace`) or, if you cannot,
    lower the finding's status/severity per the Impact Premise. Edit `A/verdicts.json` in place.
    Never invent line numbers or traces you did not verify in the code.
    ```

- [ ] **Step 8: `review.md` and `report.md`**
  - `review.md` ← `K/reviewer/instructions.md`. Input is the `killed` entries of `A/verdicts.json`. Chaining matches `preconditions` against other findings' `postconditions`. Output is `A/review.json` (revived findings with `discovery.phase: "review"`, status per re-verification), and the presentation is kept verbatim.
  - `report.md` ← `K/reporter/instructions.md` Steps 1–3.5 and Rules:
    - Load `verified`, `verified-conditional` and `downgraded` from `A/verdicts.json`, plus revived ones from `A/review.json` if present.
    - Assign final IDs `<id_prefix>-NNN` in rank order.
    - Write `A/findings.json` (full schema) and `A/report.md` per `engine/report-template.md`.
    - Run `python3 scripts/validate-findings.py A/findings.json` before finishing.

- [ ] **Step 9: Coverage test goes live**

Remove `@unittest.expectedFailure` from `tests/test_port_coverage.py`.
Run: `bash tests/run.sh`
Expected: lint 0 errors, all tests pass, **including** `test_every_krait_id_survives`. If IDs are missing, find where they lived in Krait (`grep -rn '<ID>' ~/krait/.claude/skills/krait`) and port that passage. Never edit `krait-ids.txt` to drop IDs.

- [ ] **Step 10: Commit and push**

```bash
git add -A
git commit -m "Port engine phases to JSON hand-offs with chain-specific passages moved to the Solidity pack"
git push origin main
```

---

### Task 12: Subagent prompt templates and runtime adapters

**Files:**
- Create (replacing stubs), under `plugins/chainsec/skills/chainsec/prompts/`: `lens-detector.md`, `rescan.md`, `per-unit.md`, `state-auditor.md`, `critic.md`, `reviewer.md`, `reporter.md`
- Create (replacing stubs), under `plugins/chainsec/skills/chainsec/runtimes/`: `claude-code.md`, `opencode.md`, `codex.md`, `antigravity.md`, `generic.md`
- Test: `tests/test_prompts.py`

**Interfaces:**
- Placeholders in every prompt: `{{CORE}}`, `{{CHAIN}}`, `{{ROOT}}`, `{{A}}`, `{{OUTPUT}}`. Template-specific ones: `{{LENS}}` (lens-detector), `{{CLUSTER_N}}` and `{{CLUSTER_UNITS}}` (per-unit).
- Every prompt ends with the instruction to reply `DONE {{OUTPUT}} <count>`.

- [ ] **Step 1: Write the failing test**

`tests/test_prompts.py`:
```python
import os
import re
import unittest

from helpers import CORE

PROMPTS = os.path.join(CORE, "prompts")
REQUIRED = {"{{CORE}}", "{{CHAIN}}", "{{ROOT}}", "{{A}}", "{{OUTPUT}}"}
EXTRA = {"lens-detector.md": {"{{LENS}}"}, "per-unit.md": {"{{CLUSTER_N}}", "{{CLUSTER_UNITS}}"}}
NAMES = ["lens-detector.md", "rescan.md", "per-unit.md", "state-auditor.md", "critic.md", "reviewer.md", "reporter.md"]


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
```

Run: `python3 -m unittest discover -s tests -p 'test_prompts.py' -v`
Expected: FAIL, because the stubs lack the placeholders.

- [ ] **Step 2: Write the prompts**

`prompts/lens-detector.md`:
```markdown
# Subagent brief: detection lens {{LENS}}

You are one of four parallel detection lenses in a ChainSec audit. You start with an empty
context: everything you need is in files. Use absolute paths exactly as given.

- Core folder: {{CORE}}
- Chain: {{CHAIN}} (pack folder {{CORE}}/chains/{{CHAIN}})
- Code root: {{ROOT}}
- Audit folder: {{A}}

Read, in order:
1. {{CORE}}/engine/phases/detect.md — follow the "Lens run" section for lens {{LENS}} only.
2. {{CORE}}/engine/mindsets.md and {{CORE}}/engine/kill-gates.md ("Detection pre-filter").
3. {{A}}/recon.md, {{A}}/risk.json, {{A}}/facts.json, {{A}}/known-issues.md.
4. {{CORE}}/domains/defi/heuristics.md and {{CORE}}/chains/{{CHAIN}}/heuristics.md.
5. Every module listed under "Activated Modules" in {{A}}/recon.md (paths are relative to {{CORE}}).

Write exactly one file, {{OUTPUT}}: a JSON array of findings conforming to
{{CORE}}/engine/finding.schema.json, each with "status": "candidate", "chain": "{{CHAIN}}",
"discovery": {"phase": "detect", "lens": "{{LENS}}", ...}. Write [] if you found nothing.
Do not write or modify any other file.

When finished, reply with exactly one line: DONE {{OUTPUT}} <number of findings>
```

The other six follow the same shape. Each is 15–25 lines, has the same four context bullets and the same one-file rule, and ends with the DONE line. Their differences:

| Template | Phase file section | Extra inputs | Output rules |
|---|---|---|---|
| `rescan.md` | `rescan.md` (whole) | `{{A}}/candidates/detect.json` as the exclusion list | status `candidate`, phase `rescan` |
| `per-unit.md` | `per-unit.md` "Per-cluster run" | cluster `{{CLUSTER_N}}` with units `{{CLUSTER_UNITS}}` | phase `per-unit`, `discovery.unit` set |
| `state-auditor.md` | `state.md` (whole) | facts `storage_writes` | phase `state` |
| `critic.md` | `verify.md` (whole, excluding "Repair pass") | all `{{A}}/candidates/*.json` except `detect-*.json` and `per-unit-*.json` partials; the pack `fp-patterns.md` | writes every candidate with a final status |
| `reviewer.md` | `review.md` | `{{A}}/verdicts.json` | writes `review.json` |
| `reporter.md` | `report.md` | `{{A}}/verdicts.json`, optional `{{A}}/review.json`, `{{CORE}}/chains/{{CHAIN}}/pack.json` | writes `{{OUTPUT}}` = `{{A}}/findings.json` **and** `{{A}}/report.md` (the only two-file template; say so explicitly), and must run `python3 {{CORE}}/scripts/validate-findings.py {{A}}/findings.json` before replying |

- [ ] **Step 3: Write the runtime adapters**

`runtimes/claude-code.md`:
```markdown
# Runtime: Claude Code

Detected by: the `Agent` tool (older versions: `Task`).

- Paths: this skill's folder is `${CLAUDE_SKILL_DIR}`; CORE is `${CLAUDE_SKILL_DIR}/../chainsec`
  resolved with `cd ... && pwd`. (`${CLAUDE_PLUGIN_ROOT}` also works for plugin installs.)
- **Parallel row:** send ONE message containing one `Agent` call per unit of work (e.g. four calls
  for lenses A–D), `subagent_type: "general-purpose"`, `description` like "ChainSec lens A",
  `prompt` = the filled template. At most 8 calls per message; batch the rest.
- **One-subagent row:** a single `Agent` call with the filled template.
- Wait for every call to return, then check each output file exists and parses. A missing or
  invalid file → do that unit yourself, sequentially, following the same template; if it still
  fails, record the phase in `incomplete_phases`.
- Never paste file contents into prompts; pass paths.
```

`runtimes/opencode.md`:
```markdown
# Runtime: OpenCode

Detected by: the `task` tool (OpenCode v1) or `subagent` tool (reported rename in v2).

- Paths: the skill tool prints "Base directory for this skill: <abs path>". CORE is that path
  followed by `/../chainsec`, resolved with `cd ... && pwd`.
- **Parallel row:** in ONE message, issue one `task` (or `subagent`) call per unit of work with
  `subagent_type: "general"` and the filled template as the prompt. OpenCode runs them concurrently.
- **One-subagent row:** a single call.
- Then verify outputs exactly as in `runtimes/claude-code.md` (existence + JSON parse, sequential
  retry once, then `incomplete_phases`).
```

`runtimes/codex.md`:
```markdown
# Runtime: Codex

Detected by: a sub-agent / delegation tool in your tool list (Codex only delegates when a skill or
the user asks — this skill is asking).

- Paths: resolve relative paths against the folder containing this SKILL.md; CORE is
  `<that folder>/../chainsec` resolved with `cd ... && pwd`.
- **Parallel row:** spawn one sub-agent per unit of work with the filled template as its task,
  all before waiting on any of them.
- **One-subagent row:** spawn one sub-agent.
- No sub-agent tool available → follow `runtimes/generic.md`.
- Verify outputs as in `runtimes/claude-code.md`.

Status: tool names unverified on Codex (no local install during v0.1 smoke tests).
```

`runtimes/antigravity.md`:
```markdown
# Runtime: Antigravity

Detected by: the `invoke_subagent` tool.

- Paths: resolve relative paths against this skill's folder; CORE is `<skill folder>/../chainsec`.
- **Parallel row:** call `invoke_subagent` once per unit of work (they run concurrently), each
  with the filled template as its task. Use the general-purpose/"self" agent type.
- **One-subagent row:** one `invoke_subagent` call.
- Verify outputs as in `runtimes/claude-code.md`.
```

`runtimes/generic.md`:
```markdown
# Runtime: generic (sequential)

Use when no subagent tool is available, or when unsure.

- Paths: CORE is `<this skill's folder>/../chainsec` resolved to an absolute path.
- **Parallel and one-subagent rows:** do each unit of work yourself, one after another. For each,
  read the filled template and follow it exactly as a subagent would, write its single output file,
  then move on. Do not carry conclusions from one lens into the next beyond what the files say —
  re-read inputs from disk for each unit (this preserves the independence the lenses rely on).
- Verify each output file (exists + JSON parse) before moving on; redo a unit once if invalid,
  then record the phase in `incomplete_phases`.
```

- [ ] **Step 4: Run and commit**

Run: `bash tests/run.sh`
Expected: lint 0 errors, all tests pass.

```bash
git add -A
git commit -m "Add subagent prompt templates and per-runtime dispatch adapters"
git push origin main
```

---

### Task 13: Core and entry skills

**Files:**
- Modify: `plugins/chainsec/skills/chainsec/SKILL.md` (final content)
- Create: `plugins/chainsec/skills/chainsec-{audit,review,poc,fuzz,init}/SKILL.md` and `.../agents/openai.yaml`
- Test: extend `tests/test_lint.py` with `test_expected_skills_present`

**Interfaces:**
- Consumes: `engine/pipeline.md`, `engine/phases/{preflight,review}.md`, `engine/poc/workflow.md`, `engine/fuzz.md`, `pack.json` (`poc.guide`, `fuzz.guide`).

- [ ] **Step 1: Write the failing test**

Append to `LintTest` in `tests/test_lint.py`:
```python
    def test_expected_skills_present(self):
        skills = os.path.join(REPO, "plugins", "chainsec", "skills")
        self.assertEqual(sorted(os.listdir(skills)),
                         ["chainsec", "chainsec-audit", "chainsec-fuzz", "chainsec-init", "chainsec-poc", "chainsec-review"])
```
Run: `python3 -m unittest discover -s tests -p 'test_lint.py' -v`
Expected: FAIL (only `chainsec` exists).

- [ ] **Step 2: Check the Codex `agents/openai.yaml` format**

Fetch https://learn.chatgpt.com/docs/build-skills (or search "Codex skills agents/openai.yaml allow_implicit_invocation"). Confirm that `allow_implicit_invocation` lives under `policy:`. If the docs differ, use their structure in all six files. The lint only requires the substring `allow_implicit_invocation: false`.

- [ ] **Step 3: Write the core `SKILL.md`**

```markdown
---
name: chainsec
description: ChainSec core library (audit engine, chain packs, DeFi domain knowledge, prompts, scripts) used by the chainsec-* skills. Do not invoke directly; use chainsec-audit, chainsec-review, chainsec-poc, chainsec-fuzz or chainsec-init.
user-invocable: false
disable-model-invocation: true
---

# ChainSec core

This folder is loaded by the `chainsec-*` entry skills; it is not a workflow on its own.
All paths below are relative to this folder.

| Folder | Contents |
|---|---|
| `engine/` | Pipeline, phase instructions, kill gates, verdicts, schemas, report template, PoC and fuzz method |
| `prompts/` | Subagent briefs filled in by the pipeline |
| `runtimes/` | How to dispatch subagents in each tool |
| `domains/defi/` | Chain-agnostic DeFi modules, primers, heuristics, triggers |
| `chains/<chain>/` | Chain packs; `pack.json` is the contract (`engine/pack.schema.json`) |
| `scripts/` | detect-chain, score-risk, validate-findings, merge-findings (Python 3 stdlib) |

Start at `engine/pipeline.md`. Attribution: ATTRIBUTION.md.
```

- [ ] **Step 4: Write the entry skills**

`chainsec-audit/SKILL.md`:
```markdown
---
name: chainsec-audit
description: Run a full ChainSec smart-contract security audit (recon, multi-lens detection, state analysis, kill-gate verification, report) on this repository or a given path; Solidity supported, more chains via packs. Run only when the user explicitly asks for a ChainSec audit.
disable-model-invocation: true
argument-hint: "[path] [--quick] [--chain <name>] [--fresh]"
---

# ChainSec audit

Arguments: `$ARGUMENTS` (if your tool does not substitute this, take them from the user's message).
The first token that is not a flag is TARGET (default: current directory). Flags: `--quick`
(skip per-unit and state phases), `--chain <name>`, `--fresh`.

1. Resolve the core: from this skill's folder run `cd ../chainsec && pwd`; call the result CORE.
   If `../chainsec/engine/pipeline.md` does not exist, stop and tell the user: "The ChainSec core
   skill is missing next to chainsec-audit. Install all ChainSec skills together — see
   https://github.com/usmananwar11/ChainSec/blob/main/INSTALL.md".
2. Read `../chainsec/engine/pipeline.md` and follow it exactly, with TARGET, the flags and CORE.
3. The audit takes a while. Keep the user informed with one short line per phase.
```

`chainsec-review/SKILL.md`:
```markdown
---
name: chainsec-review
description: Second opinion on findings a ChainSec audit killed; re-examines over-kill-prone gates and chains killed findings into new attack paths. Needs a finished chainsec-audit run.
argument-hint: "[path] [--chain <name>]"
---

# ChainSec review

1. Resolve CORE as in chainsec-audit (`cd ../chainsec && pwd`; stop with the INSTALL.md message if
   `../chainsec/engine/phases/review.md` is missing).
2. TARGET = first non-flag argument or the current directory. For each `TARGET/.audit/<chain>/verdicts.json`
   (or only `--chain`'s): if none exist, tell the user to run chainsec-audit first and stop.
3. Follow `../chainsec/engine/phases/review.md` for that chain (dispatch per `../chainsec/engine/pipeline.md`
   "Dispatch", template `../chainsec/prompts/reviewer.md`, output `TARGET/.audit/<chain>/review.json`).
4. Present the results exactly as review.md's "Presentation to User" section describes.
```

`chainsec-poc/SKILL.md`:
```markdown
---
name: chainsec-poc
description: Build and run an executable proof-of-concept for a ChainSec finding using the chain pack's PoC framework, asserting real harm and running the falsification gate. Run only when the user asks for a PoC.
disable-model-invocation: true
argument-hint: "<finding-id> [path]"
---

# ChainSec PoC

1. Resolve CORE as in chainsec-audit.
2. Find the finding: search `TARGET/.audit/*/findings.json`, then `TARGET/.audit/*/verdicts.json`,
   for the given id. Not found → list available ids and stop. The folder name is the chain.
3. Read `../chainsec/engine/poc/workflow.md`, then the pack guide named by `pack.json` `poc.guide`
   in `../chainsec/chains/<chain>/`. Follow the workflow; supporting references are in
   `../chainsec/engine/poc/` and the pack's `poc/references/`.
4. Write artifacts to `TARGET/.audit/<chain>/poc/<id>/` and update the finding's
   `verdict.evidence_tag` in `TARGET/.audit/<chain>/findings.json`.
```

`chainsec-fuzz/SKILL.md`:
```markdown
---
name: chainsec-fuzz
description: Extract protocol invariants and generate/run invariant fuzz tests with the chain pack's fuzz framework. Run only when the user asks for ChainSec fuzzing.
disable-model-invocation: true
argument-hint: "[path] [--chain <name>]"
---

# ChainSec fuzz

1. Resolve CORE as in chainsec-audit.
2. Detect chains with `python3 ../chainsec/scripts/detect-chain.py TARGET` (or use `--chain`).
3. For each chain: read `../chainsec/engine/fuzz.md`, then the pack guide named by `pack.json`
   `fuzz.guide`. If `TARGET/.audit/<chain>/recon.md` exists, use it; otherwise do only the
   invariant-extraction steps from code.
4. Outputs: `TARGET/.audit/<chain>/fuzz/invariants.md`, `.../fuzz/tests/`, `.../fuzz/report.md`.
```

`chainsec-init/SKILL.md`:
```markdown
---
name: chainsec-init
description: Check whether this project is ready for a ChainSec audit — detects chains and reports required/optional tools per chain pack, with install hints.
argument-hint: "[path]"
---

# ChainSec init

1. Resolve CORE as in chainsec-audit.
2. Run `python3 ../chainsec/scripts/detect-chain.py TARGET` and show the result.
3. For each detected chain, follow `../chainsec/engine/phases/preflight.md` in **report** mode and
   print its summary table. Do not write `.audit/` files in report mode.
4. End with one line: ready / not ready, and the install commands for anything missing.
```

`agents/openai.yaml` for each entry skill uses the Task 1 structure, with `display_name` and `short_description` set per skill: "ChainSec Audit / Full smart-contract security audit", "ChainSec Review / Second opinion on killed findings", "ChainSec PoC / Executable proof-of-concept", "ChainSec Fuzz / Invariant fuzzing", "ChainSec Init / Readiness check". Keep `allow_implicit_invocation: false` in all of them. For `chainsec-review` and `chainsec-init`, which are cheap and read-only, implicit invocation would be harmless. Still keep `false` for consistency.

- [ ] **Step 5: Run and commit**

Run: `bash tests/run.sh`
Expected: lint 0 errors, all tests pass.

```bash
git add -A
git commit -m "Add core and entry skills with Codex invocation policy"
git push origin main
```

---

### Task 14: Installer and documentation

**Files:**
- Create: `install.sh`
- Modify: `INSTALL.md`, `README.md`
- Test: `tests/test_install.py`

**Interfaces:**
- Produces: `install.sh [--tool agents|claude|opencode|antigravity] [--global] [--link] [--dest DIR]`.

- [ ] **Step 1: Write the failing test**

`tests/test_install.py`:
```python
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
```
Run: `python3 -m unittest discover -s tests -p 'test_install.py' -v`
Expected: FAIL (`install.sh` is missing).

- [ ] **Step 2: Implement `install.sh`**

```bash
#!/usr/bin/env bash
# Install ChainSec skills for tools that load Agent Skills from folders.
# Usage: install.sh [--tool agents|claude|opencode|antigravity] [--global] [--link] [--dest DIR]
#   agents      -> .agents/skills           (Codex, OpenCode, Cursor, Gemini CLI, Antigravity)
#   claude      -> .claude/skills           (Claude Code without the plugin; also read by OpenCode/Cursor)
#   opencode    -> .opencode/skills
#   antigravity -> .agents/skills  (--global: ~/.gemini/config/skills)
# --global installs under your home folder; --link symlinks instead of copying.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/plugins/chainsec/skills"
TOOL=agents
GLOBAL=0
LINK=0
DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --tool) TOOL="$2"; shift 2 ;;
    --global) GLOBAL=1; shift ;;
    --link) LINK=1; shift ;;
    --dest) DEST="$2"; shift 2 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
if [ -z "$DEST" ]; then
  case "$TOOL:$GLOBAL" in
    agents:0|antigravity:0) DEST=".agents/skills" ;;
    agents:1) DEST="$HOME/.agents/skills" ;;
    claude:0) DEST=".claude/skills" ;;
    claude:1) DEST="$HOME/.claude/skills" ;;
    opencode:0) DEST=".opencode/skills" ;;
    opencode:1) DEST="$HOME/.config/opencode/skills" ;;
    antigravity:1) DEST="$HOME/.gemini/config/skills" ;;
    *) echo "unknown tool: $TOOL" >&2; exit 2 ;;
  esac
fi
mkdir -p "$DEST"
for skill in "$SRC"/*/; do
  name="$(basename "$skill")"
  target="$DEST/$name"
  if [ -e "$target" ] || [ -L "$target" ]; then rm -rf "$target"; fi
  if [ "$LINK" = 1 ]; then ln -s "${skill%/}" "$target"; else cp -R "${skill%/}" "$target"; fi
  echo "installed $name -> $target"
done
echo "Done. ChainSec skills must stay together in one folder (entry skills use ../chainsec)."
```
Then run `chmod +x install.sh`.

- [ ] **Step 3: Write `INSTALL.md`**

Sections, with exact commands:
- **Claude Code (plugin, recommended):** `/plugin marketplace add usmananwar11/ChainSec` then `/plugin install chainsec@chainsec`. Commands: `/chainsec:chainsec-audit`, `/chainsec:chainsec-review`, `/chainsec:chainsec-poc <ID>`, `/chainsec:chainsec-fuzz`, `/chainsec:chainsec-init`.
- **Codex:** `codex plugin marketplace add usmananwar11/ChainSec` (Codex reads the Claude plugin manifest), or `git clone https://github.com/usmananwar11/ChainSec && ChainSec/install.sh --tool agents` in your project. Invoke with `$chainsec-audit`.
- **OpenCode:** `ChainSec/install.sh --tool opencode` (project) or `--tool opencode --global`. OpenCode also reads `.agents/skills` and `.claude/skills`. Ask: "use the chainsec-audit skill".
- **Antigravity:** `ChainSec/install.sh --tool antigravity` (project `.agents/skills`) or `--global`. Invoke `/chainsec-audit`.
- **Cursor / Gemini CLI:** `install.sh --tool agents`.
- **Requirements:** `python3` ≥ 3.11 and the tools listed by `chainsec-init` for your chain (Solidity: `forge`; optional `slither`).
- **Updating:** re-run `install.sh` (it replaces only ChainSec's own folders), or `/plugin update` in Claude Code.
- **Important:** the six `chainsec*` folders must be installed side by side.

- [ ] **Step 4: Write `README.md`**

Sections:
1. Title and one-line pitch.
2. "What it does": the pipeline in 8 bullets taken from the spec §4.1.
3. Supported chains table: Solidity ✅, Cairo and Soroban planned.
4. Supported tools table: Claude Code (parallel subagents), OpenCode (parallel), Antigravity (parallel), Codex (parallel, unverified), others (sequential).
5. Quick start (Claude Code commands), then a link to `INSTALL.md`.
6. Commands table (5 entry skills with one-line purposes).
7. Output: `.audit/` layout.
8. Repository layout (the File Map above, condensed).
9. Development: `bash tests/run.sh`.
10. Attribution (Krait/Zealynx) and license (MIT).

- [ ] **Step 5: Run and commit**

Run: `bash tests/run.sh`
Expected: all pass.

```bash
git add -A
git commit -m "Add installer for folder-based agents and finish README and INSTALL"
git push origin main
```

---

### Task 15: Benchmark harness

**Files:**
- Create: `benchmarks/solidity/registry.yaml`, `benchmarks/solidity/scoring.md`, `benchmarks/solidity/baselines/krait-v8.json`, `benchmarks/solidity/results/.gitkeep`
- Create: `tools/score_benchmark.py`
- Test: `tests/test_score_benchmark.py`

**Interfaces:**
- Result file format (baseline entries and `results/<id>.json` share it):
  ```json
  {"id": "goodentry", "tool": "chainsec", "official_total": 14, "exact": 5, "partial": 0, "fp": 0,
   "matches": [{"official": "H-04", "finding": "SOL-003", "grade": "exact"}], "false_positives": [], "notes": ""}
  ```
  `matches` and `false_positives` are optional documentation; scores use the counts.
- CLI:
  - `score_benchmark.py score <result.json>...` prints per-target P/R and the aggregate.
  - `score_benchmark.py compare <baseline.json> <results_dir>` prints a comparison table and `PASS` / `FAIL`. Exit 0 on PASS, 1 on FAIL.
  - PASS means both of these hold, over the ids present in both:
    - the aggregate recall of the results is ≥ the baseline's aggregate recall;
    - the results' total `fp` is ≤ the baseline's total `fp`.

- [ ] **Step 1: Write the failing test**

`tests/test_score_benchmark.py`:
```python
import json
import os
import sys
import tempfile
import unittest

from helpers import REPO, run

TOOL = os.path.join(REPO, "tools", "score_benchmark.py")


def entry(i, total, exact, partial=0, fp=0, tool="chainsec"):
    return {"id": i, "tool": tool, "official_total": total, "exact": exact, "partial": partial, "fp": fp}


def results_dir(*entries):
    d = tempfile.mkdtemp()
    for e in entries:
        with open(os.path.join(d, e["id"] + ".json"), "w") as f:
            json.dump(e, f)
    return d


def baseline(*entries):
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(list(entries), f)
    return p


class ScoreBenchmarkTest(unittest.TestCase):
    def test_uniform_partial_credit(self):
        d = results_dir(entry("arcade", 8, 2, partial=1))
        r = run([sys.executable, TOOL, "score", os.path.join(d, "arcade.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("recall 31.25", r.stdout)
        self.assertIn("precision 100.00", r.stdout)

    def test_compare_pass(self):
        base = baseline(entry("a", 10, 2, tool="krait"), entry("b", 10, 1, tool="krait"))
        d = results_dir(entry("a", 10, 1), entry("b", 10, 2))
        r = run([sys.executable, TOOL, "compare", base, d])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS", r.stdout)

    def test_compare_fail_on_new_fp(self):
        base = baseline(entry("a", 10, 2, tool="krait"))
        d = results_dir(entry("a", 10, 3, fp=1))
        r = run([sys.executable, TOOL, "compare", base, d])
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)

    def test_compare_fail_on_recall(self):
        base = baseline(entry("a", 10, 3, tool="krait"))
        d = results_dir(entry("a", 10, 2))
        self.assertEqual(run([sys.executable, TOOL, "compare", base, d]).returncode, 1)

    def test_shipped_baseline_aggregate(self):
        base = os.path.join(REPO, "benchmarks", "solidity", "baselines", "krait-v8.json")
        r = run([sys.executable, TOOL, "score", base])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("aggregate recall 17.42", r.stdout)


if __name__ == "__main__":
    unittest.main()
```

Run: `python3 -m unittest discover -s tests -p 'test_score_benchmark.py' -v`
Expected: FAIL (the tool is missing).

- [ ] **Step 2: Implement `tools/score_benchmark.py`**

```python
#!/usr/bin/env python3
"""Score ChainSec benchmark results with one uniform rule.

TP = exact + 0.5 * partial; precision = TP / (TP + fp); recall = TP / official_total.

Usage:
  score_benchmark.py score <file.json>...        (a file may hold one entry or a list)
  score_benchmark.py compare <baseline.json> <results_dir>
compare passes when, over ids present in both, aggregate recall >= baseline's and
total fp <= baseline's.
"""
import glob
import json
import os
import sys


def entries(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def tp(e):
    return e["exact"] + 0.5 * e.get("partial", 0)


def precision(e):
    denom = tp(e) + e.get("fp", 0)
    return 100.0 * tp(e) / denom if denom else None


def recall(e):
    return 100.0 * tp(e) / e["official_total"] if e["official_total"] else 0.0


def aggregate(es):
    total = sum(e["official_total"] for e in es)
    return 100.0 * sum(tp(e) for e in es) / total if total else 0.0


def fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def cmd_score(paths):
    es = [e for p in paths for e in entries(p)]
    for e in es:
        print(f"{e['id']}: recall {fmt(recall(e))} precision {fmt(precision(e))} fp {e.get('fp', 0)}")
    print(f"aggregate recall {fmt(aggregate(es))} total fp {sum(e.get('fp', 0) for e in es)}")
    return 0


def cmd_compare(baseline_path, results_dir):
    base = {e["id"]: e for e in entries(baseline_path)}
    res = {e["id"]: e for p in sorted(glob.glob(os.path.join(results_dir, "*.json"))) for e in entries(p)}
    ids = sorted(set(base) & set(res))
    if not ids:
        print("FAIL: no overlapping targets")
        return 1
    print(f"{'target':<16}{'base R':>9}{'new R':>9}{'base FP':>9}{'new FP':>8}")
    for i in ids:
        print(f"{i:<16}{fmt(recall(base[i])):>9}{fmt(recall(res[i])):>9}{base[i].get('fp', 0):>9}{res[i].get('fp', 0):>8}")
    b_rec, n_rec = aggregate([base[i] for i in ids]), aggregate([res[i] for i in ids])
    b_fp, n_fp = sum(base[i].get("fp", 0) for i in ids), sum(res[i].get("fp", 0) for i in ids)
    ok = n_rec >= b_rec and n_fp <= b_fp
    print(f"aggregate recall base {fmt(b_rec)} new {fmt(n_rec)}; fp base {b_fp} new {n_fp}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) >= 2 and argv[0] == "score":
        return cmd_score(argv[1:])
    if len(argv) == 3 and argv[0] == "compare":
        return cmd_compare(argv[1], argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 3: Write the baseline and registry**

`benchmarks/solidity/baselines/krait-v8.json`: Krait's recorded v8 results, re-scored with the uniform rule (totals are `high_total + medium_total`; exact is `high_found + medium_found`):
```json
[
  {"id": "pooltogether", "tool": "krait-v8", "official_total": 9,  "exact": 1, "partial": 0, "fp": 0, "notes": "registry.yaml v8"},
  {"id": "initcapital",  "tool": "krait-v8", "official_total": 15, "exact": 0, "partial": 1, "fp": 0, "notes": "registry.yaml v8"},
  {"id": "goodentry",    "tool": "krait-v8", "official_total": 14, "exact": 5, "partial": 0, "fp": 0, "notes": "registry.yaml v8"},
  {"id": "arcade",       "tool": "krait-v8", "official_total": 8,  "exact": 2, "partial": 1, "fp": 0, "notes": "registry.yaml v8"},
  {"id": "frankencoin",  "tool": "krait-v8", "official_total": 20, "exact": 2, "partial": 1, "fp": 0, "notes": "registry.yaml v8"}
]
```
The aggregate recall is 11.5 / 66 = 17.42, which is what the test checks.

`benchmarks/solidity/registry.yaml`: copy `~/krait/shadow-audits/registry.yaml` verbatim, then:
- replace the first comment line with `# ChainSec Solidity benchmark registry (from Krait shadow-audits, MIT)`;
- add `chain: solidity` under every `- id:` line.

With BSD sed on macOS:
```bash
sed -E 's/^(  - id: .*)$/\1\
    chain: solidity/' ~/krait/shadow-audits/registry.yaml > benchmarks/solidity/registry.yaml
```
Then fix the header line by hand. Verify with `grep -c 'chain: solidity' benchmarks/solidity/registry.yaml` (should equal `grep -c '  - id:'`).

`benchmarks/solidity/scoring.md`:
```markdown
# Solidity benchmark scoring

Grades per official finding: EXACT (same root cause and location) = 1, PARTIAL (related area or
same mechanism at a different location) = 0.5, missed = 0. Each reported ChainSec finding that
matches no official finding is an FP.

TP = exact + 0.5 × partial · Precision = TP/(TP+FP) · Recall = TP/official_total.
Krait's registry applied partial credit inconsistently; `baselines/krait-v8.json` re-scores its
v8 targets with this rule.

## Running a target
1. `git clone <repo> /tmp/bench/<id>` at the contest commit (registry `repo`).
2. Open a fresh agent session in that folder; run `chainsec-audit` (no flags).
3. Grade `.audit/findings.json` against the official High/Medium findings in the registry's
   `findings_repo` (report at https://code4rena.com/reports/<contest>). Record matches.
4. Write `benchmarks/solidity/results/<id>.json` (format: see baselines) — include `matches`,
   `false_positives`, ChainSec version/commit and the facts mode in `notes`.
5. `python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results`

## Known methodology deltas vs Krait
- Regex-mode `state_writers` excludes view/pure functions (Krait counted all public/external).
- `external_calls` counts only call/transfer primitives in both modes.
- On macOS Krait's extractor needed GNU `timeout`; without it Krait always ran in regex mode.
```

- [ ] **Step 4: Run and commit**

Run: `bash tests/run.sh`
Expected: all pass.

```bash
git add -A
git commit -m "Add Solidity benchmark registry, uniform scoring and Krait v8 baseline"
git push origin main
```

---

### Task 16: Cross-tool smoke tests (manual)

**Files:**
- Create: `docs/smoke-tests.md` (results log)
- Modify: `runtimes/*.md` if the tool names observed differ from the documented ones

The smoke target is `tests/fixtures/solidity-basic`, which has a planted bug: `Vault.sweep` has no access control. A run **passes** when all four of these hold:
- `.audit/solidity/findings.json` exists;
- `python3 plugins/chainsec/skills/chainsec/scripts/validate-findings.py <that file>` exits 0;
- a finding locates `src/Vault.sol` at the `sweep` function;
- `.audit/report.md` exists.

Copy the fixture to a scratch folder first, so the repo stays clean:
```bash
rm -rf /tmp/chainsec-smoke && cp -R tests/fixtures/solidity-basic /tmp/chainsec-smoke
```

- [ ] **Step 1: Claude Code.** In a Claude Code session: `/plugin marketplace add /Users/usmananwar/Documents/work/chainsec`, then `/plugin install chainsec@chainsec`, then `cd /tmp/chainsec-smoke` and `/chainsec:chainsec-audit --quick`. Check the pass criteria. Record the exact subagent tool name used, the elapsed time and the result in `docs/smoke-tests.md`.
- [ ] **Step 2: OpenCode.** Reset the scratch folder, then run `/Users/usmananwar/Documents/work/chainsec/install.sh --tool opencode --dest /tmp/chainsec-smoke/.opencode/skills`. In `opencode` inside `/tmp/chainsec-smoke`, ask: "Use the chainsec-audit skill with --quick". Check the pass criteria. Record whether the tool was `task` or `subagent`, and whether it ran in parallel.
- [ ] **Step 3: Antigravity (the user runs it).** `agy` is not on PATH, so ask the user to:
  1. run `install.sh --tool antigravity --dest /tmp/chainsec-smoke/.agents/skills`;
  2. open `/tmp/chainsec-smoke` in Antigravity and run `/chainsec-audit --quick`;
  3. paste back the final message plus the output of `ls -R .audit`.
  Check the pass criteria and record the result, and whether `invoke_subagent` was used.
- [ ] **Step 4: Fix and re-run.** For any failure, use superpowers:systematic-debugging. Fix the runtime adapter or pipeline text, re-run that tool, and update `docs/smoke-tests.md`.
- [ ] **Step 5: Commit and push**

```bash
git add -A
git commit -m "Record cross-tool smoke tests and adjust runtime adapters"
git push origin main
```

---

### Task 17: Benchmark acceptance run (manual, token-heavy, so confirm with the user before starting)

**Files:**
- Create: `benchmarks/solidity/results/{pooltogether,initcapital,goodentry,arcade,frankencoin}.json`

- [ ] **Step 1: Confirm with the user.** These are five full audits, each probably around an hour of agent time. Ask before starting, and whether to run them in parallel sessions.
- [ ] **Step 2: Run each target** following `benchmarks/solidity/scoring.md` "Running a target", in a fresh Claude Code session per target, with the plugin installed from this repo.
- [ ] **Step 3: Grade and record** each target's result JSON, with `matches` and `false_positives` filled in.
- [ ] **Step 4: Compare**

Run: `python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results`
Expected: `PASS`.

If it prints FAIL:
1. Identify which targets regressed.
2. Diff ChainSec's findings against Krait's notes in the registry.
3. Trace the cause to a port change: a dropped passage (check `test_port_coverage`), a tier shift (compare `risk.json` against Krait's formula), or dispatch differences.
4. Fix it and re-run only the affected targets.

Never adjust grades to force a pass.
- [ ] **Step 5: Commit and push**

```bash
git add -A
git commit -m "Record Solidity benchmark acceptance results against Krait v8"
git push origin main
```
