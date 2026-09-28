# ChainSec — Sources & Attribution

ChainSec's engine, Solidity pack and DeFi domain content are derived from Krait by Zealynx Security under the MIT License, relocated into a multi-chain layout.

## Krait license

```
MIT License

Copyright (c) 2025-2026 Zealynx Security

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

## Sources integrated by Krait

# Detection Sources

Krait's detection layer combines original research with curated knowledge from the open-source security community. The detection content below is integrated from MIT-licensed repositories.

| Source | What We Integrated | License | Link |
|--------|-------------------|---------|------|
| **pashov/skills** | ~100 attack vectors across 8 modules + 58 extended heuristics | MIT | [github.com/pashov/skills](https://github.com/pashov/skills) |
| **PlamenTSV/plamen** | Devil's Advocate verification methodology, cross-cutting analysis perspectives | MIT | [github.com/PlamenTSV/plamen](https://github.com/PlamenTSV/plamen) |
| **forefy/.context** | Protocol-type context enrichment across 7 primers (10,600+ findings distilled) | MIT | [github.com/forefy/.context](https://github.com/forefy/.context) |

The `krait-poc` skill (Foundry exploit PoC construction) derives its patterns from
additional corpora, including the Apache-2.0 **DeFiHackLabs**; those sources and the
license reasoning are documented separately in
[chains/solidity/poc/ATTRIBUTION.md](chains/solidity/poc/ATTRIBUTION.md). No
third-party Solidity is vendored — only facts derived from analyzing the corpora.

## What's Original to Krait

- Full audit pipeline architecture (recon → detect → state analysis → verify → report)
- 8 kill gates with zero-FP track record across 45 contests
- Deterministic file risk scoring formula
- Module trigger system (tier 0/1/2 with evidence-based activation)
- Shadow audit benchmarking methodology and self-improvement loop
- 43 original heuristics derived from missed findings in blind contest testing
- Consensus scoring across multi-lens, multi-mindset analysis

Built by [Zealynx Security](https://zealynx.io).
