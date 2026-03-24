"""
MCP Server — 세 가지 도구를 제공하는 MCP 서버

연결 방식이 도구마다 다르다:
  1. Drawing    — 같은 프로세스에서 직접 임포트 (drawing.py)
  2. Experiment — 별도 Python 프로세스에 TCP 소켓으로 통신 (포트 9877)
  3. Game       — 별도 Node.js 프로세스에 TCP 소켓으로 통신 (포트 9876)

Claude는 각 함수의 docstring을 읽고 어떤 도구를 호출할지 판단한다.
따라서 사용자가 자연어로 말해도 ("게임 시작해줘") 알맞은 함수가 호출된다.
"""

import json
import os
import socket
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

import drawing

mcp = FastMCP("The Mogiyoon Mcp")

# server.py 파일이 있는 디렉토리 — 하위 스크립트 경로 계산에 사용
BASE   = os.path.dirname(__file__)
# MCP 서버를 실행한 Python 인터프리터 경로 (서브프로세스 실행 시 동일 환경 보장)
PYTHON = sys.executable
NODE   = "node"

# ─────────────────────────────────────────────
# 소켓 헬퍼
# ─────────────────────────────────────────────

def _send(port: int, cmd: dict, timeout: float = 5.0) -> str:
    """TCP 소켓으로 JSON 명령을 전송하고 응답 메시지를 반환한다.

    프로토콜: JSON 한 줄 + 개행(\n)으로 메시지 경계를 구분한다.
    서버도 동일하게 JSON + \n 으로 응답하므로 \n이 오면 수신 완료로 판단한다.
    """
    try:
        with socket.create_connection(("localhost", port), timeout=timeout) as s:
            # 명령을 JSON 직렬화 후 \n을 붙여 전송 (메시지 경계 구분자)
            s.sendall((json.dumps(cmd, ensure_ascii=False) + "\n").encode())
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                # \n이 수신되면 응답 한 줄이 완성된 것
                if b"\n" in data:
                    break
        resp = json.loads(data.strip())
        return resp.get("message", "")
    except ConnectionRefusedError:
        # 서버가 꺼져 있을 때 어떤 서버인지 안내
        srv = "game_server.js" if port == 9876 else "experiment_server.py"
        return f"서버가 실행 중이 아닙니다. servers_start()를 먼저 실행하세요. ({srv})"
    except Exception as e:
        return f"오류: {e}"


# ═══════════════════════════════════════════════
# 1. Drawing Tools  (직접 임포트)
# ═══════════════════════════════════════════════
# drawing.py를 같은 프로세스에서 임포트해 함수를 직접 호출한다.
# 소켓 오버헤드 없이 가장 단순한 연결 방식.

@mcp.tool()
def drawing_create_canvas(width: int, height: int) -> str:
    """새 그림 캔버스를 생성합니다. width: 1-80, height: 1-40"""
    return drawing.create_canvas(width, height)

@mcp.tool()
def drawing_show() -> str:
    """현재 캔버스를 출력합니다."""
    return drawing.show_canvas()

@mcp.tool()
def drawing_clear() -> str:
    """캔버스를 모두 지웁니다."""
    return drawing.clear_canvas()

@mcp.tool()
def drawing_point(x: int, y: int, char: str = "dot") -> str:
    """캔버스의 (x, y) 위치에 문자를 찍습니다.
    char: 팔레트 키(h, v, tl, tr, bl, br, cross, dot, fill) 또는 단일 문자"""
    return drawing.draw_point(x, y, char)

@mcp.tool()
def drawing_hline(x: int, y: int, length: int, char: str = "h") -> str:
    """(x, y) 위치에서 오른쪽 방향으로 가로선을 그립니다."""
    return drawing.draw_hline(x, y, length, char)

@mcp.tool()
def drawing_vline(x: int, y: int, length: int, char: str = "v") -> str:
    """(x, y) 위치에서 아래 방향으로 세로선을 그립니다."""
    return drawing.draw_vline(x, y, length, char)

@mcp.tool()
def drawing_rect(x: int, y: int, width: int, height: int, filled: bool = False) -> str:
    """사각형을 그립니다. filled=True이면 내부를 채웁니다."""
    return drawing.draw_rect(x, y, width, height, filled)

@mcp.tool()
def drawing_text(x: int, y: int, text: str) -> str:
    """캔버스의 (x, y) 위치부터 텍스트를 씁니다."""
    return drawing.draw_text(x, y, text)

@mcp.tool()
def drawing_list_chars() -> str:
    """사용 가능한 문자 팔레트 목록을 반환합니다."""
    return drawing.list_chars()


# ═══════════════════════════════════════════════
# 2. Experiment Tools  (Python 소켓 → 포트 9877)
# ═══════════════════════════════════════════════
# experiment_server.py가 별도 프로세스로 실행 중이어야 한다.
# 모든 호출은 _send(9877, ...) 를 통해 JSON으로 전달된다.

@mcp.tool()
def exp_list_components(category: str = "") -> str:
    """실험에 사용할 수 있는 컴포넌트 목록을 반환합니다.
    category: 물질 | 환경 | 촉매 | 에너지 (비워두면 전체)"""
    return _send(9877, {"action": "list", "category": category})

@mcp.tool()
def exp_describe(name: str) -> str:
    """특정 컴포넌트의 상세 정보를 반환합니다."""
    return _send(9877, {"action": "describe", "name": name})

@mcp.tool()
def exp_select(names: list[str]) -> str:
    """실험에 사용할 컴포넌트를 선택합니다 (기존 선택 초기화).
    예: names=["산소", "수소", "고온"]"""
    return _send(9877, {"action": "select", "names": names})

@mcp.tool()
def exp_add(name: str) -> str:
    """현재 선택에 컴포넌트를 하나 추가합니다."""
    return _send(9877, {"action": "add", "name": name})

@mcp.tool()
def exp_remove(name: str) -> str:
    """현재 선택에서 컴포넌트를 제거합니다."""
    return _send(9877, {"action": "remove", "name": name})

@mcp.tool()
def exp_current() -> str:
    """현재 선택된 컴포넌트를 확인합니다."""
    return _send(9877, {"action": "current"})

@mcp.tool()
def exp_run() -> str:
    """선택된 컴포넌트들로 실험을 실행하고 결과를 반환합니다."""
    return _send(9877, {"action": "run"})

@mcp.tool()
def exp_history() -> str:
    """지금까지 진행한 실험 기록을 반환합니다."""
    return _send(9877, {"action": "history"})


# ═══════════════════════════════════════════════
# 3. Game Tools  (JS 소켓 → 포트 9876)
# ═══════════════════════════════════════════════
# game_server.js(Node.js)가 별도 프로세스로 실행 중이어야 한다.
# 게임 로직은 JS에서 처리되고, 결과는 WebSocket으로 브라우저에 push된다.

@mcp.tool()
def game_start() -> str:
    """던전 탐험 게임을 새로 시작합니다."""
    return _send(9876, {"action": "start"})

@mcp.tool()
def game_state() -> str:
    """현재 게임 화면과 플레이어 상태를 반환합니다."""
    return _send(9876, {"action": "state"})

@mcp.tool()
def game_move(direction: str) -> str:
    """플레이어를 이동합니다.
    direction: north/south/east/west 또는 n/s/e/w 또는 북/남/동/서"""
    return _send(9876, {"action": "move", "direction": direction})

@mcp.tool()
def game_attack(direction: str) -> str:
    """지정한 방향의 적을 공격합니다.
    direction: north/south/east/west 또는 n/s/e/w 또는 북/남/동/서"""
    return _send(9876, {"action": "attack", "direction": direction})

@mcp.tool()
def game_pickup() -> str:
    """발 아래에 있는 아이템을 줍습니다."""
    return _send(9876, {"action": "pickup"})

@mcp.tool()
def game_use_item(item_name: str) -> str:
    """인벤토리에서 아이템을 사용합니다."""
    return _send(9876, {"action": "use_item", "item": item_name})

@mcp.tool()
def game_look() -> str:
    """주변 4방향을 자세히 살펴봅니다."""
    return _send(9876, {"action": "look"})


# ═══════════════════════════════════════════════
# 4. 서버 관리
# ═══════════════════════════════════════════════

@mcp.tool()
def servers_start() -> str:
    """게임 서버(Node.js)와 실험 서버(Python)를 실행하고 브라우저를 엽니다."""
    msgs = []

    # game_server.js: Node.js로 실행, stdout/stderr는 버림 (백그라운드 데몬처럼 동작)
    try:
        subprocess.Popen(
            [NODE, os.path.join(BASE, "game_server.js")],
            cwd=BASE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        msgs.append("게임 서버 시작 (JS, 포트 9876)")
    except Exception as e:
        msgs.append(f"게임 서버 실패: {e}")

    # experiment_server.py: MCP와 동일한 Python 인터프리터로 실행
    try:
        subprocess.Popen(
            [PYTHON, os.path.join(BASE, "experiment_server.py")],
            cwd=BASE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        msgs.append("실험 서버 시작 (Python, 포트 9877)")
    except Exception as e:
        msgs.append(f"실험 서버 실패: {e}")

    # macOS 전용: open 명령으로 기본 브라우저에서 game.html을 서빙하는 URL을 연다
    try:
        subprocess.Popen(["open", "http://localhost:3000"])
        msgs.append("브라우저 열기: http://localhost:3000")
    except Exception:
        msgs.append("브라우저를 직접 열어주세요: http://localhost:3000")

    return "\n".join(msgs)


@mcp.tool()
def open_viewer() -> str:
    """드로잉 결과를 실시간으로 보여주는 tkinter GUI 창을 엽니다."""
    try:
        subprocess.Popen(
            [PYTHON, os.path.join(BASE, "display.py")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return "라이브 뷰어 창을 열었습니다."
    except Exception as e:
        return f"뷰어 실행 실패: {e}"


# ═══════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    # stdio 모드로 실행 — Claude Desktop이 이 프로세스의 stdin/stdout으로 MCP 통신
    mcp.run()
