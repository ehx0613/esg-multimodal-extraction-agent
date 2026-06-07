import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from openai import OpenAI

from config.settings import (
    DASHSCOPE_API_KEY,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_PROVIDER,
    RAG_LOCAL_DIM,
)


INDEX_FILE = "chunks.faiss"
METADATA_FILE = "chunks.metadata.json"
MANIFEST_FILE = "manifest.json"


def _normalize_rows(rows: np.ndarray) -> np.ndarray:
    rows = rows.astype("float32", copy=False)
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return rows / norms


def _hash_ngram_vector(text: str, dim: int = RAG_LOCAL_DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype="float32")
    text = str(text or "").lower()
    tokens = re.findall(r"[\u4e00-\u9fff]|[a-z0-9]+|%", text)
    grams: List[str] = []

    for idx, token in enumerate(tokens):
        grams.append(token)
        if idx + 1 < len(tokens):
            grams.append(token + tokens[idx + 1])
        if idx + 2 < len(tokens):
            grams.append(token + tokens[idx + 1] + tokens[idx + 2])

    for gram in grams:
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[bucket] += sign

    norm = np.linalg.norm(vec)
    if norm:
        vec /= norm
    return vec


def _local_embed(texts: List[str]) -> np.ndarray:
    return np.vstack([_hash_ngram_vector(text) for text in texts]).astype("float32")


def _dashscope_embed(texts: List[str]) -> Optional[np.ndarray]:
    if not DASHSCOPE_API_KEY:
        return None

    try:
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        response = client.embeddings.create(
            model=RAG_EMBEDDING_MODEL,
            input=texts,
        )
        vectors = [item.embedding for item in response.data]
        return _normalize_rows(np.array(vectors, dtype="float32"))
    except Exception:
        return None


def embed_texts(texts: List[str]) -> np.ndarray:
    if RAG_EMBEDDING_PROVIDER == "dashscope":
        vectors = _dashscope_embed(texts)
        if vectors is not None:
            return vectors
    return _local_embed(texts)


def build_query_text(field_item: Dict[str, Any], extra_terms: Optional[List[str]] = None) -> str:
    pieces = [
        field_item.get("field_key", "").replace("_", " "),
        field_item.get("name_cn", ""),
        field_item.get("category", ""),
        field_item.get("unit_type", ""),
        *field_item.get("aliases", []),
        *field_item.get("required_any", []),
        *field_item.get("unit_examples", []),
        *(extra_terms or []),
    ]
    return " ".join(str(piece) for piece in pieces if piece)


def _chunks_signature(chunks: List[Dict[str, Any]]) -> str:
    digest = hashlib.blake2b(digest_size=16)
    for chunk in chunks:
        digest.update(str(chunk.get("chunk_id", "")).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(chunk.get("page_number", "")).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(chunk.get("text", "")).encode("utf-8"))
        digest.update(b"\0\0")
    return digest.hexdigest()


class FaissChunkVectorStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / INDEX_FILE
        self.metadata_path = self.index_dir / METADATA_FILE
        self.manifest_path = self.index_dir / MANIFEST_FILE
        self.index = None
        self.metadata: List[Dict[str, Any]] = []

    def build_or_load(self, chunks: List[Dict[str, Any]]) -> "FaissChunkVectorStore":
        if self._can_load(chunks):
            self._load()
            return self

        texts = [str(chunk.get("context_text") or chunk.get("text", "") or "") for chunk in chunks]
        vectors = embed_texts(texts)
        vectors = _normalize_rows(vectors)

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        metadata = [
            {
                "chunk_id": chunk.get("chunk_id"),
                "page_number": chunk.get("page_number"),
                "section_title": chunk.get("section_title", ""),
                "chunk_type": chunk.get("chunk_type", ""),
                "text": chunk.get("text", ""),
                "context_text": chunk.get("context_text", ""),
            }
            for chunk in chunks
        ]

        self.index_path.write_bytes(faiss.serialize_index(index).tobytes())
        self.metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        self.manifest_path.write_text(
            json.dumps(
                {
                    "chunk_count": len(chunks),
                    "chunks_signature": _chunks_signature(chunks),
                    "embedding_provider": RAG_EMBEDDING_PROVIDER,
                    "embedding_model": RAG_EMBEDDING_MODEL if RAG_EMBEDDING_PROVIDER == "dashscope" else "local_hash_ngram",
                    "dimension": int(vectors.shape[1]),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.index = index
        self.metadata = metadata
        return self

    def search(self, query_text: str, top_k: int = 8) -> List[Dict[str, Any]]:
        if self.index is None:
            self._load()
        if self.index is None or not self.metadata:
            return []

        query_vec = _normalize_rows(embed_texts([query_text]))
        scores, indexes = self.index.search(query_vec, max(top_k, 1))

        results = []
        for score, idx in zip(scores[0], indexes[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            results.append(
                {
                    **self.metadata[idx],
                    "vector_score": round(float(score), 6),
                }
            )
        return results

    def _can_load(self, chunks: List[Dict[str, Any]]) -> bool:
        if not (self.index_path.exists() and self.metadata_path.exists() and self.manifest_path.exists()):
            return False

        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        return (
            int(manifest.get("chunk_count", -1)) == len(chunks)
            and manifest.get("chunks_signature") == _chunks_signature(chunks)
        )

    def _load(self) -> None:
        try:
            raw = np.frombuffer(self.index_path.read_bytes(), dtype="uint8")
            self.index = faiss.deserialize_index(raw)
            self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except Exception:
            self.index = None
            self.metadata = []
