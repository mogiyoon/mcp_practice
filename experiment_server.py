"""
Experiment Server - TCP 소켓으로 실험 명령을 받아 처리하는 독립 서버
포트: 9877

MCP 서버(server.py)와 별도 프로세스로 실행되며,
JSON 명령을 받아 experiment.py의 함수를 호출하고 JSON 결과를 반환한다.

프로토콜: JSON 한 줄 + 개행(\n) — server.py 의 _send() 함수와 동일한 규약 사용
"""

import json
import socketserver
import threading
from experiment import (
    list_components, describe_component,
    select_components, add_component, remove_component,
    get_current_selection, run_experiment, get_history,
)

TCP_PORT = 9877


# ─────────────────────────────────────────────
# 요청 핸들러
# ─────────────────────────────────────────────

class Handler(socketserver.StreamRequestHandler):
    """각 TCP 연결마다 새 스레드로 실행된다.
    readline()으로 JSON 한 줄을 수신하고, dispatch()에 위임한 뒤 결과를 반환한다."""

    def handle(self):
        try:
            # \n 이 올 때까지 한 줄을 읽는다
            line   = self.rfile.readline().decode().strip()
            cmd    = json.loads(line)
            result = dispatch(cmd)
        except Exception as e:
            result = {"ok": False, "message": f"오류: {e}"}
        # JSON + \n 으로 응답 (server.py 의 _send 가 \n 을 경계로 수신)
        self.wfile.write((json.dumps(result, ensure_ascii=False) + "\n").encode())


# ─────────────────────────────────────────────
# 명령 디스패처
# ─────────────────────────────────────────────

def dispatch(cmd: dict) -> dict:
    """action 필드를 보고 experiment.py 의 적절한 함수를 호출한다."""
    action = cmd.get("action", "")
    try:
        if action == "list":
            return ok(list_components(cmd.get("category") or None))
        elif action == "describe":
            return ok(describe_component(cmd["name"]))
        elif action == "select":
            return ok(select_components(cmd["names"]))
        elif action == "add":
            return ok(add_component(cmd["name"]))
        elif action == "remove":
            return ok(remove_component(cmd["name"]))
        elif action == "current":
            return ok(get_current_selection())
        elif action == "run":
            return ok(run_experiment())
        elif action == "history":
            return ok(get_history())
        else:
            return fail(f"알 수 없는 명령: {action}")
    except KeyError as e:
        return fail(f"필수 파라미터 누락: {e}")


# 응답 포맷 헬퍼
def ok(message: str)   -> dict: return {"ok": True,  "message": message}
def fail(message: str) -> dict: return {"ok": False, "message": message}


# ─────────────────────────────────────────────
# TCP 서버
# ─────────────────────────────────────────────

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """요청마다 새 스레드를 생성하는 TCP 서버.

    allow_reuse_address: 프로세스 재시작 시 TIME_WAIT 상태의 포트를 즉시 재사용한다.
    daemon_threads:      메인 스레드 종료 시 자식 스레드도 함께 종료한다.
    """
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with ThreadedTCPServer(("localhost", TCP_PORT), Handler) as server:
        print(f"실험 서버 시작: localhost:{TCP_PORT}")
        server.serve_forever()
