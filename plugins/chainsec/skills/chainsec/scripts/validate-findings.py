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
