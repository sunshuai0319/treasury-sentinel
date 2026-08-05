# KeeperHub Starter Kit

The reusable part of this project is intentionally small:

- `apps/api/app/integrations/keeperhub.py` wraps KeeperHub execution calls.
- `apps/api/app/agent/demo.py` shows the minimum Primary/Critic/Final shape.
- `contracts/contracts/TreasuryGuard.sol` gives a guarded contract target.
- `scripts/live_keeperhub_check.py` is the place to adapt the exact KeeperHub API payload.
- `starter-kit/scripts/check_environment.py` checks local dependencies and fails closed when KeeperHub is not configured.

The hackathon onboarding story is: generate policy data, evaluate locally, deploy
the guarded contract, then let KeeperHub call the contract instead of exposing a
private key to the agent.
