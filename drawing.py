"""
Drawing Tool - ASCII 캔버스에 선/도형을 그리는 프로그램
ㅡ(─), ㅣ(│), ㄱ(┐), ㄴ(└), ┌, ┘ 등의 문자로 그림을 그립니다.
"""

import os
from typing import Optional

# 캔버스 상태 (전역)
_canvas: list[list[str]] = []
_width: int = 0

_STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "drawing.txt")

def _save_state():
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(show_canvas())
_height: int = 0

# 그리기에 사용할 문자 팔레트
CHARS = {
    "h":  "─",   # 가로선 (ㅡ)
    "v":  "│",   # 세로선 (ㅣ)
    "tl": "┌",   # 왼쪽 위 모서리 (ㄱ 반전)
    "tr": "┐",   # 오른쪽 위 모서리 (ㄱ)
    "bl": "└",   # 왼쪽 아래 모서리 (ㄴ)
    "br": "┘",   # 오른쪽 아래 모서리
    "cross": "┼", # 교차
    "t":  "┬",   # 위 T
    "b":  "┴",   # 아래 T
    "l":  "├",   # 왼쪽 T
    "r":  "┤",   # 오른쪽 T
    "dot": "·",
    "fill": "█",
    "space": " ",
}


def create_canvas(width: int, height: int) -> str:
    """새 캔버스를 생성합니다."""
    global _canvas, _width, _height
    _width = max(1, min(width, 80))
    _height = max(1, min(height, 40))
    _canvas = [[" " for _ in range(_width)] for _ in range(_height)]
    _save_state()
    return f"캔버스 생성 완료: {_width}×{_height}"


def show_canvas() -> str:
    """현재 캔버스를 문자열로 반환합니다."""
    if not _canvas:
        return "캔버스가 없습니다. create_canvas를 먼저 호출하세요."
    border_h = "─" * (_width + 2)
    lines = ["┌" + border_h + "┐"]
    for row in _canvas:
        lines.append("│ " + "".join(row) + " │")
    lines.append("└" + border_h + "┘")
    return "\n".join(lines)


def clear_canvas() -> str:
    """캔버스를 지웁니다."""
    global _canvas
    if not _canvas:
        return "캔버스가 없습니다."
    _canvas = [[" " for _ in range(_width)] for _ in range(_height)]
    _save_state()
    return "캔버스를 지웠습니다."


def draw_point(x: int, y: int, char: str = "·") -> str:
    """특정 위치에 점(문자)을 찍습니다."""
    if not _canvas:
        return "캔버스가 없습니다."
    if not (0 <= x < _width and 0 <= y < _height):
        return f"범위 초과: ({x}, {y}) — 캔버스 크기는 {_width}×{_height}"
    # 팔레트 키를 받으면 변환
    _canvas[y][x] = CHARS.get(char, char[0] if char else "·")
    _save_state()
    return f"({x}, {y})에 '{_canvas[y][x]}' 그리기 완료"


def draw_hline(x: int, y: int, length: int, char: str = "h") -> str:
    """가로선을 그립니다."""
    if not _canvas:
        return "캔버스가 없습니다."
    c = CHARS.get(char, char[0] if char else "─")
    drawn = 0
    for i in range(length):
        xi = x + i
        if 0 <= xi < _width and 0 <= y < _height:
            _canvas[y][xi] = c
            drawn += 1
    _save_state()
    return f"가로선 그리기 완료 ({drawn}칸)"


def draw_vline(x: int, y: int, length: int, char: str = "v") -> str:
    """세로선을 그립니다."""
    if not _canvas:
        return "캔버스가 없습니다."
    c = CHARS.get(char, char[0] if char else "│")
    drawn = 0
    for i in range(length):
        yi = y + i
        if 0 <= x < _width and 0 <= yi < _height:
            _canvas[yi][x] = c
            drawn += 1
    _save_state()
    return f"세로선 그리기 완료 ({drawn}칸)"


def draw_rect(x: int, y: int, width: int, height: int, filled: bool = False) -> str:
    """사각형을 그립니다."""
    if not _canvas:
        return "캔버스가 없습니다."

    def put(px, py, c):
        if 0 <= px < _width and 0 <= py < _height:
            _canvas[py][px] = c

    if filled:
        for fy in range(y, y + height):
            for fx in range(x, x + width):
                put(fx, fy, "█")
    else:
        # 모서리
        put(x, y, "┌");           put(x + width - 1, y, "┐")
        put(x, y + height - 1, "└"); put(x + width - 1, y + height - 1, "┘")
        # 위아래 테두리
        for fx in range(x + 1, x + width - 1):
            put(fx, y, "─")
            put(fx, y + height - 1, "─")
        # 좌우 테두리
        for fy in range(y + 1, y + height - 1):
            put(x, fy, "│")
            put(x + width - 1, fy, "│")

    _save_state()
    return f"사각형 그리기 완료: ({x},{y}) {width}×{height}"


def draw_text(x: int, y: int, text: str) -> str:
    """캔버스에 텍스트를 씁니다."""
    if not _canvas:
        return "캔버스가 없습니다."
    written = 0
    for i, ch in enumerate(text):
        xi = x + i
        if 0 <= xi < _width and 0 <= y < _height:
            _canvas[y][xi] = ch
            written += 1
    _save_state()
    return f"텍스트 쓰기 완료 ({written}자)"


def list_chars() -> str:
    """사용 가능한 문자 팔레트를 출력합니다."""
    lines = ["사용 가능한 문자 팔레트:"]
    for key, val in CHARS.items():
        lines.append(f"  '{key}' → {val}")
    return "\n".join(lines)
