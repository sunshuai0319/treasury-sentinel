from fastapi import APIRouter

from app.agent.demo import run_demo_scenario
from app.agent.state import PaymentRun

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/demo/scenarios")
def scenarios() -> list[dict[str, str]]:
    return [
        {"id": "normal", "name": "Normal auto payment"},
        {"id": "duplicate", "name": "Duplicate invoice rejected"},
        {"id": "address_mismatch", "name": "Wallet mismatch rejected"},
        {"id": "over_limit", "name": "Finance review required"},
        {"id": "pause", "name": "Emergency pause recommended"},
    ]


@router.post("/demo/run/{scenario}", response_model=PaymentRun)
def run_scenario(scenario: str) -> PaymentRun:
    return run_demo_scenario(scenario)

