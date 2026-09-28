#!/usr/bin/env python3
"""Solidity facts extractor for ChainSec.

Usage:
  extract.py --root DIR --pack PACK_JSON --out FACTS_JSON [--artifacts DIR --foundry-dir DIR]

With --artifacts (output of `forge build --ast`) facts come from the compiler AST
(mode "compiler"). Without it, or if any in-scope file lacks an AST, facts come
from regex over comment-stripped source (mode "regex").
Output conforms to engine/facts.schema.json.
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
from _common import load_json, matches_any, write_json  # noqa: E402

CALL_KINDS = ("call", "delegatecall", "staticcall", "send", "transfer", "transferFrom",
              "safeTransfer", "safeTransferFrom", "safeTransferETH")
TOKEN_KINDS = {"transferFrom", "safeTransfer", "safeTransferFrom"}
AUTH_CALLS = ("_checkOwner", "_checkRole", "hasRole")
SKIP_DIRS = {".git", ".audit", "node_modules", "out", "cache", "artifacts", "build"}
VIS = ("external", "public", "internal", "private")
MUT = ("pure", "view", "payable")


# ------------------------------------------------------------------ shared

def scope_files(root, scope):
    rels = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            rels.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    exclude = scope.get("exclude", [])
    for key in ("include", "fallback_include"):
        chosen = [r for r in rels if matches_any(r, scope.get(key, [])) and not matches_any(r, exclude)]
        if chosen:
            return chosen
    return []


def empty_facts(root, mode):
    return {"chain": "solidity", "mode": mode, "root": root, "units": [], "entry_points": [],
            "auth_sites": [], "storage_writes": [], "external_calls": [], "value_transfers": [],
            "counters": {}}


def new_counters(loc):
    return {"loc": loc, "external_calls": 0, "state_writers": 0, "payable": 0,
            "assembly_blocks": 0, "unchecked_blocks": 0}


def classify_value(kind, n_args, has_value_opt):
    if kind in ("send", "safeTransferETH") or (kind == "call" and has_value_opt):
        return "native"
    if kind == "transfer":
        return "native" if n_args == 1 else "token"
    if kind in TOKEN_KINDS:
        return "token"
    return None


# ------------------------------------------------------------------ regex mode

_STRIP = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)
UNIT_RE = re.compile(r'\b(abstract\s+contract|contract|library|interface)\s+([A-Za-z_]\w*)\s*(?:is\s+([^{]+?))?\s*\{')
FUNC_RE = re.compile(r'(?<![.\w])(?:function\s+([A-Za-z_]\w*)|(constructor|receive|fallback))\s*\(')
MOD_DEF_RE = re.compile(r'\bmodifier\s+([A-Za-z_]\w*)')
STATE_RE = re.compile(r'(?<![\w.])(?:mapping\s*\(.*?\)|[A-Za-z_][\w.]*(?:\s*\[[^\]]*\])*)\s+'
                      r'((?:(?:public|private|internal|constant|immutable|override|transient)\s+)*)'
                      r'([A-Za-z_]\w*)\s*(?:=[^;]*)?;', re.S)
CALL_RE = re.compile(r'\.\s*(' + "|".join(CALL_KINDS) + r')\s*(\{[^}]*\})?\s*\(')
AUTH_RE = re.compile(r'msg\.sender\s*[!=]=|[!=]=\s*msg\.sender|\b(?:' + "|".join(AUTH_CALLS) + r')\s*\(')
WRITE_OPS = r'(?:=(?!=)|\+=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=|\+\+|--)'
TUPLE_OPEN_RE = re.compile(r'(?<![\w.])\(')
TUPLE_EQ_RE = re.compile(r'\s*=(?!=)')
DECL_COMPONENT_RE = re.compile(r'^[\w.\[\]]+\s+[A-Za-z_]\w*$')


def strip_comments(src):
    def repl(m):
        s = m.group(0)
        return re.sub(r"[^\n]", " ", s) if s.startswith("/") else s
    return _STRIP.sub(repl, src)


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def match_close(text, open_idx, open_ch, close_ch):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def top_level_args(text, open_idx):
    inner = text[open_idx + 1:match_close(text, open_idx, "(", ")")]
    if not inner.strip():
        return 0
    depth, count = 0, 1
    for c in inner:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            count += 1
    return count


def split_components(inner):
    parts, depth, start = [], 0, 0
    for i, c in enumerate(inner):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(inner[start:i])
            start = i + 1
    parts.append(inner[start:])
    return parts


def drop_parens(text):
    prev = None
    while prev != text:
        prev, text = text, re.sub(r'\([^()]*\)', '', text)
    return text


def parse_header(rest):
    words = re.findall(r'[A-Za-z_]\w*', drop_parens(re.split(r'\breturns\b', rest)[0]))
    vis = next((w for w in words if w in VIS), None)
    mut = next((w for w in words if w in MUT), "nonpayable")
    mods = [w for w in words if w not in VIS and w not in MUT and w not in ("virtual", "override")]
    return vis, mut, mods


def regex_units(rel, text):
    units = []
    for m in UNIT_RE.finditer(text):
        open_idx = m.end() - 1
        close = match_close(text, open_idx, "{", "}")
        parents = [p.strip() for p in drop_parens(m.group(3) or "").split(",") if p.strip()]
        first = line_of(text, m.start())
        units.append({"name": m.group(2), "kind": "contract" if "contract" in m.group(1) else m.group(1),
                      "file": rel, "line": first, "loc": line_of(text, close) - first + 1, "parents": parents,
                      "_start": m.start(), "_open": open_idx, "_close": close})
    return units


def unit_at(units, pos):
    return next((u for u in units if u["_start"] <= pos <= u["_close"]), None)


def regex_state_vars(text, unit):
    body = text[unit["_open"] + 1:unit["_close"]]
    segments, depth, seg_start = [], 0, 0
    for i, c in enumerate(body):
        if c == "{":
            if depth == 0:
                segments.append(body[seg_start:i])
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                seg_start = i + 1
    segments.append(body[seg_start:] if depth == 0 else "")
    names = set()
    for seg in segments:
        for m in STATE_RE.finditer(seg):
            mods = m.group(1).split()
            if "constant" not in mods and "immutable" not in mods:
                names.add(m.group(2))
    return names


def regex_file(facts, rel, src, text, units, state_vars, parents_of):
    counters = new_counters(src.count("\n"))
    counters["assembly_blocks"] = len(re.findall(r'\bassembly\b[^{;]*\{', text))
    counters["unchecked_blocks"] = len(re.findall(r'\bunchecked\s*\{', text))
    regions = []
    for m in FUNC_RE.finditer(text):
        unit = unit_at(units, m.start())
        if unit is None:
            continue
        p_close = match_close(text, m.end() - 1, "(", ")")
        term = re.compile(r'[{;]').search(text, p_close + 1)
        vis, mut, mods = parse_header(text[p_close + 1:term.start() if term else len(text)])
        kind = "function" if m.group(1) else m.group(2)
        name = m.group(1) or m.group(2)
        if kind in ("receive", "fallback"):
            vis = vis or "external"
        vis = vis or "internal"
        has_body = bool(term) and text[term.start()] == "{"
        line = line_of(text, m.start())
        if has_body:
            regions.append({"unit": unit["name"], "name": name,
                            "body": (term.start(), match_close(text, term.start(), "{", "}"))})
        if mut == "payable":
            counters["payable"] += 1
        if kind != "constructor" and vis in ("external", "public") and has_body and unit["kind"] != "interface":
            facts["entry_points"].append({"unit": unit["name"], "name": name, "file": rel, "line": line,
                                          "visibility": vis, "mutability": mut, "guards": mods})
            if mut not in ("view", "pure"):
                counters["state_writers"] += 1
        for g in mods:
            if g.startswith("only"):
                facts["auth_sites"].append({"unit": unit["name"], "file": rel, "line": line, "kind": "modifier:" + g})
    for m in MOD_DEF_RE.finditer(text):
        unit = unit_at(units, m.start())
        brace = text.find("{", m.end())
        if unit is not None and brace >= 0:
            regions.append({"unit": unit["name"], "name": m.group(1),
                            "body": (brace, match_close(text, brace, "{", "}"))})

    def region_name(pos):
        return next((r["name"] for r in regions if r["body"][0] <= pos <= r["body"][1]), None)

    for m in AUTH_RE.finditer(text):
        unit = unit_at(units, m.start())
        if unit is not None:
            facts["auth_sites"].append({"unit": unit["name"], "file": rel, "line": line_of(text, m.start()), "kind": "inline"})
    for m in CALL_RE.finditer(text):
        unit = unit_at(units, m.start())
        if unit is None:
            continue
        kind = m.group(1)
        entry = {"unit": unit["name"], "function": region_name(m.start()), "file": rel,
                 "line": line_of(text, m.start()), "kind": kind}
        facts["external_calls"].append(entry)
        counters["external_calls"] += 1
        asset = classify_value(kind, top_level_args(text, m.end() - 1), bool(m.group(2) and "value" in m.group(2)))
        if asset:
            facts["value_transfers"].append(dict(entry, asset=asset))
    for unit in units:
        names, stack, seen = set(), [unit["name"]], set()
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                names |= state_vars.get(n, set())
                stack += parents_of.get(n, [])
        if not names:
            continue
        alt = "|".join(sorted(map(re.escape, names), key=len, reverse=True))
        patterns = [re.compile(r'(?<![\w.])(' + alt + r')\b\s*(?:\[[^\]]*\]\s*)*(?:\.\s*\w+\s*)*' + WRITE_OPS),
                    re.compile(r'(?:\+\+|--|\bdelete\s+)\s*(' + alt + r')\b')]
        written = set()
        for r in regions:
            if r["unit"] != unit["name"]:
                continue
            for pat in patterns:
                for m in pat.finditer(text, r["body"][0], r["body"][1]):
                    key = (r["name"], line_of(text, m.start()), m.group(1))
                    if key not in written:
                        written.add(key)
                        facts["storage_writes"].append({"unit": unit["name"], "function": key[0], "file": rel,
                                                        "line": key[1], "target": key[2]})
            for m in TUPLE_OPEN_RE.finditer(text, r["body"][0], r["body"][1]):
                close = match_close(text, m.start(), "(", ")")
                if close >= r["body"][1] or not TUPLE_EQ_RE.match(text, close + 1):
                    continue
                line = line_of(text, m.start())
                for comp in split_components(text[m.start() + 1:close]):
                    comp = comp.strip()
                    if not comp or DECL_COMPONENT_RE.match(comp):
                        continue
                    base = re.match(r'[A-Za-z_]\w*', comp)
                    if base and base.group(0) in names:
                        key = (r["name"], line, base.group(0))
                        if key not in written:
                            written.add(key)
                            facts["storage_writes"].append({"unit": unit["name"], "function": key[0], "file": rel,
                                                            "line": key[1], "target": key[2]})
    facts["counters"][rel] = counters


def regex_extract(root, files):
    facts = empty_facts(root, "regex")
    parsed = []
    for rel in files:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        text = strip_comments(src)
        parsed.append((rel, src, text, regex_units(rel, text)))
    state_vars = {u["name"]: regex_state_vars(text, u) for _, _, text, units in parsed for u in units}
    parents_of = {u["name"]: u["parents"] for _, _, _, units in parsed for u in units}
    for rel, src, text, units in parsed:
        regex_file(facts, rel, src, text, units, state_vars, parents_of)
        facts["units"] += [{k: v for k, v in u.items() if not k.startswith("_")} for u in units]
    return facts


# ------------------------------------------------------------------ compiler mode

def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            if isinstance(v, (dict, list)):
                yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def load_asts(artifacts_dir, foundry_dir, root):
    asts = {}
    for path in sorted(glob.glob(os.path.join(artifacts_dir, "**", "*.json"), recursive=True)):
        try:
            data = load_json(path)
        except (OSError, ValueError):
            continue
        ast = data.get("ast") if isinstance(data, dict) else None
        if not isinstance(ast, dict) or ast.get("nodeType") != "SourceUnit":
            continue
        abs_path = ast.get("absolutePath", "")
        full = abs_path if os.path.isabs(abs_path) else os.path.join(foundry_dir, abs_path)
        asts.setdefault(os.path.relpath(os.path.normpath(full), root).replace(os.sep, "/"), ast)
    return asts


def base_identifier(expr):
    while isinstance(expr, dict):
        t = expr.get("nodeType")
        if t == "Identifier":
            return expr
        if t == "IndexAccess":
            expr = expr.get("baseExpression")
        elif t == "MemberAccess":
            expr = expr.get("expression")
        else:
            return None
    return None


def is_msg_sender(e):
    return (isinstance(e, dict) and e.get("nodeType") == "MemberAccess" and e.get("memberName") == "sender"
            and (e.get("expression") or {}).get("name") == "msg")


def compiler_extract(root, files, asts):
    facts = empty_facts(root, "compiler")
    state_ids = {}
    for rel in files:
        for node in walk(asts[rel]):
            if (node.get("nodeType") == "VariableDeclaration" and node.get("stateVariable")
                    and not node.get("constant") and node.get("mutability") not in ("immutable", "constant")):
                state_ids[node["id"]] = node["name"]
    for rel in files:
        with open(os.path.join(root, rel), "rb") as fh:
            src = fh.read()

        def line(node, _src=src):
            return _src.count(b"\n", 0, int(node["src"].split(":")[0])) + 1

        counters = new_counters(src.count(b"\n"))
        for node in walk(asts[rel]):
            if node.get("nodeType") == "InlineAssembly":
                counters["assembly_blocks"] += 1
            elif node.get("nodeType") == "UncheckedBlock":
                counters["unchecked_blocks"] += 1
        for contract in asts[rel].get("nodes", []):
            if contract.get("nodeType") != "ContractDefinition":
                continue
            cname, ckind = contract["name"], contract.get("contractKind", "contract")
            start, length = (int(x) for x in contract["src"].split(":")[:2])
            first = line(contract)
            parents = [(b.get("baseName") or {}).get("name") or (b.get("baseName") or {}).get("namePath", "")
                       for b in contract.get("baseContracts", [])]
            facts["units"].append({"name": cname, "kind": ckind, "file": rel, "line": first,
                                   "loc": src.count(b"\n", 0, start + length) + 1 - first + 1, "parents": parents})
            for member in contract.get("nodes", []):
                mt = member.get("nodeType")
                if mt == "FunctionDefinition":
                    kind = member.get("kind", "function")
                    fname = member.get("name") or kind
                    vis, mut = member.get("visibility"), member.get("stateMutability", "nonpayable")
                    guards = [(mi.get("modifierName") or {}).get("name", "") for mi in member.get("modifiers", [])]
                    if mut == "payable":
                        counters["payable"] += 1
                    if (kind != "constructor" and vis in ("external", "public") and member.get("implemented")
                            and ckind != "interface"):
                        facts["entry_points"].append({"unit": cname, "name": fname, "file": rel, "line": line(member),
                                                      "visibility": vis, "mutability": mut, "guards": guards})
                        if mut not in ("view", "pure"):
                            counters["state_writers"] += 1
                    for g in guards:
                        if g.startswith("only"):
                            facts["auth_sites"].append({"unit": cname, "file": rel, "line": line(member),
                                                        "kind": "modifier:" + g})
                elif mt == "ModifierDefinition":
                    fname = member.get("name")
                else:
                    continue
                if not member.get("body"):
                    continue
                written = set()
                for node in walk(member["body"]):
                    t = node.get("nodeType")
                    if t == "BinaryOperation" and node.get("operator") in ("==", "!=") and (
                            is_msg_sender(node.get("leftExpression")) or is_msg_sender(node.get("rightExpression"))):
                        facts["auth_sites"].append({"unit": cname, "file": rel, "line": line(node), "kind": "inline"})
                    elif t == "FunctionCall":
                        expr, opts = node.get("expression") or {}, []
                        if expr.get("nodeType") == "FunctionCallOptions":
                            opts, expr = expr.get("names", []), expr.get("expression") or {}
                        if expr.get("nodeType") == "Identifier" and expr.get("name") in AUTH_CALLS:
                            facts["auth_sites"].append({"unit": cname, "file": rel, "line": line(node), "kind": "inline"})
                        elif expr.get("nodeType") == "MemberAccess" and expr.get("memberName") in CALL_KINDS:
                            kind = expr["memberName"]
                            entry = {"unit": cname, "function": fname, "file": rel, "line": line(node), "kind": kind}
                            facts["external_calls"].append(entry)
                            counters["external_calls"] += 1
                            asset = classify_value(kind, len(node.get("arguments", [])), "value" in opts)
                            if asset:
                                facts["value_transfers"].append(dict(entry, asset=asset))
                    targets = []
                    if t == "Assignment":
                        lhs = node.get("leftHandSide") or {}
                        comps = lhs.get("components", []) if lhs.get("nodeType") == "TupleExpression" else [lhs]
                        targets = [base_identifier(c) for c in comps if c]
                    elif t == "UnaryOperation" and node.get("operator") in ("++", "--", "delete"):
                        targets = [base_identifier(node.get("subExpression"))]
                    for ident in targets:
                        ref = ident.get("referencedDeclaration") if ident else None
                        if ref in state_ids:
                            key = (fname, line(node), state_ids[ref])
                            if key not in written:
                                written.add(key)
                                facts["storage_writes"].append({"unit": cname, "function": fname, "file": rel,
                                                                "line": key[1], "target": key[2]})
        facts["counters"][rel] = counters
    return facts


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract Solidity facts")
    ap.add_argument("--root", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--artifacts")
    ap.add_argument("--foundry-dir")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    files = scope_files(root, load_json(args.pack)["scope"])
    facts = None
    if args.artifacts:
        asts = load_asts(args.artifacts, os.path.abspath(args.foundry_dir or root), root)
        if files and all(f in asts for f in files):
            facts = compiler_extract(root, files, asts)
    if facts is None:
        facts = regex_extract(root, files)
    write_json(args.out, facts)
    print(f"facts: {len(files)} files, mode={facts['mode']} -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
