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


def test_demo_runner_can_execute_local_workflow(tmp_path: Path):
    root = Path(__file__).resolve().parents[4]
    db_path = tmp_path / "demo.db"
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"DATABASE_URL=sqlite+pysqlite:///{db_path}\n"
        "MILVUS_URI=http://localhost:19530\n"
        "ARK_API_KEY=test\n"
        "KEEPERHUB_API_KEY=test\n"
        "BASE_SEPOLIA_RPC_URL=https://example.invalid\n",
        encoding="utf-8",
    )
    env = {"PYTHONPATH": str(root / "apps" / "api")}
    subprocess.run(
        [sys.executable, str(root / "scripts" / "reset_demo_data.py"), "--env-file", str(env_file), "--seed", "42"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "run_demo_scenarios.py"),
            "--workflow",
            "--seed",
            "42",
            "--env-file",
            str(env_file),
        ],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert '"workflow_scenarios": 3' in result.stdout
