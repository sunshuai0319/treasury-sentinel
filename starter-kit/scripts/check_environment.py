from __future__ import annotations

import importlib.util
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import Settings


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
    width = max(len(c.name) for c in checks)
    failed = 0
    for check in checks:
        status = "OK" if check.ok else "BLOCKED"
        print(f"{check.name:<{width}}  {status:<7}  {check.detail}")
        failed += 0 if check.ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
