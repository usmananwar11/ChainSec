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
