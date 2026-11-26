# Soroban pack — Sources & Attribution

The Soroban pack's vulnerability classes are ported, with credit, from the sources below. Class IDs
are kept unchanged so findings can be traced back to the source.

## CoinFabrik Scout for Soroban

- Repository: [github.com/CoinFabrik/scout-soroban](https://github.com/CoinFabrik/scout-soroban) (MIT)
- Commit: `53157fd4ddd9e388bf91138699f4e27a500aaef3`
- Ported: the 23 vulnerability classes under `patterns/` (detector and vulnerability docs, test-case
  vulnerable/remediated examples, and the lint text of the two classes without a doc page), and
  `benchmarks/soroban/snippets/cases.jsonl`.

### Scout license

```
MIT License

Copyright (c) 2023 CoinFabrik

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

## Stellar Development Foundation — stellar-dev-skill

- Repository: [github.com/stellar/stellar-dev-skill](https://github.com/stellar/stellar-dev-skill) (Apache-2.0)
- Commit: `9098e8ba24de3299cda24b21bb5cb80aa1cb5d2b`
- Ported: `skills/smart-contracts/security.md` into 11 files under `patterns/` (class 5 extends the
  Scout `INTEGER-OVERFLOW-OR-UNDERFLOW` pattern), sections 1 and 2 of `primers/soroban-vs-evm.md`
  (threat model, what the platform rules out), code examples from the same guide, and the
  heuristics in `heuristics.md` (added in a later task).
- Modifications: ChainSec modified this material: reorganized into per-class files, rewrote
  detection/FP/test sections, added Soroban engine mappings.
- License: the full Apache License 2.0 text is in [LICENSE-APACHE-2.0.txt](LICENSE-APACHE-2.0.txt),
  unchanged from the upstream `LICENSE`.
