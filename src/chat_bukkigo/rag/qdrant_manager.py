from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger("chat_bukkigo.rag.qdrant")


class QdrantManager:
    """Quản lý kết nối và lưu trữ vector trong Qdrant."""

    DEFAULT_COLLECTION = "nail_receptionist_knowledge"
    DEFAULT_VECTOR_SIZE = 1024

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: Optional[int] = None,
        local_path: Optional[Union[Path, str]] = None,
    ) -> None:
        self.collection_name = collection_name
        self.server_url = server_url or os.getenv("QDRANT_URL", "http://192.168.0.121:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY", "12345678")
        self.vector_size = vector_size or int(os.getenv("EMBEDDING_DIMENSION", str(self.DEFAULT_VECTOR_SIZE)))
        self.local_path = Path(local_path or (Path(__file__).resolve().parent.parent.parent.parent / "data" / "qdrant_db"))
        self.client = self._init_client()
        self._ensure_collection()

    def _init_client(self) -> QdrantClient:
        """Khởi tạo Qdrant Client: ưu tiên Server nếu có, fallback sang Local Disk/Memory."""
        if self.server_url:
            try:
                client = QdrantClient(
                    url=self.server_url,
                    api_key=self.api_key if self.api_key else None,
                    timeout=3.0,
                    check_compatibility=False,
                )
                client.get_collections()
                logger.info("Verbindung zu Qdrant Server erfolgreich: %s", self.server_url)
                return client
            except Exception as e:
                logger.warning("Qdrant Server (%s) nicht erreichbar (%s), verwende lokalen Speicher: %s", self.server_url, e, self.local_path)

        self.local_path.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(self.local_path), check_compatibility=False)

    def _ensure_collection(self) -> None:
        """Tạo collection nếu chưa tồn tại hoặc recreate nếu dimension cũ không khớp."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if exists:
            try:
                coll_info = self.client.get_collection(self.collection_name)
                vectors_cfg = coll_info.config.params.vectors
                current_size = None
                if hasattr(vectors_cfg, "size"):
                    current_size = vectors_cfg.size
                elif isinstance(vectors_cfg, dict) and "size" in vectors_cfg:
                    current_size = vectors_cfg["size"]

                if current_size is not None and current_size != self.vector_size:
                    logger.warning(
                        "Collection '%s' có vector size cũ (%d) khác cấu hình model mới (%d). Recreate collection...",
                        self.collection_name,
                        current_size,
                        self.vector_size,
                    )
                    self.client.delete_collection(self.collection_name)
                    exists = False
            except Exception as e:
                logger.warning("Không thể kiểm tra vector size của collection '%s': %s", self.collection_name, e)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Collection '%s' wurde neu angelegt auf %s mit Vector-Size %d.", self.collection_name, self.server_url, self.vector_size)

    def upsert_records(self, ids: List[Union[str, int]], vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        """Lưu hoặc cập nhật danh sách vector và payload vào Qdrant."""
        points = [
            models.PointStruct(
                id=idx,
                vector=vec,
                payload=payload,
            )
            for idx, vec, payload in zip(ids, vectors, payloads)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("%d Vektoren erfolgreich in Qdrant gespeichert.", len(points))

    def search(
        self,
        query_vector: List[float],
        limit: int = 3,
        category: Optional[str] = None,
        service: Optional[str] = None,
    ) -> List[models.ScoredPoint]:
        """Tìm kiếm vector tương đồng kết hợp Payload Filtering."""
        conditions: List[models.FieldCondition] = []
        if category:
            conditions.append(
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category),
                )
            )
        if service:
            conditions.append(
                models.FieldCondition(
                    key="service",
                    match=models.MatchValue(value=service),
                )
            )

        query_filter = models.Filter(must=conditions) if conditions else None

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
        return results.points
