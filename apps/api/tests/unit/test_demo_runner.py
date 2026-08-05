import subprocess
import sys
from pathlib import Path


def test_demo_runner_writes_evidence_document():
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "run_demo_scenarios.py")],
        cwd=root,
        env={"PYTHONPATH": str(root / "apps" / "api")},
        text=True,
        capture_output=True,
        check=True,
    )

    assert '"ok": true' in result.stdout
    output = root / "docs" / "demo-script.md"
    assert "`normal` → `APPROVE`" in output.read_text()
