"""
Experiment Tool - 다양한 실험 셋을 섞어서 실험하는 프로그램
실험 구성 요소(컴포넌트)들을 조합해 결과를 관찰합니다.
"""

import os
import random
from dataclasses import dataclass, field
from typing import Optional

_STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "experiment.txt")

def _save_state(content: str):
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(content)

# ───────────────────────────────────────────────
# 실험 컴포넌트 정의
# ───────────────────────────────────────────────

@dataclass
class ExpComponent:
    name: str
    category: str          # "물질" | "환경" | "촉매" | "에너지"
    description: str
    tags: list[str]
    properties: dict       # 수치 속성들

COMPONENTS: dict[str, ExpComponent] = {
    "산소":     ExpComponent("산소",     "물질",  "산화 반응을 촉진하는 기체",   ["기체", "산화"],    {"반응성": 8, "온도영향": 3}),
    "수소":     ExpComponent("수소",     "물질",  "가장 가벼운 환원성 기체",      ["기체", "환원"],    {"반응성": 9, "온도영향": 5}),
    "탄소":     ExpComponent("탄소",     "물질",  "유기물의 기본 원소",           ["고체", "유기"],    {"반응성": 4, "온도영향": 2}),
    "물":       ExpComponent("물",       "물질",  "범용 용매",                    ["액체", "용매"],    {"반응성": 1, "온도영향": 6}),
    "소금":     ExpComponent("소금",     "물질",  "이온성 화합물",                ["고체", "이온"],    {"반응성": 2, "온도영향": 1}),
    "고온":     ExpComponent("고온",     "환경",  "반응 속도를 가속",             ["열", "에너지"],    {"가속도": 7, "안정성": -4}),
    "저온":     ExpComponent("저온",     "환경",  "반응 속도를 억제",             ["냉각", "안정"],    {"가속도": -5, "안정성": 8}),
    "고압":     ExpComponent("고압",     "환경",  "기체 반응에 영향",             ["압력"],            {"가속도": 5, "안정성": -2}),
    "자외선":   ExpComponent("자외선",   "에너지","광화학 반응 유발",             ["빛", "광화학"],    {"반응성": 6, "온도영향": 2}),
    "전기":     ExpComponent("전기",     "에너지","전기화학 반응 유발",           ["전기", "이온"],    {"반응성": 7, "가속도": 4}),
    "철 촉매":  ExpComponent("철 촉매",  "촉매",  "반응 활성화 에너지를 낮춤",    ["금속", "촉매"],    {"가속도": 6, "반응성": 3}),
    "효소":     ExpComponent("효소",     "촉매",  "생화학 반응 전용 촉매",        ["생물", "촉매"],    {"가속도": 9, "안정성": 5}),
}

# 결과 규칙 테이블: (태그_세트_조합) → 결과 설명
REACTION_RULES: list[tuple[set, str, str]] = [
    ({"산소", "수소"},        "폭발적 결합",      "H₂O 생성 — 매우 격렬한 반응 (⚠️ 폭발 위험)"),
    ({"산소", "탄소"},        "연소 반응",        "CO₂ 생성 — 탄소가 산화됨"),
    ({"수소", "탄소"},        "탄화수소 합성",    "유기물 전구체 생성"),
    ({"물", "소금"},          "이온 용해",        "NaCl 이온화 — 전도성 용액 생성"),
    ({"산화", "고온"},        "산화 가속",        "고온에서 산화 반응 속도 3배 증가"),
    ({"환원", "전기"},        "전기 환원",        "전기분해로 환원 반응 유도"),
    ({"광화학", "유기"},      "광합성 유사 반응", "빛 에너지로 유기물 합성 시도"),
    ({"촉매", "고온"},        "촉매 분해 위험",   "⚠️ 고온에서 촉매 비활성화 가능"),
    ({"생물", "저온"},        "효소 동결",        "효소 활성 저하 — 반응 거의 중단"),
    ({"이온", "전기"},        "전기분해",         "이온이 전극으로 이동, 분리 반응"),
    ({"압력", "기체"},        "압축 반응",        "기체 농도 증가로 반응 속도 상승"),
    ({"금속", "산화"},        "금속 산화",        "금속 표면에 산화막 형성"),
]

# ───────────────────────────────────────────────
# 실험 세션 상태
# ───────────────────────────────────────────────

_session: dict = {
    "selected": [],      # 현재 선택된 컴포넌트 이름 목록
    "results": [],       # 실험 결과 기록
}


def list_components(category: Optional[str] = None) -> str:
    """사용 가능한 실험 컴포넌트 목록을 반환합니다."""
    items = COMPONENTS.values()
    if category:
        items = [c for c in items if c.category == category]
    lines = ["=== 실험 컴포넌트 목록 ==="]
    by_cat: dict[str, list] = {}
    for c in items:
        by_cat.setdefault(c.category, []).append(c)
    for cat, comps in by_cat.items():
        lines.append(f"\n[{cat}]")
        for c in comps:
            props = ", ".join(f"{k}:{v:+d}" for k, v in c.properties.items())
            lines.append(f"  {c.name:8s} — {c.description}")
            lines.append(f"           태그: {', '.join(c.tags)}  |  속성: {props}")
    return "\n".join(lines)


def describe_component(name: str) -> str:
    """특정 컴포넌트의 상세 정보를 반환합니다."""
    c = COMPONENTS.get(name)
    if not c:
        return f"'{name}' 컴포넌트를 찾을 수 없습니다. list_components로 목록을 확인하세요."
    lines = [
        f"=== {c.name} ===",
        f"카테고리: {c.category}",
        f"설명: {c.description}",
        f"태그: {', '.join(c.tags)}",
        "속성:",
    ]
    for k, v in c.properties.items():
        bar = "+" * max(0, v) if v > 0 else "-" * max(0, -v)
        lines.append(f"  {k:12s}: {v:+3d}  {bar}")
    return "\n".join(lines)


def select_components(names: list[str]) -> str:
    """실험에 사용할 컴포넌트를 선택합니다."""
    valid, invalid = [], []
    for name in names:
        if name in COMPONENTS:
            valid.append(name)
        else:
            invalid.append(name)
    _session["selected"] = valid
    lines = [f"선택된 컴포넌트: {', '.join(valid) if valid else '없음'}"]
    if invalid:
        lines.append(f"존재하지 않는 컴포넌트: {', '.join(invalid)}")
    return "\n".join(lines)


def add_component(name: str) -> str:
    """현재 선택에 컴포넌트를 추가합니다."""
    if name not in COMPONENTS:
        return f"'{name}' 컴포넌트를 찾을 수 없습니다."
    if name in _session["selected"]:
        return f"'{name}'은 이미 선택되어 있습니다."
    _session["selected"].append(name)
    return f"'{name}' 추가됨. 현재 선택: {', '.join(_session['selected'])}"


def remove_component(name: str) -> str:
    """현재 선택에서 컴포넌트를 제거합니다."""
    if name not in _session["selected"]:
        return f"'{name}'은 선택되어 있지 않습니다."
    _session["selected"].remove(name)
    return f"'{name}' 제거됨. 현재 선택: {', '.join(_session['selected']) or '없음'}"


def run_experiment() -> str:
    """현재 선택된 컴포넌트들로 실험을 실행합니다."""
    selected = _session["selected"]
    if len(selected) < 2:
        return "실험을 실행하려면 최소 2개의 컴포넌트가 필요합니다."

    comps = [COMPONENTS[n] for n in selected]

    # 전체 태그 수집
    all_tags: set[str] = set()
    for c in comps:
        all_tags.update(c.tags)
    all_names: set[str] = set(selected)

    # 속성 합산
    total_props: dict[str, int] = {}
    for c in comps:
        for k, v in c.properties.items():
            total_props[k] = total_props.get(k, 0) + v

    # 반응 규칙 매칭
    matched_reactions = []
    for rule_set, reaction_name, description in REACTION_RULES:
        # 이름 기반 또는 태그 기반 매칭
        if rule_set.issubset(all_names) or rule_set.issubset(all_tags):
            matched_reactions.append((reaction_name, description))

    # 결과 조립
    lines = [
        "=" * 40,
        f"실험 실행: {' + '.join(selected)}",
        "=" * 40,
        "\n[속성 합산]",
    ]
    for k, v in total_props.items():
        bar = "█" * min(abs(v), 15)
        sign = "+" if v >= 0 else ""
        lines.append(f"  {k:12s}: {sign}{v}  {bar}")

    lines.append("\n[반응 분석]")
    if matched_reactions:
        for name, desc in matched_reactions:
            lines.append(f"  ⚗️  {name}")
            lines.append(f"     → {desc}")
    else:
        lines.append("  특별한 반응 없음 — 안정적인 혼합물")

    # 종합 안정성 점수
    stability = total_props.get("안정성", 0) - total_props.get("반응성", 0) // 2
    if stability > 5:
        status = "매우 안정적 ✅"
    elif stability > 0:
        status = "보통 ⚠️"
    else:
        status = "불안정 / 위험 ❌"
    lines.append(f"\n[종합 안정성] {status} (점수: {stability:+d})")

    result_str = "\n".join(lines)
    _session["results"].append({
        "components": selected[:],
        "reactions": [r[0] for r in matched_reactions],
        "stability": stability,
    })
    _save_state(result_str)
    return result_str


def get_history() -> str:
    """지금까지의 실험 기록을 반환합니다."""
    if not _session["results"]:
        return "실험 기록이 없습니다."
    lines = ["=== 실험 기록 ==="]
    for i, r in enumerate(_session["results"], 1):
        lines.append(f"\n[실험 #{i}]")
        lines.append(f"  구성: {', '.join(r['components'])}")
        lines.append(f"  반응: {', '.join(r['reactions']) or '없음'}")
        lines.append(f"  안정성 점수: {r['stability']:+d}")
    return "\n".join(lines)


def get_current_selection() -> str:
    """현재 선택된 컴포넌트를 반환합니다."""
    sel = _session["selected"]
    if not sel:
        return "선택된 컴포넌트가 없습니다."
    lines = [f"현재 선택: {', '.join(sel)}"]
    for name in sel:
        c = COMPONENTS[name]
        lines.append(f"  - {c.name} ({c.category}): {c.description}")
    return "\n".join(lines)
