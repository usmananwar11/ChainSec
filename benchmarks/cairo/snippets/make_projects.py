#!/usr/bin/env python3
"""Write Scarb projects for the Cairo snippet suite. Usage: make_projects.py CASES.jsonl OUT [--per N]"""
import argparse
import json
import os
import re

SCARB = '[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2024_07"\n\n' \
        '[dependencies]\nstarknet = "2.18.0"\n\n[[target.starknet-contract]]\n'


def camel(case_id):
    return "".join(p.capitalize() for p in re.split(r'[^A-Za-z0-9]+', case_id) if p)


def source(case):
    head = f"// case {case['case_id']} ({case['class_id']}); source: {case.get('source_url', '')}\n"
    code = case["code"].rstrip() + "\n"
    if "starknet::contract" in code or "starknet::component" in code:
        return head + code
    body = "".join(("    " + l if l.strip() else l) for l in code.splitlines(True))
    return head + f"#[starknet::contract]\nmod {camel(case['case_id'])} {{\n{body}}}\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cases")
    ap.add_argument("out")
    ap.add_argument("--per", type=int, default=7)
    a = ap.parse_args(argv)
    cases = sorted((json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()),
                   key=lambda c: c["case_id"])
    manifest = {}
    for i in range(0, len(cases), a.per):
        proj = f"snippets-{i // a.per + 1}"
        src = os.path.join(a.out, proj, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(a.out, proj, "Scarb.toml"), "w") as f:
            f.write(SCARB.format(name=proj.replace("-", "_")))
        mods = []
        for case in cases[i:i + a.per]:
            mod = re.sub(r'\W', '_', case["case_id"]).lower()
            mods.append(mod)
            with open(os.path.join(src, mod + ".cairo"), "w") as f:
                f.write(source(case))
            manifest.setdefault(proj, []).append({"case_id": case["case_id"], "class_id": case["class_id"],
                                                  "expected_detect": case["expected_detect"],
                                                  "file": f"src/{mod}.cairo"})
        with open(os.path.join(src, "lib.cairo"), "w") as f:
            f.write("".join(f"mod {m};\n" for m in mods))
    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({"projects": len(manifest), "cases": len(cases)}))


if __name__ == "__main__":
    main()
