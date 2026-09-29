# Kill gates and the Impact Premise

Applied by the verify phase to every candidate, and as a pre-filter by detection phases.
Before applying gates, read the pack's fp-patterns.md, section "Gate overrides and examples".

## Step 0: Automatic kill gates

**This gate runs FIRST. Any finding matching ANY of these 8 categories is IMMEDIATELY killed. No exploit trace is attempted. No further analysis. No exceptions. No "but in this case...". KILL IT.**

These 8 categories account for 95%+ of all false positives across 40 shadow audits and have NEVER produced a true positive. They are unconditional kills.

In ChainSec a gate kill is `status: killed` with `verdict.gate` set to the gate letter (see `engine/verdicts.md`).

### Gate A — Generic Best Practice (kill immediately)
"Use a safe-transfer wrapper" without naming specific failing token, "safe approval" generically, "single-step ownership", "missing event emission", "fixed-gas native transfer" without specific failing recipient, "weak on-chain randomness", "use a deadline" without concrete MEV profit calc, "centralization risk". Chain-specific examples: the pack's fp-patterns.md "Gate overrides and examples", Gate A.
→ **KILL. Zero TPs in 40 contests.**

### Gate B — Theoretical But Not Exploitable (kill immediately)
Requires exotic token behavior not in protocol's actual token list, oracle returning out-of-range values, overflow in practically bounded values, condition prevented by deployment/init. **TOKEN CONTEXT CHECK**: Finding relying on token behavior MUST name the SPECIFIC token from the protocol's actual list. "If a fee-on-transfer token is used" without naming which one = KILL. **DECIMAL/INTERFACE EDGE CASES**: Only matters if it affects actual token pairs the protocol uses.
→ **KILL. Zero TPs in 40 contests.**

### Gate C — Design Is Intentional (kill immediately)
Code comments/docs indicate deliberate behavior, same pattern as reference implementation (Uniswap V3, Curve, etc.), function works as NatSpec describes. **FORK BEHAVIOR CHECK**: If Recon identified a fork, check if original has same behavior → inherited design, not bug. Only report code that DIFFERS from fork origin.
→ **KILL. Zero TPs in 40 contests.**

### Gate D — Speculative / No Concrete Exploit (kill immediately)
"Could be an issue if...", cannot specify WHO/WHAT/HOW MUCH, vague "manipulation" without exact path, "stale data" without exploitable window.
→ Ask: "Can I write `1. Attacker calls X 2. State becomes Y 3. Profit Z`?" If no → **KILL.**

### Gate E — Admin Trust Boundary (kill immediately)
Requires trusted admin/owner/governance to act maliciously. EXCEPTION: Missing timelock on irreversible destructive action may qualify as Medium.
→ **KILL. Zero TPs in 40 contests.**

### Gate F — Dust / Economically Insignificant (kill immediately)
Rounding < $1/tx, bounded truncation dust, precision loss < gas costs. If max_loss × max_iterations < $100 = dust.
→ **KILL. Zero TPs in 40 contests.**

### Gate G — Out of Context (kill immediately)
Token behaviors for tokens not in whitelist, chain-specific issues on unsupported chains, standards the protocol doesn't implement, external protocols not integrated with.
→ **KILL. Zero TPs in 40 contests.**

### Gate H — Publicly Known / Acknowledged Issue (kill immediately)
Already listed in README "Known Issues", previous audit reports, or bot reports. **PRECISION REQUIREMENT**: Match on MECHANISM, not TOPIC. "SOFT_RESTRICTED bypass via open market" ≠ "SOFT_RESTRICTED bypass via withdraw()". Two bugs in same area with different exploit paths are different bugs. Only kill if known issue describes SAME entry point, SAME root cause, SAME impact.
→ **KILL if exact mechanism match. DO NOT KILL if only same topic but different path.**

### DoS exception (applies to Gates A, B, D, F)
If DoS permanently/repeatedly bricks a CORE lifecycle function (settlement, liquidation, withdrawal, unstaking, repayment, auction) AND unprivileged attacker can trigger at low cost AND effect is persistent → Medium minimum, survives A/B/D/F. 25% of missed findings were DoS bugs incorrectly killed.

## Gate F in chain units

Gate F thresholds are in USD. Convert on-chain amounts with the pack's `value_unit`
(`amount / 10^decimals` native units) and a price stated in `recon.md`; if recon recorded no
price, state the assumed price in `verdict.reason`.

## Step 0.5: Impact Premise

*(Source: PlamenTSV/plamen, MIT — `phase5-poc-execution.md` § Impact Premise Verification)*

Gate D kills "speculative" findings, but "speculative" is a judgement call. This step makes it mechanical.

Before you trace anything, write the candidate's claimed **HARM in ONE sentence**: **WHO loses WHAT.** Not the mechanism — the consequence.

**Mechanism statements — INSUFFICIENT. These describe machinery, not damage:**
- "`startLiquidation` succeeds while the market is active" — proves a call is possible, not that anyone loses
- "the parameter can be set to zero" — proves a setter works, not that zero causes harm
- "the reentrancy callback is triggered" — proves a callback fires, not that state corrupts
- "state is corrupted" / "a guard is missing" / "the function is callable" / "value diverges" — all machinery

**Harm statements — REQUIRED:**
- "claimants receive 15% less than their pro-rata share after the attack sequence"
- "a user's withdrawal reverts permanently once the parameter is set to zero"
- "the attacker extracts 1.5x their fair share before the guard triggers"
- "any peer can permanently halt settlement for all borrowers"

**Decision:**

| Outcome | Action |
|---|---|
| You can write a harm statement naming a **specific user class** AND a **specific fund / liveness / privilege / accounting consequence** | Record it as `Harm` and proceed to verification |
| You can only describe machinery | **KILL under Gate D.** Record `Harm: MECHANISM-ONLY` |

In ChainSec, `Harm` is the finding's `harm` object (`who`, `loses_what`, `magnitude`). A kill here
is `status: killed`, `verdict.gate: impact-premise`, with `verdict.reason` starting
`Harm: MECHANISM-ONLY`.

"Could be exploited", "may be unsafe", and "is dangerous" are not harm statements. A finding whose only stated harm is a mechanism is not a finding.

**Note on scope**: this gate tests whether a *consequence was stated*, not whether it was *proven*. Proving it is Step 1–3's job. Do not use this gate to kill a finding that names real harm but hasn't yet traced it.

## Detection pre-filter

Do NOT generate candidates for these (automatic kills).

These 8 categories have produced ZERO true positives across 35 shadow audits. Do NOT waste time generating candidates in these categories. They WILL be killed by the Critic.

**A. Generic Best Practice** — Do NOT report: safe-transfer wrapper usage, safe approval, two-step ownership, missing events, fixed-gas native transfers, weak on-chain randomness, generic deadline concerns, centralization risks. These are informational at best. Chain-specific examples: the pack's fp-patterns.md "Gate overrides and examples", Gate A.

**B. Theoretical/Unrealistic** — Do NOT report findings requiring: exotic token behaviors not in the protocol's actual token list, oracle values outside documented range, integer overflow of practically bounded values, conditions prevented by deployment/initialization, fee-on-transfer behavior when protocol uses WETH/USDC/DAI. **For ANY token-behavior finding (FoT, rebasing, missing return, hooks), you MUST name the SPECIFIC token from THIS protocol's actual deployment that exhibits the behavior. "If a FoT token is used" = kill.**

**C. Intentional Design** — Do NOT report: behavior matching documentation/comments, patterns from reference implementations (UniV3, Curve, DODO, and the standard libraries named in the pack's fp-patterns.md "Gate overrides and examples", Gate C), intentionally permissionless functions, features working as spec'd. **If this is a FORK, behavior inherited from the original protocol is intentional design — only report bugs in code that DIFFERS from the fork origin.**

**D. Speculative** — Do NOT report anything where you cannot immediately state: WHO is the attacker, WHAT function they call with WHAT params, and HOW MUCH they profit. "Could be an issue" = not a candidate.

**E. Admin Trust** — Do NOT report: "owner can set bad value", "admin can drain", "governance can rug". Unless: missing timelock on irreversible destructive action.

**F. Dust** — Do NOT report: rounding where max loss < $1 per tx, truncation dust, precision loss below gas cost.

**G. Out of Context** — Do NOT report: token behaviors for tokens not whitelisted, chain issues for unchosen chains, standard edge cases for unimplemented standards.

**H. Publicly Known Issues** — Do NOT report: any bug mechanism already described in the README's "Known Issues", "Acknowledged", or "Publicly Known Issues" sections, or in linked previous audit acknowledgments, or in the automated/bot report section. Read the README BEFORE generating candidates.
