# Known issues (README, pre-contest)
- Oracle liveness/staleness is not checked in contracts (Aave lending pool would fail on stale/zero feed anyway).
- Side effects when lending-pool supply of tokens is drained by borrowing → positions that can't be closed (team knows how to handle).
- Bot-race/automated findings (gist) are publicly known and ineligible; gist content NOT accessed (external). Treat generic bot-style findings (floating pragma, missing zero checks, unsafe ERC20 transfer, centralization/owner privileges, missing events) as likely known.
- Aave lending pool fork is out of scope.
