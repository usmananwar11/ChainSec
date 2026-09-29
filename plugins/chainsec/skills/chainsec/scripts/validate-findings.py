#!/usr/bin/env python3
"""Validate ChainSec findings before the report.

Usage:
  validate-findings.py <findings.json> [--schema PATH] [--downgrade | --schema-only]

Prints a JSON list of rejects ({"id", "rule", "detail"}) to stdout.
Exit 0: no rejects (or --downgrade resolved them). Exit 1: rejects remain. Exit 2: bad input.

Hard rules apply to findings with status verified / verified-conditional and
severity Critical, High or Medium:
  location       at least one location with file and line_start
  harm           non-empty harm.who and harm.loses_what (the Impact Premise)
  exploit_trace  non-empty exploit_trace
Every id must be unique: each repeated id gets one "duplicate-id" reject.
With --downgrade, hard-rule rejects are rewritten in place to status "downgraded",
severity "Low", with the reason recorded; only the offending element is touched.
Schema errors and duplicate ids are never auto-fixed.
With --schema-only, only schema rejects (and input errors) are reported.
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


NOT_AUTO_FIXED = {"schema", "duplicate-id"}


def check(findings, schema):
    """Return [(index, reject)]; index is the offending element's position, None for duplicate-id."""
    rejects = []
    seen = {}
    for i, f in enumerate(findings):
        fid = f.get("id", f"#{i}") if isinstance(f, dict) else f"#{i}"
        for err in validate(f, schema):
            rejects.append((i, {"id": fid, "rule": "schema", "detail": err}))
        if isinstance(f, dict):
            for rule, detail in hard_rule_failures(f):
                rejects.append((i, {"id": fid, "rule": rule, "detail": detail}))
            if "id" in f:
                seen.setdefault(json.dumps(f["id"]), []).append(i)
    for key, idxs in seen.items():
        if len(idxs) > 1:
            rejects.append((None, {"id": json.loads(key), "rule": "duplicate-id",
                                   "detail": f"id used {len(idxs)} times (indexes {idxs}); renumber"}))
    return rejects


def downgrade(findings, rejects):
    hard = {}
    for i, r in rejects:
        if r["rule"] not in NOT_AUTO_FIXED:
            hard.setdefault(i, []).append(r["rule"])
    for i, rules in hard.items():
        f = findings[i]
        verdict = f.setdefault("verdict", {})
        verdict.setdefault("original_severity", f.get("severity"))
        f["status"] = "downgraded"
        f["severity"] = "Low"
        note = "auto-downgraded by validate-findings: missing " + ", ".join(rules)
        verdict["reason"] = f"{verdict.get('reason', '')} | {note}".strip(" |")
    return [(i, r) for i, r in rejects if r["rule"] in NOT_AUTO_FIXED]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate ChainSec findings")
    ap.add_argument("findings")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--downgrade", action="store_true")
    mode.add_argument("--schema-only", action="store_true")
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
    if args.schema_only:
        rejects = [(i, r) for i, r in rejects if r["rule"] == "schema"]
    if args.downgrade and rejects:
        rejects = downgrade(findings, rejects)
        write_json(args.findings, findings)
    rejects = [r for _, r in rejects]
    print(json.dumps(rejects, indent=2))
    return 1 if rejects else 0


if __name__ == "__main__":
    sys.exit(main())
