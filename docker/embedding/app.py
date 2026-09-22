from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import torch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bge_m3_service")

# Tự động trỏ HF_HOME vào thư mục models_cache nếu chưa cấu hình
if "HF_HOME" not in os.environ:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cache_candidate = os.path.join(project_root, "models_cache")
    if os.path.exists(cache_candidate):
        os.environ["HF_HOME"] = cache_candidate

MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-m3")


def get_optimal_device() -> str:
    """Tự động phát hiện phần cứng tối ưu: Metal GPU (MPS) trên Mac, CUDA trên Nvidia, hoặc CPU."""
    explicit_device = os.getenv("DEVICE")
    if explicit_device:
        return explicit_device
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


DEVICE = get_optimal_device()

# Nếu chạy trên CPU, giới hạn số luồng để không gây nghẽn CPU host
if DEVICE == "cpu":
    max_threads = int(os.getenv("TORCH_NUM_THREADS", "2"))
    torch.set_num_threads(max_threads)
    logger.info("Chạy trên CPU với giới hạn %d luồng tính toán.", max_threads)
else:
    logger.info("Tăng tốc phần cứng kích hoạt thành công: device='%s'", DEVICE)

model: Optional[SentenceTransformer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info("Bắt đầu nạp model '%s' lên Device '%s'...", MODEL_NAME, DEVICE)
    start_time = time.time()
    try:
        model = SentenceTransformer(MODEL_NAME, device=DEVICE)
        elapsed = time.time() - start_time
        logger.info("Model '%s' sẵn sàng trên device '%s' (Mất %.2f giây).", MODEL_NAME, DEVICE, elapsed)
    except Exception as exc:
        logger.exception("Lỗi khi nạp model '%s': %s", MODEL_NAME, exc)
        raise exc
    yield
    logger.info("Dừng BGE-M3 Embedding Service.")


app = FastAPI(
    title="BAAI/bge-m3 Embedding Service",
    description="Dedicated OpenAI-compatible Embedding Service for BAAI/bge-m3 with Metal GPU (MPS) support",
    version="1.0.0",
    lifespan=lifespan,
)


class OpenAIEmbeddingRequest(BaseModel):
    input: Union[str, List[str]] = Field(..., description="Văn bản hoặc danh sách văn bản cần embed")
    model: Optional[str] = Field(default=MODEL_NAME, description="Tên model")
    encoding_format: Optional[str] = Field(default="float", description="Định dạng vector")


class DirectEmbedRequest(BaseModel):
    texts: List[str] = Field(..., description="Danh sách văn bản cần embed")


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint kiểm tra trạng thái model và phần cứng đang sử dụng."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model is still loading or unavailable")
    dimension = model.get_sentence_embedding_dimension()
    device_name = str(model.device)
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "dimension": dimension,
        "device": device_name,
        "is_gpu_accelerated": "mps" in device_name or "cuda" in device_name,
    }


@app.post("/v1/embeddings")
def openai_embeddings(request: OpenAIEmbeddingRequest) -> Dict[str, Any]:
    """API tương thích chuẩn OpenAI `/v1/embeddings`."""
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not ready.",
        )

    texts = [request.input] if isinstance(request.input, str) else request.input
    if not texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input cannot be empty.",
        )

    try:
        # BGE-M3 dense embeddings với chuẩn hóa Cosine (normalize_embeddings=True)
        embeddings = model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        data = []
        for idx, emb in enumerate(embeddings):
            data.append(
                {
                    "object": "embedding",
                    "embedding": emb.tolist() if hasattr(emb, "tolist") else list(emb),
                    "index": idx,
                }
            )

        estimated_tokens = sum(max(1, len(t.split())) for t in texts)
        return {
            "object": "list",
            "data": data,
            "model": MODEL_NAME,
            "usage": {
                "prompt_tokens": estimated_tokens,
                "total_tokens": estimated_tokens,
            },
        }
    except Exception as e:
        logger.exception("Error during embedding calculation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding error: {e}",
        )


@app.post("/embed")
def direct_embed(request: DirectEmbedRequest) -> Dict[str, Any]:
    """Endpoint trực tiếp nhận texts và trả về danh sách vectors."""
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not ready.",
        )

    if not request.texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Texts list cannot be empty.",
        )

    try:
        embeddings = model.encode(
            request.texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return {
            "embeddings": embeddings.tolist() if hasattr(embeddings, "tolist") else [list(x) for x in embeddings],
            "dimension": model.get_sentence_embedding_dimension(),
            "count": len(request.texts),
        }
    except Exception as e:
        logger.exception("Direct embed error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Direct embed error: {e}",
        )
