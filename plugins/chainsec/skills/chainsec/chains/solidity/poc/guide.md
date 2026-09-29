# Solidity PoC guide (Foundry)

Follow engine/poc/workflow.md; this file supplies the Foundry specifics.

## Foundry workflow steps

### 1. Recon the target's PoC environment (MANDATORY — gates everything)

**Do not write a line of test code until you have profiled the repo.** A PoC written blind
wastes the 5-attempt compile budget rediscovering setup the project already solved. Read
`chains/solidity/poc/references/environment-recon.md` and produce its PoC environment profile:

- Build system + `foundry.toml` / `remappings.txt` (evm_version, remappings, rpc endpoints).
- **Does it compile as-is?** Run `forge build` first. If not, resolve it or record
  `NO_BUILD_ENVIRONMENT` — you cannot PoC a project that does not build.
- **Existing test conventions to REUSE** — a shared `BaseTest`/`Setup`, deploy scripts in
  `script/` (real constructor args live there), existing mocks, and whether the project's
  own tests already fork. Reusing these is where most compile failures are avoided.
- **Deployment shape** of the in-scope contract (plain / proxy / factory / diamond / multi-
  contract / init-sequence) — dictates how `setUp()` must build it.
- **External dependencies** the target calls live (oracle, AMM, lending, bridge).
- **Fork feasibility** — is an RPC actually reachable? If a fork is required and none is,
  that is `[CODE-TRACE: NO_FORK_RPC]` (BLOCKED, not FAIL) — decide it here, not after five
  blind attempts.

This step's output — the profile and the harness choice — feeds every step below.

### 2. Choose the harness: local, fork, or hybrid

The recon produces this decision (full framework in `environment-recon.md`). It is NOT
"audit finding = local, incident = fork":

- **local** — in-scope contracts are self-contained and external deps are mockable. Deploy
  fresh instances. Read `chains/solidity/poc/references/local-harness.md` + `chains/solidity/poc/references/deploy-shapes.md`.
- **fork** — the harm depends on a **live external contract's real state** (oracle price,
  AMM reserves, a deployed integration), OR you are reproducing an incident, OR the target
  is already deployed. Fork at a pinned block. Read `chains/solidity/poc/references/fork-setup.md` (and
  `chains/solidity/poc/references/reproduce-incident.md` for a known hack).
- **hybrid** — in-scope logic is the bug but it reads from a live dependency you cannot mock
  trustworthily: fork the chain for the dependency, deploy fresh in-scope contracts on top.

**Fork testing is frequently necessary for in-scope audit findings, not just incident
replay** — any finding whose harm routes through a real oracle/AMM/integration usually needs
a fork, because a hand-written mock of that dependency is exactly where a false positive
hides. When torn between a faithful fork and a convenient mock, fork.

### 3. Gather the concrete facts

Collect the real values the harness needs: the chain + a **pinned** block; every contract
address you touch; **real function signatures read from deployed source or ABI, never
guessed**; the attacker's funding source (`deal` or a flash loan, step 5). Every address and
selector must come from a source you actually read (Etherscan, the repo, a `cast` call) — a
made-up signature is the #1 cause of a PoC that "should work" but doesn't compile.

### 4. Build the skeleton and instantiate the target

Use the harness in `chains/solidity/poc/references/harness.md`: inherit the balance-logging base, set up the
fork or local deploy in `setUp()`, put the attack in `testExploit()`. Instantiate the
in-scope contract per its **deployment shape** (`chains/solidity/poc/references/deploy-shapes.md`) — reuse the
project's own deploy script / base fixture rather than hand-rolling a constructor call. On a
fork, the system is already deployed: cast the known addresses to their interfaces. `vm.label`
every address (the corpus's most-used cheatcode — unreadable traces waste more time than they save).

### 5. Wire the money

Most real exploits are flash-loan-funded (36% of the corpus). If the attack needs capital it
does not have, read `chains/solidity/poc/references/flashloan.md` and **match the callback to the provider**
(`executeOperation`=Aave, `receiveFlashLoan`=Balancer, `uniswapV2Call`/`pancakeCall`=V2 pair,
`DPPFlashLoanCall`=DODO) — mismatching it is the second most common compile failure. If the
attacker uses its own capital, `vm.deal` (native) / `deal(token, addr, amt)` (ERC-20) funds it.

### 6. Compile → run → fix (the loop)

Run `forge build`, then `forge test --match-test <name> -vvv` from the project root (use `-vvvv`
for full traces). If Krait's forge MCP server is installed, its `forge_build` / `forge_test`
tools are an equivalent sandboxed alternative.

On failure, read `chains/solidity/poc/references/debug-ladder.md` — it maps every common error class to its fix
(missing interface, wrong constructor args, stale signature, fork RPC issue, `-vvvv` trace
reading). **Max 5 compile attempts, then fall back to `[CODE-TRACE]`** — do not grind
forever on a setup that will not build.

## Reference files

Load these as the workflow directs — do not read them all up front.

| File | When |
|------|------|
| `chains/solidity/poc/references/environment-recon.md` | Step 1 — profile the target's build/test/deploy env (gating) |
| `chains/solidity/poc/references/deploy-shapes.md` | Step 4 — instantiate proxy/factory/diamond/multi-contract targets |
| `chains/solidity/poc/references/harness.md` | Step 4 — the base test contract + balance-log pattern |
| `chains/solidity/poc/references/fork-setup.md` | Step 2/4 — fork cheatcodes, chain aliases, pinning a block |
| `chains/solidity/poc/references/local-harness.md` | Step 2/4 — PoC against in-scope source, no live deployment |
| `chains/solidity/poc/references/reproduce-incident.md` | Step 2 — sourcing address/block/tx for a known hack |
| `chains/solidity/poc/references/flashloan.md` | Step 5 — provider callback signatures + liquidity sources |
| `chains/solidity/poc/references/cheatsheet.md` | Any step — the cheatcodes real PoCs actually use, ranked |
| `chains/solidity/poc/references/debug-ladder.md` | Step 6 — error class → fix, ordered by frequency |
