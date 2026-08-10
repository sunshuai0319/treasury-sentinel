from __future__ import annotations

import importlib.util
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import Settings

TREASURY_GUARD_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "role", "type": "bytes32"}, {"internalType": "address", "name": "account", "type": "address"}],
        "name": "hasRole",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    }
]
ERC20_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def port_open(uri: str) -> bool:
    host_port = uri.split("://", 1)[-1].split("/", 1)[0]
    host, _, port = host_port.partition(":")
    if not host or not port:
        return False
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            return True
    except OSError:
        return False


def chain_checks(settings: Settings) -> list[Check]:
    if importlib.util.find_spec("web3") is None:
        return [
            Check("keeperhub_executor_role", False, "web3 package missing"),
            Check("keeperhub_guardian_role", False, "web3 package missing"),
            Check("treasury_guard_usdc_balance", False, "web3 package missing"),
        ]
    if not (
        settings.base_sepolia_rpc_url
        and settings.treasury_guard_address
        and settings.demo_usdc_address
        and settings.keeperhub_wallet_address
    ):
        return [
            Check("keeperhub_executor_role", False, "missing rpc/contract/wallet config"),
            Check("keeperhub_guardian_role", False, "missing rpc/contract/wallet config"),
            Check("treasury_guard_usdc_balance", False, "missing rpc/contract config"),
        ]
    from web3 import Web3

    try:
        web3 = Web3(Web3.HTTPProvider(settings.base_sepolia_rpc_url, request_kwargs={"timeout": 8}))
        guard_address = Web3.to_checksum_address(settings.treasury_guard_address)
        usdc_address = Web3.to_checksum_address(settings.demo_usdc_address)
        wallet_address = Web3.to_checksum_address(settings.keeperhub_wallet_address)
        guard = web3.eth.contract(address=guard_address, abi=TREASURY_GUARD_ABI)
        usdc = web3.eth.contract(address=usdc_address, abi=ERC20_ABI)
        executor_role = Web3.keccak(text="EXECUTOR_ROLE")
        guardian_role = Web3.keccak(text="GUARDIAN_ROLE")
        has_executor = bool(guard.functions.hasRole(executor_role, wallet_address).call())
        has_guardian = bool(guard.functions.hasRole(guardian_role, wallet_address).call())
        balance = int(usdc.functions.balanceOf(guard_address).call())
    except Exception as exc:  # noqa: BLE001 - onboarding check should explain blockers, not crash
        detail = f"chain read failed: {type(exc).__name__}"
        return [
            Check("keeperhub_executor_role", False, detail),
            Check("keeperhub_guardian_role", False, detail),
            Check("treasury_guard_usdc_balance", False, detail),
        ]
    return [
        Check(
            "keeperhub_executor_role",
            has_executor,
            "wallet has EXECUTOR_ROLE" if has_executor else "missing EXECUTOR_ROLE",
        ),
        Check(
            "keeperhub_guardian_role",
            has_guardian,
            "wallet has GUARDIAN_ROLE" if has_guardian else "missing GUARDIAN_ROLE",
        ),
        Check("treasury_guard_usdc_balance", balance > 0, f"{balance / 1_000_000:.6f} USDC"),
    ]


def main() -> int:
    settings = Settings(_env_file=REPO_ROOT / "apps/api/.env")  # type: ignore[call-arg]
    checks = [
        Check("python", sys.version_info >= (3, 12), sys.version.split()[0]),
        Check("web3", importlib.util.find_spec("web3") is not None, "package importable"),
        Check("embedding_model", Path(settings.embedding_model_path).exists(), settings.embedding_model_path),
        Check("postgres", settings.database_url.startswith("postgresql+psycopg://"), "configured"),
        Check("milvus", port_open(settings.milvus_uri), settings.milvus_uri),
        Check("rpc", settings.base_sepolia_rpc_url.startswith("http"), settings.base_sepolia_rpc_url),
        Check("treasury_guard", bool(settings.treasury_guard_address), settings.treasury_guard_address or "missing"),
        Check("demo_usdc", bool(settings.demo_usdc_address), settings.demo_usdc_address or "missing"),
        Check(
            "keeperhub",
            bool(settings.keeperhub_api_key and settings.keeperhub_wallet_address),
            "api_key/set and wallet/set" if settings.keeperhub_api_key and settings.keeperhub_wallet_address else "missing api key or wallet",
        ),
    ]
    checks.extend(chain_checks(settings))
    width = max(len(c.name) for c in checks)
    failed = 0
    for check in checks:
        status = "OK" if check.ok else "BLOCKED"
        print(f"{check.name:<{width}}  {status:<7}  {check.detail}")
        failed += 0 if check.ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
