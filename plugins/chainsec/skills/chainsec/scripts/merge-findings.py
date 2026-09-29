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
Exit 2 when an input is missing, is not JSON, or is not a JSON list of objects.
"""
import argparse
import glob
import json
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


def load_inputs(paths):
    lists = []
    for p in paths:
        try:
            data = load_json(p)
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"merge-findings: cannot read {p}: {e}")
        if not isinstance(data, list) or not all(isinstance(f, dict) for f in data):
            raise ValueError(f"merge-findings: {p} must be a JSON list of objects")
        lists.append(data)
    return lists


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge ChainSec findings")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--chains-dir", default=os.path.join(HERE, "..", "chains"))
    ap.add_argument("--concat", action="store_true")
    args = ap.parse_args(argv)
    try:
        lists = load_inputs(args.inputs)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if args.concat:
        result = [f for lst in lists for f in lst]
    else:
        result = merge(lists, extension_map(args.chains_dir))
    write_json(args.out, result)
    print(f"{len(result)} findings -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
