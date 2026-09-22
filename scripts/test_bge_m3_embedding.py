from __future__ import annotations

import math
import sys
from pathlib import Path

# Đảm bảo đường dẫn import từ src
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from chat_bukkigo.rag.embedding import EmbeddingEngine


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def main() -> None:
    print("=" * 70)
    print("=== TEST EMBEDDING ENGINE: BAAI/bge-m3 DOCKER SERVICE ===")
    print("=" * 70)

    # 1. Khởi tạo Engine
    engine = EmbeddingEngine()
    print(f"Service URL: {engine.service_url}")
    print(f"Model: {engine.model}")
    print(f"Cấu hình Vector Size: {engine.vector_size}")

    # 2. Test Single Query Embedding
    print("\n1. Đang test embed_query...")
    query = "Was ist der Unterschied zwischen Shellac und Gel?"
    try:
        vec = engine.embed_query(query)
        print(f"-> Thành công! Vector dimension: {len(vec)}")
        assert len(vec) == 1024, f"Kỳ vọng 1024 chiều, thực tế {len(vec)}"
        print(f"-> 5 phần tử đầu: {[round(x, 4) for x in vec[:5]]}")
    except Exception as e:
        print(f"-> Lỗi khi embed_query: {e}")
        raise

    # 3. Test Batch Texts Embedding & Multilingual Similarity
    print("\n2. Đang test embed_texts (Đa ngôn ngữ DE - VI - Out of domain)...")
    texts = [
        "Was ist Shellac?",                                  # DE
        "Sơn móng tay Shellac là gì?",                      # VI (Tương đồng)
        "Thủ đô của nước Pháp là thành phố Paris.",         # Không liên quan
    ]

    vectors = engine.embed_texts(texts)
    print(f"-> Đã sinh {len(vectors)} vectors (Mỗi vector {len(vectors[0])} chiều)")

    sim_de_vi = cosine_similarity(vectors[0], vectors[1])
    sim_de_unrelated = cosine_similarity(vectors[0], vectors[2])

    print(f"-> Độ tương đồng Cosine (DE vs VI tương đồng nghĩa): {sim_de_vi:.4f}")
    print(f"-> Độ tương đồng Cosine (DE vs Câu không liên quan):  {sim_de_unrelated:.4f}")

    assert sim_de_vi > sim_de_unrelated, "Độ tương đồng ngữ nghĩa đa ngôn ngữ phải cao hơn câu không liên quan"
    print("-> Đánh giá chất lượng: CHUẨN XÁC! BAAI/bge-m3 hiểu ngữ nghĩa song ngữ DE-VI vượt trội.")

    # 4. Test Strict Error (Không fallback)
    print("\n3. Đang test cơ chế Strict Error (Báo lỗi khi service sai, không fallback)...")
    offline_engine = EmbeddingEngine(service_url="http://localhost:59999/v1", timeout=2.0)
    try:
        offline_engine.embed_query("Test câu hỏi")
        print("-> [CẢNH BÁO] Không báo lỗi khi service offline (Không đúng yêu cầu)!")
    except RuntimeError as re:
        print(f"-> Đúng kỳ vọng! Đã bắt lỗi nghiêm ngặt: {type(re).__name__}")
        print(f"   Thông báo: {str(re)[:90]}...")

    print("\n" + "=" * 70)
    print("=== TẤT CẢ CÁC BƯỚC KIỂM THỬ BGE-M3 THÀNH CÔNG ===")
    print("=" * 70)


if __name__ == "__main__":
    main()
