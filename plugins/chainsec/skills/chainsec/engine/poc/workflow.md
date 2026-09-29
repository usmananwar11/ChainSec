# PoC workflow — exploit proof-of-concept

You write tests that **prove exploitation mechanically**. A finding backed by a
passing PoC is ground truth; a finding backed by prose is a hypothesis. Your job is to
move findings from the second category to the first — or to honestly fail them.

This workflow is standalone. It is invoked directly ("write a PoC for X", "reproduce the Y
hack", `chainsec-poc <ID>`) or by the ChainSec audit pipeline's verification phase to harden a
`[CODE-TRACE]` finding into a `[POC-PASS]`.

The test framework, commands and harness come from the chain pack: `pack.json` `poc.framework`,
`poc.run` and `poc.guide` (the guide lives at `chains/<chain>/<poc.guide>`). Wherever a step
below says *(pack: …)*, read the pack's poc guide for that step.

**Output location:** everything a PoC run produces (test files, run logs, fix diffs) goes in
`.audit/<chain>/poc/<ID>/`.

## The one rule that matters: assert HARM, not mechanism

A PoC that proves a function *can be called*, a state *can be reached*, or a path *exists*
is **not** a valid PoC. It must assert the **consequence** — who loses what.

| Mechanism assertion (INVALID) | Harm assertion (REQUIRED) |
|---|---|
| `startLiquidation` succeeds while market active | victim's collateral balance drops by X with no repayment |
| attacker can call `setPrice()` | attacker's post-balance − pre-balance ≥ profit, funded by the pool |
| reentrancy callback fires | attacker withdrew 1.5× their deposit before the guard tripped |

Concretely: snapshot the balance/state that represents the loss **before** the attack,
run the attack, assert the delta is the claimed harm. The `balanceLog`-style before/after
pattern *(pack: see the pack's poc guide, pack.json poc.guide — its harness reference)* exists
for exactly this.

If you cannot write a harm assertion, the finding is `[CODE-TRACE]` at best — say so, do
not dress a mechanism test up as a proof.

## The second rule: a green test is a hypothesis, not a proof

You wrote the test to confirm a finding you already believe, so it will build the world where
the finding is true. `[POC-PASS]` is earned only when the passing exploit survives the
**falsification gate** (Step 7): the defective line, changed to correct, must make the exploit
die. Assert harm (rule one) *and* prove the test is pinned (rule two) — both, or it is no pass.

## Two modes

- **Single finding** (the default) — prove or disprove one suspected bug. Follow the
  workflow below.
- **Batch triage** — verify a *list* of findings → one consolidated verdict table. Whenever
  the target is more than one finding, read `engine/poc/batch-triage.md` and follow it; it
  wraps this workflow with a PoC-ability triage and the table format.

Both modes obey the same evidence rule: a passing PoC promotes a finding, a failing PoC
demotes it, and **inability to PoC does neither** — some valid findings are un-PoC-able by
nature and must keep their severity.

### Triage lanes

From `engine/poc/batch-triage.md` Step 1 — classify each finding before spending any build budget:

| Lane | Meaning | Action |
|------|---------|--------|
| **TESTABLE** | Concrete on-chain harm, reachable from an entry point, buildable env | Full 8-step workflow. Budget attempts. |
| **STRUCTURAL** | Real finding, but no executable on-chain harm assertion exists | Do NOT attempt a PoC. Record `[CODE-TRACE]` + the structural reason. Keep severity. |
| **BLOCKED** | Testable in principle, but this environment can't (no build, no fork RPC, external dep) | Record `[CODE-TRACE]` + the environmental blocker. Keep severity. Re-runnable elsewhere. |
| **NO-HARM** | Only a mechanism stated, no consequence | Flag for the author. Not a PoC target. |

## Workflow (single finding)

Follow these steps in order. Each references a file you load only when you reach it —
keep this top-level file in context, pull the rest on demand.

### 1. Recon the target's PoC environment (MANDATORY — gates everything)

**Do not write a line of test code until you have profiled the repo.** A PoC written blind
wastes the 5-attempt compile budget rediscovering setup the project already solved. Produce a
PoC environment profile: build system and config, whether it compiles as-is (if not, resolve it
or record `NO_BUILD_ENVIRONMENT` — you cannot PoC a project that does not build), existing test
conventions to REUSE, the **deployment shape** of the in-scope code, the **external
dependencies** it calls live, and **fork feasibility** — is an RPC actually reachable? If a fork
is required and none is, that is `[CODE-TRACE: NO_FORK_RPC]` (BLOCKED, not FAIL) — decide it
here, not after five blind attempts. *(pack: see the pack's poc guide, pack.json poc.guide)*

This step's output — the profile and the harness choice — feeds every step below.

### 2. Choose the harness: local, fork, or hybrid

The recon produces this decision. It is NOT "audit finding = local, incident = fork":

- **local** — in-scope contracts are self-contained and external deps are mockable. Deploy
  fresh instances.
- **fork** — the harm depends on a **live external contract's real state** (oracle price,
  AMM reserves, a deployed integration), OR you are reproducing an incident, OR the target
  is already deployed. Fork at a pinned block.
- **hybrid** — in-scope logic is the bug but it reads from a live dependency you cannot mock
  trustworthily: fork the chain for the dependency, deploy fresh in-scope contracts on top.

**Fork testing is frequently necessary for in-scope audit findings, not just incident
replay** — any finding whose harm routes through a real oracle/AMM/integration usually needs
a fork, because a hand-written mock of that dependency is exactly where a false positive
hides. When torn between a faithful fork and a convenient mock, fork.
*(pack: see the pack's poc guide, pack.json poc.guide)*

### 3. Gather the concrete facts

Collect the real values the harness needs: the chain + a **pinned** block; every contract
address you touch; **real function signatures read from deployed source or ABI, never
guessed**; the attacker's funding source (a test-framework balance grant or a flash loan,
step 5). Every address and selector must come from a source you actually read (a block
explorer, the repo, an RPC call) — a made-up signature is the #1 cause of a PoC that "should
work" but doesn't compile. *(pack: see the pack's poc guide, pack.json poc.guide)*

### 4. Build the skeleton and instantiate the target

Use the pack's harness: the balance-logging base, the fork or local deploy in the test setup,
the attack in the exploit test. Instantiate the in-scope contract per its **deployment
shape** — reuse the project's own deploy script / base fixture rather than hand-rolling a
constructor call. On a fork, the system is already deployed: bind the known addresses to their
interfaces. Label every address (unreadable traces waste more time than they save).
*(pack: see the pack's poc guide, pack.json poc.guide)*

### 5. Wire the money

Most real exploits are flash-loan-funded (36% of the corpus). If the attack needs capital it
does not have, use a flash loan and **match the callback to the provider** — mismatching it is
the second most common compile failure. If the attacker uses its own capital, grant it the
balance through the test framework. *(pack: see the pack's poc guide, pack.json poc.guide)*

### 6. Compile → run → fix (the loop)

Build, then run the test with the pack's `poc.run` command and your test filter. On failure,
use the pack's debug ladder (error class → fix). **Max 5 compile attempts, then fall back to
`[CODE-TRACE]`** — do not grind forever on a setup that will not build.
*(pack: see the pack's poc guide, pack.json poc.guide)*

If the test compiles and runs but the harm assertion fails, apply
`engine/poc/assertion-protocol.md` before concluding `[POC-FAIL]`.

### 7. Falsification gate — prove the PoC is pinned, not theater (MANDATORY when the exploit passes)

**Do not record `[POC-PASS]` on a green test alone.** The reasoning that produced the finding
produced the test, so it will build the exact world where the finding is true. Read
`engine/poc/falsification-gate.md` and run its two controls — they answer different questions:

- **Defect-mutation (the honest pin)**: change the *defective line itself* to correct, re-run the
  unchanged exploit. Survives → `[POC-UNPINNED]` (theater → `[CODE-TRACE]`). Dies → the bug is
  real, settled independent of any fix. Cross-check with a negative/baseline control (the C-01 move).
- **Fix-efficacy (separate verdict)**: only after the pin holds, apply the *recommended fix* and
  **fuzz the parameter it constrains** (not just re-run the literal exploit — that is
  tautological when the fix bounds the value the exploit sets). Whole neighborhood clean → fix
  verified. Any variant still reproduces → `FIX-INSUFFICIENT` — real, pinned, fix doesn't close it.

Never iterate a candidate fix against a single exploit test (theater again); derive a better fix
from the mutation, validate it under a fuzz sweep, cap at 2, hand to human review. Recursion-trap
rules are in the reference.

### 8. Assign the evidence tag

| Tag | Meaning |
|---|---|
| `[POC-PASS]` | Exploit passed **and** the gate held: defect-mutation killed it (pinned), fix killed it (verified). |
| `[POC-PASS · FIX-INSUFFICIENT]` | Pinned, but the proposed fix does **not** close it. Bug real; remediation flagged. A finding, not a demotion. |
| `[POC-UNPINNED]` | Exploit passed but the defect-mutation did **not** kill it — not pinned to the cited defect. → `[CODE-TRACE]`, flag for review. |
| `[POC-FAIL]` | Ran, harm assertion failed. The attack does not work as described (overturn only via `engine/poc/assertion-protocol.md`). |
| `[CODE-TRACE]` | Could not execute (no build env / dep / fork RPC / ≥5 compile fails). Never supports CONFIRMED, never counts *against* the finding. |

`[POC-FAIL]` and `[POC-UNPINNED]` are real results — they protect you from reporting a bug your
own test only appeared to prove.

After a run, set the finding's `verdict.evidence_tag` to the tag in
`.audit/<chain>/findings.json` (and in `TARGET/.audit/findings.json` when it exists). How the
report renders each tag is in `engine/verdicts.md`.

### 9. Report the result and the fix

Write up the finding with its gate outcome. For a `[POC-PASS]`, include the verified fix diff;
for `[POC-PASS · FIX-INSUFFICIENT]`, include the exploit surviving the fix and what a correct
fix must change (from the mutation spec). Read `engine/poc/fix-and-report.md` for the block.

## Reference files

Load these as the workflow directs — do not read them all up front.

| File | When |
|------|------|
| the pack's poc guide (`poc.guide`) and the references it lists | Steps 1–6 — environment, harness, funding, build/run/debug |
| `engine/poc/falsification-gate.md` | Step 7 — defect-mutation + fix-efficacy: pin vs. theater |
| `engine/poc/assertion-protocol.md` | Step 6/7 — one-retry protocol; variant sweep dimensions |
| `engine/poc/fix-and-report.md` | Step 9 — fix diff + report block format |
| `engine/poc/batch-triage.md` | Batch mode — verify a list of findings → verdict table |

## Boundaries

- **Local forks only.** These PoCs run against local forks of public chains for
  verification. Do not construct anything intended to execute against live systems, and do
  not include private keys, real funding, or deployment steps.
- **Do not weaken an assertion to force a pass.** If the harm does not reproduce, that is
  `[POC-FAIL]`. Changing what you assert until it goes green is fabrication.
- Attribution and sources for the mined patterns are in the pack's poc ATTRIBUTION file.
