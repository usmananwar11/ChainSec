# L1↔L2 Messaging Module

> **Trigger**: Protocol sends or receives L1↔L2 messages (`#[l1_handler]`, `send_message_to_l1_syscall`)
> **Inject into**: Lens C (External/Cross-contract)
> **Priority**: HIGH — an unchecked handler mints for anyone; a stuck message locks bridged funds
> <!-- Ported from keep-starknet-strange cairo-auditor (MIT): bridging notes and attack vectors 29, 35, 36, 91, 97, 136, 137, 139, 141, 144; see ATTRIBUTION.md -->

Chain-specific half of `domains/defi/modules/cross-chain-bridge.md` for Starknet's native messaging.

## 1. How Messaging Works

- **L1 → L2**: an L1 contract calls the Starknet core contract's `sendMessageToL2(to_address, selector, payload)`. The sequencer later invokes the `#[l1_handler]` function named by `selector` on `to_address`, passing the L1 sender as the first argument `from_address: felt252`, then the payload. Each message is consumed once (its hash includes a nonce); the L1 sender can cancel an unconsumed message after a delay.
- **L2 → L1**: `send_message_to_l1_syscall(to_address, payload)` records a message; once the block is proven, the L1 contract consumes it with `consumeMessageFromL2(from_address, payload)`, which checks the L2 sender and the payload hash.

## 2. Handler Authentication

| `#[l1_handler]` | `from_address` compared to | Stored value set & non-zero? | Effects |
|---|---|---|---|

- Missing or wrong `from_address` check → anyone on L1 can send the message and trigger the handler's effects (L1H-01).
- `from_address` is `felt252`; a stored `EthAddress` or `ContractAddress` needs an explicit conversion before comparison.
- The trusted L1 address can be changed: by whom, with what delay (AV-98)?
- `get_caller_address()` inside a handler does not identify the L1 sender (CALLER-01).

## 3. Payload Encoding

- Field order and types must match the L1 encoder exactly: `u256` amounts arrive as two felts (low, high); addresses as felts (U256-01, MSG-03).
- Recipient from L1 converted to `ContractAddress` and validated; an invalid or zero recipient must not panic the handler without a recovery path.
- One canonical preimage encoding for any message hash shared across domains (AV-144).
- Payload and array sizes bounded (AV-141).

## 4. Failure and Recovery

- A handler that reverts does not deliver the L2 effect while L1 state (locked/burned funds) has changed (L1H-02). List every input-dependent revert in each handler: pause, cap, blacklist, decode panic, zero recipient.
- Is there an L1 path to reclaim funds (message cancellation) and is it reachable by the depositor?
- One malformed message must not block processing of others (AV-136).

## 5. Outbound (L2 → L1)

- Burn/lock on L2 happens before `send_message_to_l1_syscall` and before success events (AV-97).
- `to_address` is the intended L1 contract, non-zero, and not caller-controlled.
- Withdrawal rate limits / circuit breaker for high-TVL bridges (AV-139; StarkGate's daily limit pattern).

## 6. Replay and Lifecycle

- Native L1→L2 messages are single-use, but custom relayed or app-level messages need a replay key with the full identity — sender, nonce, amount, domain (AV-29, AV-91).
- Cancellation or pending timestamps not overwritable by repeated calls (AV-35, AV-165).
- Multi-step token activation (deploy, register, configure) cannot be front-run between steps (AV-137).
