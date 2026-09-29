---
name: chainsec
description: ChainSec core library (audit engine, chain packs, DeFi domain knowledge, prompts, scripts) used by the chainsec-* skills. Do not invoke directly; use chainsec-audit, chainsec-review, chainsec-poc, chainsec-fuzz or chainsec-init.
user-invocable: false
disable-model-invocation: true
---

# ChainSec core

This folder is loaded by the `chainsec-*` entry skills; it is not a workflow on its own.
All paths below are relative to this folder.

| Folder | Contents |
|---|---|
| `engine/` | Pipeline, phase instructions, kill gates, verdicts, schemas, report template, PoC and fuzz method |
| `prompts/` | Subagent briefs filled in by the pipeline |
| `runtimes/` | How to dispatch subagents in each tool |
| `domains/defi/` | Chain-agnostic DeFi modules, primers, heuristics, triggers |
| `chains/<chain>/` | Chain packs; `pack.json` is the contract (`engine/pack.schema.json`) |
| `scripts/` | detect-chain, score-risk, validate-findings, merge-findings (Python 3 stdlib) |

Start at `engine/pipeline.md`. Attribution: ATTRIBUTION.md.
