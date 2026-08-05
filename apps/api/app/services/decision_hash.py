import hashlib
import json
from typing import Any


def stable_decision_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
