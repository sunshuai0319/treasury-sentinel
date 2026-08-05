import os
import subprocess
import sys
from pathlib import Path


def test_demo_reset_seeds_only_demo_rows(tmp_path: Path):
    root = Path(__file__).resolve().parents[4]
    db_path = tmp_path / "demo.db"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"DATABASE_URL=sqlite+pysqlite:///{db_path}",
                "MILVUS_URI=http://localhost:19530",
                "ARK_API_KEY=test",
                "KEEPERHUB_API_KEY=test",
                "BASE_SEPOLIA_RPC_URL=https://example.invalid",
            ]
        ),
        encoding="utf-8",
    )

    env = {key: value for key, value in os.environ.items() if key not in {"DATABASE_URL"}}
    env["PYTHONPATH"] = str(root / "apps" / "api")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "reset_demo_data.py"), "--env-file", str(env_file), "--seed", "1"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert '"ok": true' in result.stdout
    assert db_path.exists()
