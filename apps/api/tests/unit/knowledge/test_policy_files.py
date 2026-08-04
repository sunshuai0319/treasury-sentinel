import json
from pathlib import Path


def test_policy_manifest_files_and_sections_exist():
    root = Path(__file__).parents[5]
    manifest = json.loads((root / "knowledge/fixtures/policy-manifest.json").read_text())

    assert len(manifest["documents"]) == 6
    assert manifest["embedding_dimension"] == 512
    for item in manifest["documents"]:
        text = (root / item["path"]).read_text()
        assert f"# {item['title']}" in text
        assert item["content_hash"] is None
        for section in item["required_sections"]:
            assert f"## {section}" in text

