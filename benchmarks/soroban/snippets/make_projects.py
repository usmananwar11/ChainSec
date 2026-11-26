#!/usr/bin/env python3
"""Write Soroban snippet projects. Usage: make_projects.py CASES_JSONL OUT [--classes-per-project N]

Groups cases by class (N classes per project, default 4) into Cargo workspaces OUT/snippets-<k>/
with one member crate per case at contracts/case-<nn>/ (neutral names, shuffled by a fixed seed so
the order does not reveal vulnerable vs fixed). Writes OUT/manifest.json:
{project: [{case_id, class_id, expected_detect, tier, dir}]}.
"""
import argparse
import json
import os
import random

ROOT_TOML = ('[workspace]\nresolver = "2"\nmembers = ["contracts/*"]\n\n'
             '[workspace.dependencies]\nsoroban-sdk = "=20.0.0"\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("out")
    ap.add_argument("--classes-per-project", type=int, default=4)
    args = ap.parse_args(argv)
    cases = [json.loads(line) for line in open(args.cases, encoding="utf-8") if line.strip()]
    classes = sorted({c["class_id"] for c in cases})
    n = args.classes_per_project
    manifest = {}
    for k in range(0, len(classes), n):
        group = set(classes[k:k + n])
        proj = f"snippets-{k // n + 1}"
        members = [c for c in cases if c["class_id"] in group]
        random.Random(proj).shuffle(members)
        pdir = os.path.join(args.out, proj)
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "Cargo.toml"), "w", encoding="utf-8") as f:
            f.write(ROOT_TOML)
        rows = []
        for i, c in enumerate(members, 1):
            rel = f"contracts/case-{i:02d}"
            for name, text in c["files"].items():
                path = os.path.join(pdir, rel, name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if name == "Cargo.toml":
                    text = text.replace('name = "case"', f'name = "case-{i:02d}"', 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            rows.append({k2: c[k2] for k2 in ("case_id", "class_id", "expected_detect", "tier")} | {"dir": rel + "/"})
        manifest[proj] = rows
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({"projects": len(manifest), "cases": len(cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
