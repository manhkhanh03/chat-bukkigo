from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    AESTHETIC = "aesthetic"
    COMPARISON = "comparison"
    TECHNICAL = "technical"
    SAFETY = "safety"


class ResponseMode(StrEnum):
    DIRECT = "direct"
    RECOMMEND = "recommend"
    EXPLORE = "explore"
    COMPARE = "compare"
    REFINE = "refine"
    SAFETY = "safety"


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    intent: Intent
    response_mode: ResponseMode
    references: tuple[str, ...]
    signals: tuple[str, ...]


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    plain = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", plain.replace("đ", "d")).strip()


SAFETY_SIGNALS = (
    "đau",
    "sưng",
    "chảy máu",
    "có mủ",
    "nung mủ",
    "ngứa",
    "rát",
    "nổi mẩn",
    "dị ứng",
    "nhiễm trùng",
    "nấm móng",
    "móng xanh",
    "móng đen",
    "móng vàng bất thường",
    "bong khỏi nền",
    "gãy sâu",
    "an toàn",
    "vệ sinh dụng cụ",
    "mang thai",
)

UNACCENTED_SAFETY_SIGNALS = (
    "sung",
    "chay mau",
    "co mu",
    "nung mu",
    "ngua",
    "noi man",
    "di ung",
    "nhiem trung",
    "nam mong",
    "mong xanh",
    "mong den",
    "mong vang bat thuong",
    "bong khoi nen",
    "gay sau",
    "an toan",
    "ve sinh dung cu",
    "mang thai",
    "bi dau",
    "mong dau",
    "dau quanh mong",
    "bi rat",
    "rat quanh mong",
)

OCCASION_SIGNALS = (
    "tet",
    "dam cuoi",
    "co dau",
    "du tiec",
    "di tiec",
    "phong van",
    "cong so",
    "di lam",
    "du lich",
    "di bien",
    "noel",
    "valentine",
    "halloween",
    "trung thu",
    "sinh nhat",
    "hen ho",
)

COLOR_SHAPE_SIGNALS = (
    "mau",
    "nude",
    "tong da",
    "da tay",
    "dang mong",
    "almond",
    "oval",
    "square",
    "squoval",
    "coffin",
    "ballerina",
    "stiletto",
    "mong ngan",
    "mong dai",
    "thon tay",
)

STYLE_SIGNALS = (
    "phong cach",
    "vibe",
    "toi gian",
    "thanh lich",
    "sang",
    "nu tinh",
    "trong treo",
    "de thuong",
    "cute",
    "ca tinh",
    "quyen ru",
    "nghe thuat",
    "co dien",
    "futuristic",
    "le hoi",
    "nhe nhang",
    "khong qua noi",
)

CONSULTATION_SIGNALS = (
    "tu van",
    "goi y",
    "hop voi toi",
    "hop minh",
    "nen chon",
    "ngan sach",
    "khong qua noi",
)

EXPLORE_SIGNALS = (
    "khong biet",
    "chua biet",
    "khong ro minh thich",
    "gi cung duoc",
    "phan van",
)

COMPARISON_SIGNALS = ("so voi", "khac gi", "chon cai nao", "mau nao hon", "a hay b")
TECHNICAL_SIGNALS = (
    "quy trinh",
    "cach lam",
    "cach thao",
    "do ben",
    "gel",
    "acrylic",
    "dap bot",
    "mong ep",
    "builder",
    "base coat",
    "top coat",
    "e-file",
)

REFINEMENT_SIGNALS = (
    "nhe hon",
    "dam hon",
    "noi hon",
    "bot noi",
    "bot dam",
    "them chut",
    "doi sang",
    "giu mau",
    "giu dang",
    "mau 1",
    "mau 2",
    "mau 3",
    "mau thu nhat",
    "mau thu hai",
    "mau thu ba",
    "huong 1",
    "huong 2",
    "huong 3",
    "cai nay",
    "cai kia",
    "the nay",
    "the kia",
    "van con",
)


def _matches(text: str, candidates: tuple[str, ...]) -> list[str]:
    return [
        candidate
        for candidate in candidates
        if re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", text)
    ]


def _safety_matches(message: str) -> list[str]:
    accented = re.sub(r"\s+", " ", message.casefold()).strip()
    matches = [normalize(value) for value in _matches(accented, SAFETY_SIGNALS)]
    matches.extend(_matches(normalize(message), UNACCENTED_SAFETY_SIGNALS))
    return list(dict.fromkeys(matches))


def _has_choice(text: str) -> bool:
    padded = f" {text} "
    return " hay " in padded and " hay khong " not in padded


def _response_mode(
    text: str,
    *,
    has_context: bool,
    comparison: list[str],
) -> ResponseMode:
    if comparison or _has_choice(text):
        return ResponseMode.COMPARE
    if has_context and _matches(text, REFINEMENT_SIGNALS):
        return ResponseMode.REFINE
    if _matches(text, EXPLORE_SIGNALS):
        return ResponseMode.EXPLORE
    if _matches(text, CONSULTATION_SIGNALS):
        return ResponseMode.RECOMMEND
    return ResponseMode.DIRECT


def _aesthetic_references(
    *,
    mode: ResponseMode,
    occasion: list[str],
    color_shape: list[str],
    style: list[str],
) -> tuple[str, ...]:
    refs: list[str] = []
    if color_shape:
        refs.append("color-and-proportion.md")
    if occasion:
        refs.append("occasion-guides.md")
    if style or mode is ResponseMode.EXPLORE:
        refs.append("style-taxonomy.md")

    if not refs:
        refs.append("aesthetic-principles.md")
    if mode in {ResponseMode.RECOMMEND, ResponseMode.EXPLORE} and len(refs) == 1:
        fallback = (
            "aesthetic-principles.md"
            if refs[0] == "style-taxonomy.md"
            else "style-taxonomy.md"
        )
        refs.append(fallback)

    return tuple(dict.fromkeys(refs[:2]))


def route(message: str, *, context: str | None = None) -> RoutingDecision:
    text = normalize(message)
    current_safety = _safety_matches(message)
    current_comparison = _matches(text, COMPARISON_SIGNALS)
    mode = _response_mode(
        text,
        has_context=bool(context),
        comparison=current_comparison,
    )

    routing_text = text
    if mode is ResponseMode.REFINE and context:
        routing_text = f"{normalize(context)} {text}".strip()

    safety = current_safety or (
        _safety_matches(context or "") if mode is ResponseMode.REFINE else []
    )
    if safety:
        return RoutingDecision(
            intent=Intent.SAFETY,
            response_mode=ResponseMode.SAFETY,
            references=("safety-escalation.md",),
            signals=tuple(safety),
        )

    occasion = _matches(routing_text, OCCASION_SIGNALS)
    color_shape = _matches(routing_text, COLOR_SHAPE_SIGNALS)
    style = _matches(routing_text, STYLE_SIGNALS)
    consultation = _matches(routing_text, CONSULTATION_SIGNALS)
    exploration = _matches(routing_text, EXPLORE_SIGNALS)
    comparison = _matches(routing_text, COMPARISON_SIGNALS)
    technical = _matches(routing_text, TECHNICAL_SIGNALS)

    intent = Intent.AESTHETIC
    if comparison or _has_choice(routing_text):
        intent = Intent.COMPARISON
    elif technical and not (occasion or style or consultation or color_shape):
        intent = Intent.TECHNICAL

    if technical:
        refs = ("technical-basics.md",)
    else:
        refs = _aesthetic_references(
            mode=mode,
            occasion=occasion,
            color_shape=color_shape,
            style=style,
        )

    return RoutingDecision(
        intent=intent,
        response_mode=mode,
        references=refs,
        signals=tuple(
            dict.fromkeys(
                occasion
                + color_shape
                + style
                + consultation
                + exploration
                + comparison
                + technical
            )
        ),
    )
