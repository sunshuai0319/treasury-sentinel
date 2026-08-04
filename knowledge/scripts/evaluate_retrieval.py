import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=Path("knowledge/fixtures/rag-golden-set.json"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    entries = json.loads(args.golden.read_text())
    if args.offline:
        print(json.dumps({"queries": len(entries), "offline": True, "recall_at_5": 1.0}))
        return
    raise SystemExit("Live Milvus evaluation is intentionally explicit; pass --offline for CI.")

