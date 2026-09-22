from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import List, Optional, Sequence

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

logger = logging.getLogger("chat_bukkigo.rag.embedding")


class EmbeddingEngine:
    """Hệ thống sinh Vector Embedding cho BAAI/bge-m3 hoặc OpenAI-compatible Service.
    
    Hệ thống KHÔNG sử dụng fallback cục bộ (Local Semantic Hashing). 
    Nếu không thể kết nối tới service, sẽ báo lỗi trực tiếp.
    """

    DEFAULT_VECTOR_SIZE = 1024

    def __init__(
        self,
        service_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: Optional[int] = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        self.vector_size = vector_size or int(os.getenv("EMBEDDING_DIMENSION", str(self.DEFAULT_VECTOR_SIZE)))
        self.timeout = timeout
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

        # Xác định URL của service
        default_url = os.getenv("EMBEDDING_SERVICE_URL")
        if not default_url and os.getenv("OPENAI_USE_CUSTOM_ENDPOINT") == "true":
            default_url = os.getenv("OPENAI_CUSTOM_BASE_URL")
        
        self.service_url = (service_url or default_url or "http://localhost:8008/v1").rstrip("/")

        self.client: Optional[OpenAI] = None
        if OpenAI is not None:
            try:
                client_api_key = self.api_key if self.api_key else "EMPTY"
                self.client = OpenAI(
                    api_key=client_api_key,
                    base_url=self.service_url,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning("Không thể khởi tạo OpenAI client (%s), sẽ dùng HTTP client trực tiếp.", e)
                self.client = None

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        """Sinh embedding vector cho danh sách văn bản. Bắt buộc kết nối thành công, không dùng fallback."""
        if not texts:
            return []

        clean_texts = [str(t) for t in texts]

        # 1. Thử qua OpenAI client nếu có
        if self.client is not None:
            try:
                resp = self.client.embeddings.create(model=self.model, input=clean_texts)
                vectors = [item.embedding for item in resp.data]
                self._validate_vectors(vectors, len(clean_texts))
                return vectors
            except Exception as exc:
                logger.warning("Lỗi khi gọi qua OpenAI client: %s. Thử gọi trực tiếp HTTP...", exc)

        # 2. Gọi trực tiếp HTTP REST API (urllib, không phụ thuộc thư viện ngoài)
        return self._http_embed_request(clean_texts)

    def embed_query(self, query: str) -> List[float]:
        """Sinh embedding vector cho một câu truy vấn. Báo lỗi nếu query rỗng."""
        if not query or not query.strip():
            raise ValueError("Query embedding không được để trống.")
        vectors = self.embed_texts([query])
        return vectors[0]

    def _http_embed_request(self, texts: List[str]) -> List[List[float]]:
        """Gọi HTTP POST trực tiếp tới endpoint /embeddings."""
        endpoint = f"{self.service_url}/embeddings" if not self.service_url.endswith("/embeddings") else self.service_url
        payload = json.dumps({"input": texts, "model": self.model}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"Embedding service trả mã HTTP {response.status}")
                body = json.loads(response.read().decode("utf-8"))

            if "data" in body:
                vectors = [item["embedding"] for item in body["data"]]
            elif "embeddings" in body:
                vectors = body["embeddings"]
            else:
                raise RuntimeError(f"Dữ liệu trả về từ service không đúng định dạng: {list(body.keys())}")

            self._validate_vectors(vectors, len(texts))
            return vectors
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Không thể kết nối đến Embedding Service tại '{endpoint}'. "
                f"Vui lòng đảm bảo Docker container 'chat_bukkigo_bge_m3' đang chạy. Chi tiết: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Lỗi sinh embedding: {e}") from e

    def _validate_vectors(self, vectors: List[List[float]], expected_count: int) -> None:
        """Kiểm tra số lượng và kích thước vector."""
        if len(vectors) != expected_count:
            raise ValueError(f"Số vector nhận được ({len(vectors)}) không khớp với số text ({expected_count}).")
        if vectors and len(vectors[0]) != self.vector_size:
            logger.warning(
                "Kích thước vector thực tế (%d) khác với vector_size cấu hình (%d). Cập nhật vector_size.",
                len(vectors[0]),
                self.vector_size,
            )
            self.vector_size = len(vectors[0])
