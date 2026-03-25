# the-mogiyoon-mcp

Claude에게 자연어로 명령하면 게임 캐릭터가 움직이고, 캔버스에 그림이 그려지고, 실험이 실행되는 MCP 서버입니다.

세 가지 연결 방식을 모두 사용합니다.

| 도구 | 연결 방식 | 실행 환경 |
|------|-----------|-----------|
| 🎨 Drawing | 직접 임포트 | Python (server.py와 같은 프로세스) |
| ⚗️ Experiment | TCP 소켓 (9877) | Python 별도 프로세스 |
| 🎮 Game | TCP 소켓 (9876) | Node.js → 브라우저 Canvas |

```
Claude
  │ MCP
  ▼
server.py
  ├── drawing_*  →  import drawing.py
  ├── exp_*      →  TCP :9877  →  experiment_server.py
  └── game_*     →  TCP :9876  →  game_server.js
                                      │ WebSocket :8765
                                      └── game.html (브라우저)
```

---

## 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.10 이상 |
| Node.js | 16 이상 |
| ws | `npm install` |

---

## 설치

```bash
git clone <repo-url>
cd mcp_server

# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# Python 의존성 설치
pip install -r requirements.txt

# Node.js 의존성 설치
npm install
```

tkinter가 필요한 경우 (macOS Homebrew Python):
```bash
brew install python-tk
```

---

## Claude Desktop 연결

`~/Library/Application Support/Claude/claude_desktop_config.json`에 추가합니다.

시스템 Python 경로는 버전마다 다르므로, **프로젝트 venv를 사용하면 경로가 항상 고정**됩니다.

```json
{
  "mcpServers": {
    "the-mogiyoon-mcp": {
      "command": "/절대경로/mcp_server/.venv/bin/python",
      "args": ["/절대경로/mcp_server/server.py"]
    }
  }
}
```

절대경로 확인:
```bash
cd mcp_server
echo "$(pwd)/.venv/bin/python"
echo "$(pwd)/server.py"
```

설정 후 **Claude Desktop 재시작** 필수.

---

## 사용법

Claude Desktop에서 자연어로 말하면 됩니다.

```
서버 시작해줘
```

게임 서버(Node.js), 실험 서버(Python), 브라우저(`http://localhost:3000`)가 한 번에 실행됩니다.

### 게임

```
게임 시작해줘
동쪽으로 이동해줘
북쪽 적 공격해줘
아이템 주워줘
체력 포션 사용해줘
주변 살펴봐줘
```

### 그림

```
30x10 캔버스 만들어줘
사각형 그려줘
Hello 텍스트 써줘
```

### 실험

```
실험 컴포넌트 목록 보여줘
산소랑 수소에 고온 넣어서 실험해줘
실험 기록 보여줘
```

---

## 파일 구조

```
mcp_server/
├── server.py            MCP 서버 진입점 (FastMCP)
├── drawing.py           Drawing 로직
├── experiment.py        Experiment 로직
├── experiment_server.py Python TCP 서버 (포트 9877)
├── game_server.js       Node.js 서버 (TCP 9876 / WS 8765 / HTTP 3000)
├── game.html            브라우저 게임 화면 (Canvas)
├── display.py           tkinter 실시간 뷰어 (Drawing용)
├── game.py              Python 게임 로직 (레거시)
├── viewer.py            터미널 뷰어 (레거시)
└── package.json
```

---

## MCP 도구 목록

### 서버 관리

| 도구 | 설명 |
|------|------|
| `servers_start()` | 게임·실험 서버 실행 + 브라우저 오픈 |
| `open_viewer()` | tkinter Drawing 뷰어 열기 |

### Drawing

| 도구 | 파라미터 |
|------|----------|
| `drawing_create_canvas(width, height)` | 1–80, 1–40 |
| `drawing_show()` | |
| `drawing_clear()` | |
| `drawing_point(x, y, char)` | char: 팔레트 키 또는 단일 문자 |
| `drawing_hline(x, y, length, char)` | |
| `drawing_vline(x, y, length, char)` | |
| `drawing_rect(x, y, width, height, filled)` | |
| `drawing_text(x, y, text)` | |
| `drawing_list_chars()` | 팔레트 목록 확인 |

### Experiment

| 도구 | 파라미터 |
|------|----------|
| `exp_list_components(category)` | 물질·환경·촉매·에너지 |
| `exp_describe(name)` | |
| `exp_select(names)` | 리스트로 전달 |
| `exp_add(name)` | |
| `exp_remove(name)` | |
| `exp_current()` | |
| `exp_run()` | 최소 2개 필요 |
| `exp_history()` | |

### Game

| 도구 | 파라미터 |
|------|----------|
| `game_start()` | |
| `game_state()` | |
| `game_move(direction)` | north/south/east/west, n/s/e/w, 북/남/동/서 |
| `game_attack(direction)` | 위와 동일 |
| `game_pickup()` | |
| `game_use_item(item_name)` | |
| `game_look()` | |

---

## 포트 정리

| 포트 | 용도 |
|------|------|
| 9876 | game_server.js TCP (MCP → 게임) |
| 8765 | game_server.js WebSocket (게임 → 브라우저) |
| 3000 | game_server.js HTTP (game.html 서빙) |
| 9877 | experiment_server.py TCP (MCP → 실험) |
