from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Đảm bảo đường dẫn import từ src
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from chat_bukkigo.rag.embedding import EmbeddingEngine
from chat_bukkigo.rag.ingest import ingest_knowledge_base
from chat_bukkigo.rag.qdrant_manager import QdrantManager
from chat_bukkigo.rag.retriever import KnowledgeRetriever


def run_tests(force_ingest: bool = False) -> None:
    print("=" * 70)
    print("=== TEST TÌM KIẾM TRUY XUẤT QDRANT (NAIL REZEPTIONISTIN) ===")
    print("=" * 70)

    qdrant_mgr = QdrantManager()
    embed_engine = EmbeddingEngine()

    # Chỉ nạp data nếu có yêu cầu tường minh qua cờ --ingest
    if force_ingest:
        print("\n[TÙY CHỌN] Đang nạp lại toàn bộ Knowledge Base vào Qdrant...")
        total_ingested = ingest_knowledge_base(qdrant=qdrant_mgr, embedding=embed_engine)
        print(f"-> Đã nạp thành công: {total_ingested} Chunks.")
    else:
        print("\n-> Sử dụng dữ liệu hiện có trong Qdrant (bỏ qua bước Ingest).")

    retriever = KnowledgeRetriever(qdrant_manager=qdrant_mgr, embedding_engine=embed_engine)

    # Danh sách câu hỏi kiểm thử (Test Queries)
    test_cases = [
        {
            "title": "Tình huống 1 (Case 1): So sánh Shellac vs Gel",
            "query_de": "Was ist besser, Shellac oder Gel?",
            "query_vi": "Nên làm Shellac hay Gel, cái nào tốt hơn?",
            "expected_category": "service_comparison",
        },
        {
            "title": "Tình huống 2 (Case 2): Móng mỏng / Yếu",
            "query_de": "Meine Nägel sind sehr dünn und brechen schnell, geht Shellac?",
            "query_vi": "Móng tôi rất mỏng và yếu thì có làm Shellac được không?",
            "expected_category": "service_detail",
        },
        {
            "title": "Tình huống 3 (Case 3): Khiếu nại / Chipping & Lifting",
            "query_de": "Mein Shellac löst sich nach zwei Tagen ab!",
            "query_vi": "Móng mới làm hôm qua mà bị bong hết rồi!",
            "expected_category": "complaint_warranty",
        },
        {
            "title": "Tình huống 4 (Case 4): An toàn y tế (Greenie / Nhiễm trùng)",
            "query_de": "Mein Nagel ist grün unter dem Lack und tut weh!",
            "query_vi": "Móng bị xanh lục dưới lớp sơn và bị đau",
            "expected_category": "safety_escalation",
        },
        {
            "title": "Tình huống 5 (Case 5): Đặt hẹn với thợ chỉ định",
            "query_de": "Ich möchte einen Termin bei Karin in Oerlikon buchen",
            "query_vi": "Tôi muốn đặt lịch làm móng với thợ Karin ở Oerlikon",
            "expected_category": "booking_policy",
        },
    ]

    print("\nBắt đầu chạy truy vấn kiểm thử...")
    for tc in test_cases:
        print(f"\n------------------------------------------------------------")
        print(f"[{tc['title']}]")
        print(f"Câu hỏi (DE): \"{tc['query_de']}\"")
        results = retriever.retrieve(tc["query_de"], limit=1)
        if not results:
            print("  [LỖI] Không tìm thấy kết quả phù hợp!")
            continue

        best = results[0]
        print(f"  -> Top-1 Match: [{best.chunk_id}] (Score: {best.score:.4f})")
        print(f"  -> Category: {best.category} | Service: {best.service} | Topic: {best.topic}")
        print(f"  -> Facts: {best.facts[:110]}...")
        print(f"  -> Boundary Rule: {best.boundary_rules[:110]}...")
        print(f"  -> Trả lời mẫu (DE-CH): {best.sample_dialogue.get('de_CH', '')}")
        print(f"  -> Trả lời mẫu (VI-VN): {best.sample_dialogue.get('vi_VN', '')}")

    print("\n" + "=" * 70)
    print("=== HOÀN THÀNH KIỂM THỬ TRUY XUẤT ===")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiểm thử tìm kiếm trên Qdrant")
    parser.add_argument("--ingest", action="store_true", help="Nạp lại dữ liệu trước khi test (mặc định: False)")
    args = parser.parse_args()
    run_tests(force_ingest=args.ingest)
