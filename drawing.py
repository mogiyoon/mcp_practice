"""
Drawing Tool - ASCII 캔버스에 선/도형을 그리는 프로그램
ㅡ(─), ㅣ(│), ㄱ(┐), ㄴ(└), ┌, ┘ 등의 문자로 그림을 그립니다.

상태는 전역 변수(_canvas, _width, _height)에 저장되고,
그리기 작업이 끝날 때마다 state/drawing.txt 파일에 저장된다.
tkinter 뷰어(display.py)는 이 파일의 변경을 감지해 화면을 갱신한다.
"""

import os
from typing import Optional

# ─────────────────────────────────────────────
# 캔버스 상태 (전역)
# ─────────────────────────────────────────────

# _canvas: 2차원 문자 배열 — _canvas[y][x] 로 접근
_canvas: list[list[str]] = []
_width:  int = 0
_height: int = 0

# MCP 서버가 있는 폴더 기준으로 state/ 디렉토리에 파일을 저장
_STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "drawing.txt")


def _save_state():
    """현재 캔버스를 state/drawing.txt 에 저장한다.
    display.py가 300ms마다 이 파일의 수정 시각(mtime)을 폴링해
    변화가 있으면 GUI를 업데이트한다."""
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(show_canvas())


# ─────────────────────────────────────────────
# 문자 팔레트 — MCP 도구에서 char 인자로 키를 전달하면 자동 변환
# ─────────────────────────────────────────────

CHARS = {
    "h":     "─",   # 가로선 (ㅡ)
    "v":     "│",   # 세로선 (ㅣ)
    "tl":    "┌",   # 왼쪽 위 모서리
    "tr":    "┐",   # 오른쪽 위 모서리
    "bl":    "└",   # 왼쪽 아래 모서리
    "br":    "┘",   # 오른쪽 아래 모서리
    "cross": "┼",   # 교차
    "t":     "┬",   # 위 T자
    "b":     "┴",   # 아래 T자
    "l":     "├",   # 왼쪽 T자
    "r":     "┤",   # 오른쪽 T자
    "dot":   "·",   # 점
    "fill":  "█",   # 채우기
    "space": " ",   # 빈 칸
}


# ─────────────────────────────────────────────
# 캔버스 기본 조작
# ─────────────────────────────────────────────

def create_canvas(width: int, height: int) -> str:
    """새 캔버스를 생성합니다.
    최대 크기는 80×40으로 제한한다 (터미널 가독성 고려)."""
    global _canvas, _width, _height
    _width  = max(1, min(width,  80))
    _height = max(1, min(height, 40))
    # 2차원 배열 초기화 — 모든 셀을 공백으로 채운다
    _canvas = [[" " for _ in range(_width)] for _ in range(_height)]
    _save_state()
    return f"캔버스 생성 완료: {_width}×{_height}"


def show_canvas() -> str:
    """현재 캔버스를 테두리 포함 문자열로 반환합니다."""
    if not _canvas:
        return "캔버스가 없습니다. create_canvas를 먼저 호출하세요."
    # 테두리 길이: 내부 너비 + 좌우 공백 2칸
    border_h = "─" * (_width + 2)
    lines = ["┌" + border_h + "┐"]
    for row in _canvas:
        lines.append("│ " + "".join(row) + " │")
    lines.append("└" + border_h + "┘")
    return "\n".join(lines)


def clear_canvas() -> str:
    """캔버스를 모두 공백으로 지웁니다."""
    global _canvas
    if not _canvas:
        return "캔버스가 없습니다."
    _canvas = [[" " for _ in range(_width)] for _ in range(_height)]
    _save_state()
    return "캔버스를 지웠습니다."


# ─────────────────────────────────────────────
# 그리기 함수
# ─────────────────────────────────────────────

def draw_point(x: int, y: int, char: str = "·") -> str:
    """특정 위치에 점(문자)을 찍습니다.
    char: CHARS 팔레트 키 또는 임의의 단일 문자."""
    if not _canvas:
        return "캔버스가 없습니다."
    if not (0 <= x < _width and 0 <= y < _height):
        return f"범위 초과: ({x}, {y}) — 캔버스 크기는 {_width}×{_height}"
    # 팔레트 키면 변환, 아니면 첫 번째 문자 사용
    _canvas[y][x] = CHARS.get(char, char[0] if char else "·")
    _save_state()
    return f"({x}, {y})에 '{_canvas[y][x]}' 그리기 완료"


def draw_hline(x: int, y: int, length: int, char: str = "h") -> str:
    """(x, y)에서 오른쪽으로 가로선을 그립니다.
    캔버스 경계를 벗어나는 부분은 무시한다."""
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
    """(x, y)에서 아래로 세로선을 그립니다.
    캔버스 경계를 벗어나는 부분은 무시한다."""
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
    """사각형을 그립니다.
    filled=True이면 내부를 █로 채우고, False이면 테두리만 그린다."""
    if not _canvas:
        return "캔버스가 없습니다."

    def put(px, py, c):
        """캔버스 범위 내에만 문자를 쓰는 헬퍼."""
        if 0 <= px < _width and 0 <= py < _height:
            _canvas[py][px] = c

    if filled:
        # 내부 전체를 채운다
        for fy in range(y, y + height):
            for fx in range(x, x + width):
                put(fx, fy, "█")
    else:
        # 네 모서리
        put(x,            y,            "┌")
        put(x + width-1,  y,            "┐")
        put(x,            y + height-1, "└")
        put(x + width-1,  y + height-1, "┘")
        # 위·아래 가로선
        for fx in range(x + 1, x + width - 1):
            put(fx, y,            "─")
            put(fx, y + height-1, "─")
        # 좌·우 세로선
        for fy in range(y + 1, y + height - 1):
            put(x,           fy, "│")
            put(x + width-1, fy, "│")

    _save_state()
    return f"사각형 그리기 완료: ({x},{y}) {width}×{height}"


def draw_text(x: int, y: int, text: str) -> str:
    """(x, y)부터 오른쪽으로 텍스트를 씁니다.
    캔버스 너비를 넘어가는 글자는 무시한다."""
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


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def list_chars() -> str:
    """사용 가능한 문자 팔레트 목록을 출력합니다."""
    lines = ["사용 가능한 문자 팔레트:"]
    for key, val in CHARS.items():
        lines.append(f"  '{key}' → {val}")
    return "\n".join(lines)
