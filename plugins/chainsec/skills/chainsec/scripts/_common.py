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


def scope_files(root, scope):
    """Select pack scope, applying exclusions before deciding whether to fall back."""
    skip_dirs = {".git", ".audit", "node_modules", "out", "cache", "artifacts", "build"}
    rels = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
        for name in sorted(filenames):
            rels.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    exclude = scope.get("exclude", [])
    for key in ("include", "fallback_include"):
        chosen = [r for r in rels if matches_any(r, scope.get(key, [])) and not matches_any(r, exclude)]
        if chosen:
            return chosen
    return []
