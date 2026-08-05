import json
from pathlib import Path

from app.agent.demo import run_demo_scenario

SCENARIOS = ["normal", "duplicate", "address_mismatch", "over_limit", "pause"]
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo-script.md"
DEPLOYMENT = ROOT / "contracts" / "deployments" / "base-sepolia.json"


def main() -> None:
    deployment = json.loads(DEPLOYMENT.read_text()) if DEPLOYMENT.exists() else {}
    runs = [run_demo_scenario(name) for name in SCENARIOS]
    lines = [
        "# Treasury Sentinel Demo Script",
        "",
        "This file is generated from the deterministic local demo runner.",
        "",
        "## Base Sepolia contracts",
        "",
        f"- TreasuryGuard: `{deployment.get('treasuryGuard', 'not recorded')}`",
        f"- MockUSDC: `{deployment.get('mockUsdc', 'not recorded')}`",
        f"- Chain ID: `{deployment.get('chainId', 84532)}`",
        "",
        "## Scenario order",
        "",
    ]
    for index, run in enumerate(runs, start=1):
        lines.extend(
            [
                f"{index}. `{run.scenario}` → `{run.final_action}`",
                f"   - Request: `{run.request_id}`",
                f"   - Invoice: `{run.invoice_id}`",
                f"   - Final reasons: {'; '.join(run.timeline[-1].reasons)}",
                f"   - Policy refs: {', '.join(run.timeline[-1].policy_refs)}",
            ]
        )
    lines.extend(
        [
            "",
            "## KeeperHub / transaction evidence",
            "",
            (
                "Live KeeperHub execution is intentionally blocked until `KEEPERHUB_API_KEY` and "
                "`KEEPERHUB_WALLET_ADDRESS` are configured. Do not replace this section with mock tx hashes."
            ),
        ]
    )
    OUTPUT.write_text("\n".join(lines) + "\n")
    print(json.dumps({"scenarios": len(runs), "output": str(OUTPUT), "ok": True}, sort_keys=True))


if __name__ == "__main__":
    main()
