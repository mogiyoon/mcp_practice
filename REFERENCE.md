# MCP Three Tools — Reference

## 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.10 이상 (권장 3.12) |
| mcp | `pip3 install mcp` |
| tkinter | `brew install python-tk@3.12` (macOS Homebrew) |

---

## 파일 구조

```
mcp_server/
├── server.py       FastMCP 서버 진입점
├── drawing.py      ASCII 캔버스 드로잉
├── experiment.py   실험 컴포넌트 조합
├── game.py         ASCII 던전 게임
├── display.py      tkinter 실시간 뷰어
└── state/          MCP → GUI 상태 파일 (자동 생성)
    ├── drawing.txt
    ├── experiment.txt
    └── game.txt
```

---

## MCP 도구 목록

### 🖥️ Viewer

| 도구 | 설명 |
|------|------|
| `open_viewer()` | tkinter GUI 창 열기 (Game / Drawing / Experiment 탭) |

---

### 🎨 Drawing

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `drawing_create_canvas(width, height)` | width: 1–80, height: 1–40 | 새 캔버스 생성 |
| `drawing_show()` | — | 현재 캔버스 출력 |
| `drawing_clear()` | — | 캔버스 초기화 |
| `drawing_point(x, y, char)` | char: 팔레트 키 또는 단일 문자 | 점 찍기 |
| `drawing_hline(x, y, length, char)` | char 기본값: `"h"` | 가로선 |
| `drawing_vline(x, y, length, char)` | char 기본값: `"v"` | 세로선 |
| `drawing_rect(x, y, width, height, filled)` | filled 기본값: False | 사각형 |
| `drawing_text(x, y, text)` | — | 텍스트 쓰기 |
| `drawing_list_chars()` | — | 팔레트 목록 확인 |

#### 문자 팔레트

| 키 | 문자 | 키 | 문자 |
|----|----|----|----|
| `h` | `─` | `v` | `│` |
| `tl` | `┌` | `tr` | `┐` |
| `bl` | `└` | `br` | `┘` |
| `cross` | `┼` | `t` | `┬` |
| `b` | `┴` | `l` | `├` |
| `r` | `┤` | `dot` | `·` |
| `fill` | `█` | `space` | ` ` |

---

### ⚗️ Experiment

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `exp_list_components(category)` | category: 물질·환경·촉매·에너지 (선택) | 컴포넌트 목록 |
| `exp_describe(name)` | — | 컴포넌트 상세 정보 |
| `exp_select(names)` | names: 컴포넌트 이름 리스트 | 실험 구성 설정 (초기화 후 재선택) |
| `exp_add(name)` | — | 현재 구성에 추가 |
| `exp_remove(name)` | — | 현재 구성에서 제거 |
| `exp_current()` | — | 현재 선택 확인 |
| `exp_run()` | — | 실험 실행 (최소 2개 필요) |
| `exp_history()` | — | 실험 기록 목록 |

#### 컴포넌트 목록

| 이름 | 카테고리 | 주요 태그 |
|------|----------|-----------|
| 산소 | 물질 | 기체, 산화 |
| 수소 | 물질 | 기체, 환원 |
| 탄소 | 물질 | 고체, 유기 |
| 물 | 물질 | 액체, 용매 |
| 소금 | 물질 | 고체, 이온 |
| 고온 | 환경 | 열, 에너지 |
| 저온 | 환경 | 냉각, 안정 |
| 고압 | 환경 | 압력 |
| 자외선 | 에너지 | 빛, 광화학 |
| 전기 | 에너지 | 전기, 이온 |
| 철 촉매 | 촉매 | 금속, 촉매 |
| 효소 | 촉매 | 생물, 촉매 |

#### 반응 규칙

| 조합 | 반응 이름 |
|------|-----------|
| 산소 + 수소 | 폭발적 결합 |
| 산소 + 탄소 | 연소 반응 |
| 수소 + 탄소 | 탄화수소 합성 |
| 물 + 소금 | 이온 용해 |
| 산화 + 고온 | 산화 가속 |
| 환원 + 전기 | 전기 환원 |
| 광화학 + 유기 | 광합성 유사 반응 |
| 촉매 + 고온 | 촉매 분해 위험 |
| 생물 + 저온 | 효소 동결 |
| 이온 + 전기 | 전기분해 |
| 압력 + 기체 | 압축 반응 |
| 금속 + 산화 | 금속 산화 |

---

### 🎮 Game

| 도구 | 파라미터 | 설명 |
|------|----------|------|
| `game_start()` | — | 새 게임 시작 (레벨 1) |
| `game_state()` | — | 현재 화면 + 상태 출력 |
| `game_move(direction)` | north/south/east/west, n/s/e/w, 북/남/동/서 | 이동 |
| `game_attack(direction)` | 위와 동일 | 인접 방향 공격 |
| `game_pickup()` | — | 발 아래 아이템 줍기 |
| `game_use_item(item_name)` | 아이템 이름 문자열 | 인벤토리 아이템 사용 |
| `game_look()` | — | 4방향 주변 상세 확인 |

#### 맵 기호

| 기호 | 의미 |
|------|------|
| `@` | 플레이어 |
| `♟` | 일반 적 |
| `♔` | 보스 |
| `※` | 아이템 |
| `▶` | 출구 (다음 레벨) |
| `█` | 벽 |
| `·` | 바닥 |

#### 아이템 종류

| 이름 | 효과 |
|------|------|
| 체력 포션 | HP 회복 |
| 힘의 룬 | ATK 영구 증가 |
| 생명의 크리스탈 | 최대 HP 증가 |

#### 적 AI

- 플레이어가 **4칸 이내**: 플레이어 방향으로 1칸 이동
- 플레이어가 **1칸 이내**: 직접 공격
- 레벨이 올라갈수록 HP·ATK·개수 증가, 레벨 당 보스 1마리 포함

---

## 상태 파일

| 경로 | 갱신 시점 |
|------|-----------|
| `state/game.txt` | `game_start`, `game_move`, `game_attack`, `game_pickup`, `game_use_item` |
| `state/drawing.txt` | `drawing_create_canvas`, `drawing_clear`, `drawing_point`, `drawing_hline`, `drawing_vline`, `drawing_rect`, `drawing_text` |
| `state/experiment.txt` | `exp_run` |

---

## Claude Desktop 설정

파일 위치: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "three-tools": {
      "command": "python3.12 절대경로",
      "args": ["mcp_server/server.py 절대경로"]
    }
  }
}
```

Python 경로 확인:
```bash
which python3.12
# /opt/homebrew/opt/python@3.12/Frameworks/Python.framework/Versions/3.12/bin/python3.12
```

설정 후 Claude Desktop 재시작 필수.
