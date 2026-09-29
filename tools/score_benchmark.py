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
