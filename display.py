"""
Display - 게임 / 드로잉 / 실험 결과를 별도 GUI 창에 실시간으로 표시합니다.
MCP 서버가 state/ 폴더에 파일을 쓸 때마다 자동 업데이트됩니다.

실행: python3.12 display.py
"""

import tkinter as tk
from tkinter import ttk
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = {
    "game":       os.path.join(BASE, "state", "game.txt"),
    "drawing":    os.path.join(BASE, "state", "drawing.txt"),
    "experiment": os.path.join(BASE, "state", "experiment.txt"),
}

# 탭별 색상 테마
THEMES = {
    "game":       {"bg": "#0d1117", "fg": "#58d68d", "accent": "#f0e68c"},
    "drawing":    {"bg": "#0d1117", "fg": "#85c1e9", "accent": "#f8c471"},
    "experiment": {"bg": "#0d1117", "fg": "#d2b4de", "accent": "#82e0aa"},
}

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
    POLL_MS = 300  # 상태 파일 폴링 주기

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MCP Live Viewer")
        self.root.configure(bg="#0d1117")
        self.root.geometry("900x650")
        self.root.resizable(True, True)

        self._mtimes = {k: None for k in STATE}
        self._setup_ui()
        self._poll()

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

        # 탭 노트북
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Custom.TNotebook",
            background="#0d1117", borderwidth=0,
        )
        style.configure(
            "Custom.TNotebook.Tab",
            background="#21262d", foreground="#8b949e",
            padding=[14, 6], font=("Menlo", 11),
        )
        style.map(
            "Custom.TNotebook.Tab",
            background=[("selected", "#1f6feb")],
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

            # 스크롤바
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side="right", fill="y")

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

            # 상태 표시줄
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

            # 초기 플레이스홀더 표시
            self._set_text(key, PLACEHOLDER[key])

    # ──────────────────────────────────────────
    # 폴링 & 업데이트
    # ──────────────────────────────────────────

    def _poll(self):
        for key, path in STATE.items():
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = None

            if mtime != self._mtimes[key]:
                self._mtimes[key] = mtime
                content = self._read(path)
                self._set_text(key, content or PLACEHOLDER[key])
                ts = time.strftime("%H:%M:%S") if mtime else "--:--:--"
                label = getattr(self, f"status_{key}")
                label.config(text=f"  마지막 업데이트: {ts}")

        self.root.after(self.POLL_MS, self._poll)

    def _read(self, path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, OSError):
            return None

    def _set_text(self, key: str, content: str):
        w = self.text_widgets[key]
        w.config(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", content)
        w.config(state="disabled")
        # 게임 로그는 맨 아래로 스크롤
        if key == "game":
            w.see("end")


def main():
    os.makedirs(os.path.join(BASE, "state"), exist_ok=True)
    root = tk.Tk()
    app = LiveDisplay(root)
    root.mainloop()


if __name__ == "__main__":
    main()
