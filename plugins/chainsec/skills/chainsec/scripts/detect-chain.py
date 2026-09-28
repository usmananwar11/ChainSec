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
