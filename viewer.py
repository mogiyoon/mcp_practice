"""
Viewer - 게임 / 드로잉 상태를 별도 터미널 창에 실시간으로 표시합니다.
사용법: python3.12 viewer.py [game|drawing]
"""

import sys
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILES = {
    "game":    os.path.join(BASE, "state", "game.txt"),
    "drawing": os.path.join(BASE, "state", "drawing.txt"),
}

TITLES = {
    "game":    "🎮  던전 탐험 게임 — 라이브 뷰어",
    "drawing": "🎨  ASCII 드로잉 — 라이브 뷰어",
}

HELP = {
    "game": (
        "명령어 (Claude에게 입력)\n"
        "  game_move('north'/'south'/'east'/'west')\n"
        "  game_attack('north'/...)\n"
        "  game_pickup()\n"
        "  game_use_item('체력 포션')\n"
        "  game_look()\n"
        "  game_start()  ← 새 게임"
    ),
    "drawing": (
        "명령어 (Claude에게 입력)\n"
        "  drawing_create_canvas(width, height)\n"
        "  drawing_rect(x, y, w, h)\n"
        "  drawing_hline(x, y, length)\n"
        "  drawing_vline(x, y, length)\n"
        "  drawing_text(x, y, 'text')\n"
        "  drawing_show()  ← 현재 상태 보기"
    ),
}


def clear():
    os.system("clear")


def read_state(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def render(mode: str):
    path = STATE_FILES[mode]
    title = TITLES[mode]
    help_text = HELP[mode]

    last_mtime = None

    print(f"\033[1;36m{title}\033[0m")
    print("Claude에게 명령을 내리면 이 창이 자동으로 업데이트됩니다.")
    print("종료: Ctrl+C\n")

    while True:
        try:
            mtime = os.path.getmtime(path) if os.path.exists(path) else None
        except OSError:
            mtime = None

        if mtime != last_mtime:
            last_mtime = mtime
            clear()
            print(f"\033[1;36m{'─' * 50}\033[0m")
            print(f"\033[1;36m  {title}\033[0m")
            print(f"\033[1;36m{'─' * 50}\033[0m\n")

            content = read_state(path)
            if content:
                print(content)
            else:
                print("  아직 상태가 없습니다.")
                print(f"  Claude에게 {'game_start()' if mode == 'game' else 'drawing_create_canvas(30, 10)'}를 입력해보세요.\n")

            print(f"\n\033[90m{'─' * 50}")
            print(help_text)
            print("─" * 50 + "\033[0m")

        time.sleep(0.3)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "game"
    if mode not in STATE_FILES:
        print(f"사용법: python3.12 viewer.py [game|drawing]")
        sys.exit(1)
    try:
        render(mode)
    except KeyboardInterrupt:
        print("\n뷰어를 종료했습니다.")
