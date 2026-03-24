"""
Display — 게임 / 드로잉 / 실험 결과를 별도 GUI 창에 실시간으로 표시합니다.

동작 원리:
  MCP 도구(drawing_*, exp_*)가 실행될 때마다 state/ 폴더의 .txt 파일이 갱신된다.
  이 앱은 300ms마다 각 파일의 수정 시각(mtime)을 폴링해
  변화가 감지되면 해당 탭의 텍스트를 자동으로 업데이트한다.

실행: python3.12 display.py
"""

import tkinter as tk
from tkinter import ttk
import os
import time

# 이 스크립트 위치 기준으로 state/ 경로를 계산한다
BASE = os.path.dirname(os.path.abspath(__file__))

# 탭 키 → 상태 파일 경로 매핑
STATE = {
    "game":       os.path.join(BASE, "state", "game.txt"),
    "drawing":    os.path.join(BASE, "state", "drawing.txt"),
    "experiment": os.path.join(BASE, "state", "experiment.txt"),
}

# 탭별 색상 테마 (GitHub Dark 계열)
THEMES = {
    "game":       {"bg": "#0d1117", "fg": "#58d68d", "accent": "#f0e68c"},
    "drawing":    {"bg": "#0d1117", "fg": "#85c1e9", "accent": "#f8c471"},
    "experiment": {"bg": "#0d1117", "fg": "#d2b4de", "accent": "#82e0aa"},
}

# 상태 파일이 없을 때 탭에 표시할 안내 텍스트
PLACEHOLDER = {
    "game": (
        "┌─────────────────────────┐\n"
        "│   던전 탐험 게임          │\n"
        "│                         │\n"
        "│  Claude에게 입력하세요:   │\n"
        "│  game_start()           │\n"
        "└─────────────────────────┘"
    ),
    "drawing": (
        "┌─────────────────────────┐\n"
        "│   ASCII 드로잉 캔버스     │\n"
        "│                         │\n"
        "│  Claude에게 입력하세요:   │\n"
        "│  drawing_create_canvas  │\n"
        "│  (30, 12)               │\n"
        "└─────────────────────────┘"
    ),
    "experiment": (
        "┌─────────────────────────┐\n"
        "│   실험 결과              │\n"
        "│                         │\n"
        "│  Claude에게 입력하세요:   │\n"
        "│  exp_list_components()  │\n"
        "│  exp_select([...])      │\n"
        "│  exp_run()              │\n"
        "└─────────────────────────┘"
    ),
}


class LiveDisplay:
    POLL_MS = 300  # 파일 폴링 주기 (밀리초)

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MCP Live Viewer")
        self.root.configure(bg="#0d1117")
        self.root.geometry("900x650")
        self.root.resizable(True, True)

        # 탭별 마지막으로 확인한 mtime — None이면 아직 파일을 읽지 않은 상태
        self._mtimes = {k: None for k in STATE}

        self._setup_ui()
        self._poll()  # 폴링 루프 시작

    # ──────────────────────────────────────────
    # UI 구성
    # ──────────────────────────────────────────

    def _setup_ui(self):
        # 타이틀 바
        title_bar = tk.Frame(self.root, bg="#161b22", pady=6)
        title_bar.pack(fill="x")
        tk.Label(
            title_bar, text="⬡  MCP Live Viewer",
            font=("Menlo", 13, "bold"),
            bg="#161b22", fg="#c9d1d9",
        ).pack(side="left", padx=14)

        # 탭 노트북 스타일 설정
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.TNotebook",     background="#0d1117", borderwidth=0)
        style.configure(
            "Custom.TNotebook.Tab",
            background="#21262d", foreground="#8b949e",
            padding=[14, 6], font=("Menlo", 11),
        )
        style.map(
            "Custom.TNotebook.Tab",
            background=[("selected", "#1f6feb")],  # 선택된 탭: 파란색
            foreground=[("selected", "#ffffff")],
        )

        self.notebook = ttk.Notebook(self.root, style="Custom.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        self.text_widgets: dict[str, tk.Text] = {}
        tab_labels = {"game": "🎮  Game", "drawing": "🎨  Drawing", "experiment": "⚗️  Experiment"}

        for key, label in tab_labels.items():
            theme = THEMES[key]
            frame = tk.Frame(self.notebook, bg=theme["bg"])
            self.notebook.add(frame, text=label)

            # 세로 스크롤바
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side="right", fill="y")

            # 읽기 전용 텍스트 위젯 (state="disabled"로 사용자 입력 차단)
            text = tk.Text(
                frame,
                font=("Menlo", 12),
                bg=theme["bg"], fg=theme["fg"],
                insertbackground=theme["fg"],
                selectbackground="#264f78",
                relief="flat", bd=0,
                padx=16, pady=12,
                yscrollcommand=scrollbar.set,
                state="disabled", cursor="arrow",
                wrap="none",
            )
            text.pack(fill="both", expand=True)
            scrollbar.config(command=text.yview)

            # 하단 상태 표시줄 (마지막 업데이트 시각)
            status = tk.Label(
                frame,
                text="대기 중...",
                font=("Menlo", 10),
                bg="#161b22", fg="#8b949e",
                anchor="w", padx=12, pady=4,
            )
            status.pack(fill="x", side="bottom")

            self.text_widgets[key] = text
            setattr(self, f"status_{key}", status)

            # 파일이 없으면 플레이스홀더 표시
            self._set_text(key, PLACEHOLDER[key])

    # ──────────────────────────────────────────
    # 폴링 루프
    # ──────────────────────────────────────────

    def _poll(self):
        """POLL_MS마다 각 상태 파일의 mtime을 확인한다.
        이전 mtime과 다르면 파일을 읽어 해당 탭을 업데이트한다."""
        for key, path in STATE.items():
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = None  # 파일이 아직 없는 경우

            if mtime != self._mtimes[key]:
                self._mtimes[key] = mtime
                content = self._read(path)
                self._set_text(key, content or PLACEHOLDER[key])
                ts    = time.strftime("%H:%M:%S") if mtime else "--:--:--"
                label = getattr(self, f"status_{key}")
                label.config(text=f"  마지막 업데이트: {ts}")

        # after()로 재귀 예약 — tkinter 메인 루프 안에서 안전하게 실행된다
        self.root.after(self.POLL_MS, self._poll)

    def _read(self, path: str) -> str | None:
        """파일을 읽어 문자열로 반환한다. 파일이 없으면 None을 반환한다."""
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, OSError):
            return None

    def _set_text(self, key: str, content: str):
        """텍스트 위젯을 잠깐 활성화해 내용을 교체한 뒤 다시 비활성화한다."""
        w = self.text_widgets[key]
        w.config(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", content)
        w.config(state="disabled")
        # 게임 로그는 최신 내용이 아래에 있으므로 스크롤을 끝으로 내린다
        if key == "game":
            w.see("end")


def main():
    # state/ 폴더가 없으면 미리 생성 (파일 쓰기 전에 폴링이 시작될 수 있음)
    os.makedirs(os.path.join(BASE, "state"), exist_ok=True)
    root = tk.Tk()
    app = LiveDisplay(root)
    root.mainloop()


if __name__ == "__main__":
    main()
