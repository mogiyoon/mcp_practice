"""
Experiment Server - TCP 소켓으로 실험 명령을 받아 처리하는 독립 서버
포트: 9877
MCP 서버에서 JSON 명령을 보내면 JSON 결과를 반환합니다.
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


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            line = self.rfile.readline().decode().strip()
            cmd  = json.loads(line)
            result = dispatch(cmd)
        except Exception as e:
            result = {"ok": False, "message": f"오류: {e}"}
        self.wfile.write((json.dumps(result, ensure_ascii=False) + "\n").encode())


def dispatch(cmd: dict) -> dict:
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


def ok(message: str)   -> dict: return {"ok": True,  "message": message}
def fail(message: str) -> dict: return {"ok": False, "message": message}


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with ThreadedTCPServer(("localhost", TCP_PORT), Handler) as server:
        print(f"실험 서버 시작: localhost:{TCP_PORT}")
        server.serve_forever()
