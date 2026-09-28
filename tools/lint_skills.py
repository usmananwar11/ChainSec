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
