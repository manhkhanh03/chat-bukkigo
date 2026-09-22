from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

from .embedding import EmbeddingEngine
from .qdrant_manager import QdrantManager
from .schema import KnowledgeChunk

logger = logging.getLogger("chat_bukkigo.rag.ingest")


def ingest_knowledge_base(
    json_path: Optional[Union[Path, str]] = None,
    qdrant: Optional[QdrantManager] = None,
    embedding: Optional[EmbeddingEngine] = None,
) -> int:
    """Nạp toàn bộ Knowledge Chunks từ file JSON vào Qdrant Vector DB."""
    path = Path(json_path or (Path(__file__).resolve().parent.parent.parent.parent / "data" / "nail_receptionist_kb.json"))
    if not path.exists():
        raise FileNotFoundError(f"Knowledge-Base-Datei nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks_data = data.get("chunks", [])
    chunks = [KnowledgeChunk(**item) for item in chunks_data]

    qdrant_mgr = qdrant or QdrantManager()
    embed_engine = embedding or EmbeddingEngine()

    texts_to_embed = [chunk.to_embedding_text() for chunk in chunks]
    vectors = embed_engine.embed_texts(texts_to_embed)

    point_ids = list(range(1, len(chunks) + 1))
    payloads = [chunk.model_dump() for chunk in chunks]

    qdrant_mgr.upsert_records(ids=point_ids, vectors=vectors, payloads=payloads)
    print(f"Erfolgreich {len(chunks)} Chunks in Qdrant eingebunden.")
    return len(chunks)


if __name__ == "__main__":
    ingest_knowledge_base()
