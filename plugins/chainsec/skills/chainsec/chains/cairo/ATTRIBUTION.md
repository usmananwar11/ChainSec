# Cairo pack — Sources & Attribution

The Cairo pack's security knowledge is ported, with credit, from the **cairo-auditor** skill of
keep-starknet-strange's `starknet-agentic` (MIT), version 1.0.4 as distributed through the
`starknet-agentic-skills` plugin. Vulnerability-class IDs and attack-vector numbers are kept
unchanged so findings can be traced back to the source.

| Source | License | Link |
|--------|---------|------|
| **keep-starknet-strange/starknet-agentic** — `skills/cairo-auditor/` | MIT | [github.com/keep-starknet-strange/starknet-agentic](https://github.com/keep-starknet-strange/starknet-agentic) |

## starknet-agentic license

```
MIT License

Copyright (c) 2026 Keep Starknet Strange

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## What was ported

| ChainSec file | Source (`skills/cairo-auditor/`) | How |
|---|---|---|
| `patterns/<ID>.md` (28 files) | `references/vulnerability-db/<ID>.md` | Ported: content kept, headings normalized, ChainSec header added (lens, related vectors, module) |
| `patterns/README.md` | `references/vulnerability-db/README.md` | Adapted: index with lens and category |
| `heuristics.md`, "Extended heuristics" | `references/attack-vectors/attack-vectors-{1..4}.md` | Ported: all 170 vectors, numbers kept as `AV-<n>`, one line each |
| `heuristics.md`, core heuristics and additions | `references/audit-findings/source-cairo-security-import.md`, `references/judging.md` | Adapted: rewritten as ChainSec heuristics with new IDs (FELT, INT, U256, MAP, CALLER, L1H, MSG, UPG, LIBC, DISP, REENT, AA, SIGN, COMP, INIT, DEPLOY, GUARD, TIME, PRIV, BOOL) |
| `fp-patterns.md` | `references/judging.md` ("Do Not Report", Cairo-specific notes), vuln-db false-positive caveats | Adapted to ChainSec FP-3/7/8/9 and gates |
| `modules/*.md`, `primers/starknet-vs-evm.md` | `references/audit-findings/source-cairo-security-import.md`, attack vectors, vuln DB | Adapted: reorganized into ChainSec lens modules |

The source's own citations (Code4rena, ConsenSys Diligence, ChainSecurity, Nethermind, Cairo Book,
Crytic, OpenZeppelin, SNIPs) are referenced by name where a finding is used as an example.

## Not ported

- cairo-auditor's orchestration (`SKILL.md`, `workflows/`, `agents/`), report formatting, scripts,
  Semgrep rules, evals and its confidence-score rubric: ChainSec's engine provides its own pipeline,
  kill gates and report.
- `references/checklists/release-gate.md` (a release gate for cairo-auditor's own benchmark).

## Original to ChainSec

`pack.json`, the `recon/` extractor, clustering and Caracal summary, the PoC and fuzz guides,
`module-triggers.md`, and the mapping of the ported content onto ChainSec's lenses, gates and IDs.
