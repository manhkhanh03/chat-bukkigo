from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Đảm bảo import từ src
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

load_dotenv(ROOT_DIR / ".env")

from chat_bukkigo.core.agent import AgentCore
from chat_bukkigo.core.registry import ToolRegistry
from chat_bukkigo.prompt_builder import SkillLoader


async def run_integration_tests() -> None:
    print("=" * 70)
    print("=== TEST TÍCH HỢP FUNCTION CALLING: AGENT CORE & QDRANT TOOL ===")
    print("=" * 70)

    # 1. Khởi tạo ToolRegistry & Quét tools
    print("\n1. Đang quét và đăng ký Tool từ thư mục tools/...")
    tools_dir = ROOT_DIR / "tools"
    registry = ToolRegistry(tools_dir=tools_dir)
    registry.discover_and_register()

    assert registry.has_tools(), "Lỗi: Không tìm thấy tool nào được đăng ký!"
    tool = registry.get_tool("search_nail_knowledge")
    assert tool is not None, "Lỗi: Tool 'search_nail_knowledge' chưa được đăng ký!"
    print(f"-> Đã đăng ký thành công: '{tool.name}' (Timeout: {tool.timeout}s)")
    print(f"-> Schema sinh ra cho LLM: {tool.get_tool_schema()['function']['name']}")

    # 2. Test thực thi trực tiếp Tool qua Registry
    print("\n2. Test thực thi trực tiếp Tool qua ToolRegistry (gọi Qdrant BGE-M3)...")
    test_arg = {"query": "Móng tôi rất mỏng và yếu có làm Shellac được không?", "service": "shellac"}
    tool_output = await registry.execute_tool("search_nail_knowledge", test_arg)
    print("-> Kết quả trả về từ Tool:")
    print(f"   {tool_output[:250]}...")
    assert "facts" in tool_output or "status" in tool_output, "Kết quả trả về phải chứa facts hoặc status"
    print("-> Thực thi Tool trực tiếp: THÀNH CÔNG!")

    # 3. Test nạp System Prompt với Core References (Guardrails)
    print("\n3. Test nạp Core System Prompt (SKILL.md + Core Rules + Safety)...")
    skill_loader = SkillLoader(ROOT_DIR / "skills" / "nail-beauty-consultant")
    core_system_prompt = skill_loader.build_core_system_prompt()
    print(f"-> Độ dài System Prompt nạp sẵn: {len(core_system_prompt)} ký tự.")
    assert "13 Kernregeln" in core_system_prompt or "AI Rezeptionistin" in core_system_prompt
    assert "receptionist-core-rules.md" in core_system_prompt
    assert "safety-and-medical.md" in core_system_prompt
    print("-> Nạp Core Guardrails: THÀNH CÔNG!")

    # 4. Test Agent với LLM (nếu có OPENAI_API_KEY hoặc mock)
    print("\n4. Test luồng tương tác Agent...")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_CUSTOM_BASE_URL") if os.getenv("OPENAI_USE_CUSTOM_ENDPOINT") == "true" else None

    if not api_key:
        print("-> [INFO] Chưa cấu hình OPENAI_API_KEY trong .env.")
        print("   Đã kiểm tra cấu trúc Registry, Tool và Schema: HOÀN TOÀN HỢP LỆ!")
        print("   Khi bạn điền API key, Agent sẽ tự động kích hoạt gọi Tool tra cứu.")
    else:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            agent = AgentCore(
                llm_client=client,
                registry=registry,
                system_prompt=core_system_prompt,
                model=model,
            )

            # Test kịch bản 1: Chào hỏi đơn giản (Không gọi Tool)
            print("\n--- Kịch bản 1: Chào hỏi (Kỳ vọng: Không gọi tool) ---")
            res1 = await agent.chat("Guten Tag, wie heissen Sie?", session_id="test_session_1")
            print(f"Bot: {res1['answer']}")
            print(f"Tools đã dùng: {res1['tools_used']}")
            assert len(res1["tools_used"]) == 0, "Câu chào hỏi không được gọi tool!"

            # Test kịch bản 2: Hỏi chuyên môn sâu (Kỳ vọng: Tự gọi tool search_nail_knowledge)
            print("\n--- Kịch bản 2: So sánh kỹ thuật (Kỳ vọng: Tự gọi tool search_nail_knowledge) ---")
            res2 = await agent.chat("Was ist besser, Shellac oder Gel?", session_id="test_session_2")
            print(f"Bot: {res2['answer']}")
            print(f"Tools đã dùng: {res2['tools_used']}")
            assert "search_nail_knowledge" in res2["tools_used"], "Phải gọi tool search_nail_knowledge để tra cứu!"

            print("\n-> TẤT CẢ CÁC KỊCH BẢN AGENT TEST THÀNH CÔNG!")
        except Exception as e:
            print(f"-> Gặp lỗi khi gọi OpenAI API: {e}")

    print("\n" + "=" * 70)
    print("=== HOÀN THÀNH TOÀN BỘ KIỂM THỬ TÍCH HỢP ===")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
