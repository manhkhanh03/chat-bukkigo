from chat_bukkigo.router import Intent, route


def test_tet_advice_loads_aesthetic_context_without_safety() -> None:
    decision = route("Tư vấn cho tôi bộ móng đẹp đi chơi Tết, sang nhưng không quá nổi")

    assert decision.intent is Intent.AESTHETIC
    assert "occasion-guides.md" in decision.references
    assert "style-taxonomy.md" in decision.references
    assert "safety-escalation.md" not in decision.references


def test_real_health_signal_routes_only_to_safety() -> None:
    decision = route("Sau khi làm gel vùng da quanh móng bị sưng đỏ và có mủ")

    assert decision.intent is Intent.SAFETY
    assert decision.references == ("safety-escalation.md",)


def test_technical_question_does_not_load_safety_by_default() -> None:
    decision = route("Gel và acrylic khác gì nhau về độ bền?")

    assert decision.intent is Intent.COMPARISON
    assert "safety-escalation.md" not in decision.references


def test_plain_technical_question_is_not_forced_into_consultation() -> None:
    decision = route("Quy trình tháo gel như thế nào?")

    assert decision.intent is Intent.TECHNICAL
    assert "consultation-playbook.md" not in decision.references
