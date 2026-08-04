import hashlib
import json
import re
from pathlib import Path

from app.integrations.milvus.repository import PolicyChunk

SECTION_RE = re.compile(r"^## (?P<section>.+)$", re.MULTILINE)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(root: Path) -> dict:
    return json.loads((root / "knowledge/fixtures/policy-manifest.json").read_text())


def split_policy_document(text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group("section"), text[start:end].strip()))
    return sections


def build_policy_chunks(root: Path, embedder) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    manifest = load_manifest(root)
    for item in manifest["documents"]:
        text = (root / item["path"]).read_text()
        doc_hash = content_hash(text)
        sections = split_policy_document(text)
        embeddings = embedder.embed_documents([body for _, body in sections])
        for (section_id, body), embedding in zip(sections, embeddings, strict=True):
            chunks.append(
                PolicyChunk(
                    chunk_id=f"{item['document_id']}:v{item['version']}:{section_id}",
                    document_id=item["document_id"],
                    policy_version=item["version"],
                    section_id=section_id,
                    title=item["title"],
                    content=body,
                    document_type=item["document_type"],
                    payment_category="GENERAL",
                    approval_level="UNKNOWN",
                    effective_from=20260804,
                    effective_to=0,
                    content_hash=doc_hash,
                    embedding=embedding,
                )
            )
    return chunks

