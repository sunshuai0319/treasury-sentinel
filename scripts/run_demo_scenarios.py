import json
from pathlib import Path

from app.agent.demo import run_demo_scenario
from app.config import Settings
from app.db import session_factory
from app.services.payment_workflow import PaymentWorkflowRepository

SCENARIOS = ["normal", "duplicate", "address_mismatch", "over_limit", "pause"]
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo-script.md"
DEPLOYMENT = ROOT / "contracts" / "deployments" / "base-sepolia.json"
EXPECTED_ACTIONS = {
    "normal": "APPROVE",
    "duplicate": "REJECT",
    "address_mismatch": "REJECT",
    "over_limit": "REVIEW",
    "pause": "PAUSE",
}
WORKFLOW_INVOICES = {
    "normal": ("inv_demo_001", 420_000_000, "0x1111111111111111111111111111111111111111"),
    "address_mismatch": ("inv_demo_mismatch", 420_000_000, "0x2222222222222222222222222222222222222222"),
    "over_limit": ("inv_demo_over_limit", 700_000_000, "0x1111111111111111111111111111111111111111"),
}


def run_workflow_scenarios(seed: int, env_file: Path) -> list[dict[str, str]]:
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    repo = PaymentWorkflowRepository(session_factory(settings))
    results = []
    for scenario, (invoice_id, amount, recipient) in WORKFLOW_INVOICES.items():
        record = repo.create(
            idempotency_key=f"demo-{seed}:{scenario}",
            vendor_id="vendor_demo",
            invoice_id=invoice_id,
            amount_units=amount,
            recipient_address=recipient,
        )
        run = repo.analyze(record.request_id)
        if run is None:
            raise RuntimeError(f"workflow scenario {scenario} did not produce a run")
        results.append({"scenario": scenario, "request_id": run.request_id, "final_action": run.final_action})
    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", action="store_true")
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--env-file", type=Path, default=ROOT / "apps/api/.env")
    args = parser.parse_args()

    deployment = json.loads(DEPLOYMENT.read_text()) if DEPLOYMENT.exists() else {}
    runs = [run_demo_scenario(name) for name in SCENARIOS]
    for run in runs:
        expected = EXPECTED_ACTIONS[run.scenario]
        if run.final_action != expected:
            raise SystemExit(f"{run.scenario} expected {expected}, got {run.final_action}")
    workflow_runs = run_workflow_scenarios(args.seed, args.env_file) if args.workflow else []
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
    if workflow_runs:
        lines.extend(["", "## Local API workflow assertions", ""])
        for item in workflow_runs:
            lines.append(f"- `{item['scenario']}` request `{item['request_id']}` → `{item['final_action']}`")
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
    print(
        json.dumps(
            {"scenarios": len(runs), "workflow_scenarios": len(workflow_runs), "output": str(OUTPUT), "ok": True},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
