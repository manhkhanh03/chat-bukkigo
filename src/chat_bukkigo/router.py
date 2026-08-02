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


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    intent: Intent
    references: tuple[str, ...]
    signals: tuple[str, ...]


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    plain = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", plain.replace("đ", "d")).strip()


SAFETY_SIGNALS = (
    "dau",
    "sung",
    "chay mau",
    "co mu",
    "nung mu",
    "ngua",
    "rat",
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
    "khong biet",
    "phan van",
    "hop voi toi",
    "hop minh",
    "nen chon",
    "ngan sach",
    "khong qua noi",
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


def _matches(text: str, candidates: tuple[str, ...]) -> list[str]:
    return [candidate for candidate in candidates if candidate in text]


def route(message: str) -> RoutingDecision:
    text = normalize(message)
    safety = _matches(text, SAFETY_SIGNALS)
    if safety:
        return RoutingDecision(
            intent=Intent.SAFETY,
            references=("safety-escalation.md",),
            signals=tuple(safety),
        )

    occasion = _matches(text, OCCASION_SIGNALS)
    color_shape = _matches(text, COLOR_SHAPE_SIGNALS)
    style = _matches(text, STYLE_SIGNALS)
    consultation = _matches(text, CONSULTATION_SIGNALS)
    comparison = _matches(text, COMPARISON_SIGNALS)
    technical = _matches(text, TECHNICAL_SIGNALS)

    intent = Intent.AESTHETIC
    if comparison or (" hay " in f" {text} " and technical):
        intent = Intent.COMPARISON
    elif technical and not (occasion or style or consultation or color_shape):
        intent = Intent.TECHNICAL

    refs: list[str] = ["aesthetic-principles.md"]
    if intent in {Intent.AESTHETIC, Intent.COMPARISON}:
        refs.extend(("consultation-playbook.md", "recommendation-patterns.md"))
    if occasion:
        refs.append("occasion-guides.md")
    if color_shape:
        refs.append("color-and-proportion.md")
    if style or consultation or (intent is Intent.AESTHETIC and not color_shape):
        refs.append("style-taxonomy.md")
    if intent in {Intent.AESTHETIC, Intent.COMPARISON}:
        refs.append("anti-patterns.md")

    return RoutingDecision(
        intent=intent,
        references=tuple(dict.fromkeys(refs)),
        signals=tuple(occasion + color_shape + style + consultation + comparison + technical),
    )
