"""
Game Tool - ASCII 던전 탐험 게임
MCP 명령어로 플레이어를 조작합니다.
"""

import os
import random
from dataclasses import dataclass, field
from typing import Optional

_STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "game.txt")

def _save_state(content: str):
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(content)

# ───────────────────────────────────────────────
# 타일 / 엔티티 정의
# ───────────────────────────────────────────────

TILE_EMPTY   = " "
TILE_WALL    = "█"
TILE_FLOOR   = "·"
TILE_EXIT    = "▶"
TILE_ITEM    = "※"
TILE_PLAYER  = "@"
TILE_ENEMY   = "♟"
TILE_BOSS    = "♔"

DIRECTIONS = {
    "north": (0, -1), "n": (0, -1),
    "south": (0, +1), "s": (0, +1),
    "west":  (-1, 0), "w": (-1, 0),
    "east":  (+1, 0), "e": (+1, 0),
    "북": (0, -1), "남": (0, +1), "서": (-1, 0), "동": (+1, 0),
}

@dataclass
class Entity:
    name: str
    x: int
    y: int
    hp: int
    max_hp: int
    atk: int
    is_boss: bool = False

    def alive(self) -> bool:
        return self.hp > 0

    def hp_bar(self) -> str:
        ratio = self.hp / self.max_hp
        filled = int(ratio * 10)
        return "█" * filled + "░" * (10 - filled)

    def symbol(self) -> str:
        return TILE_BOSS if self.is_boss else TILE_ENEMY


@dataclass
class Item:
    name: str
    x: int
    y: int
    effect: str    # "heal" | "atk_up" | "max_hp_up"
    value: int
    collected: bool = False

    def symbol(self) -> str:
        return TILE_ITEM


# ───────────────────────────────────────────────
# 게임 상태
# ───────────────────────────────────────────────

class GameState:
    MAP_W = 20
    MAP_H = 12

    def __init__(self):
        self.reset()

    def reset(self):
        self.running = False
        self.level = 1
        self.turn = 0
        self.log: list[str] = []
        self.map: list[list[str]] = []
        self.player: Optional[Entity] = None
        self.enemies: list[Entity] = []
        self.items: list[Item] = []
        self.exit_pos: tuple[int, int] = (0, 0)
        self.inventory: list[Item] = []
        self.game_over = False
        self.victory = False

    def _generate_level(self):
        W, H = self.MAP_W, self.MAP_H
        # 외벽 + 내부 플로어
        self.map = [[TILE_WALL] * W for _ in range(H)]
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                self.map[y][x] = TILE_FLOOR

        # 내부 랜덤 기둥
        random.seed(self.level * 42)
        for _ in range(self.level * 2):
            wx = random.randint(2, W - 3)
            wy = random.randint(2, H - 3)
            self.map[wy][wx] = TILE_WALL

        # 플레이어 위치
        px, py = 1, 1
        if self.player is None:
            self.player = Entity("플레이어", px, py, 30, 30, 5 + self.level)
        else:
            self.player.x, self.player.y = px, py

        # 출구
        ex, ey = W - 2, H - 2
        self.exit_pos = (ex, ey)
        self.map[ey][ex] = TILE_EXIT

        # 적 배치
        enemy_count = 2 + self.level
        self.enemies = []
        names = ["슬라임", "고블린", "스켈레톤", "오크", "트롤"]
        for i in range(enemy_count - 1):
            while True:
                ex2 = random.randint(2, W - 2)
                ey2 = random.randint(2, H - 2)
                if self.map[ey2][ex2] == TILE_FLOOR and (ex2, ey2) != (px, py):
                    break
            name = names[i % len(names)]
            hp = 8 + self.level * 3
            self.enemies.append(Entity(name, ex2, ey2, hp, hp, 2 + self.level))
        # 보스
        while True:
            bx = random.randint(W // 2, W - 2)
            by = random.randint(H // 2, H - 2)
            if self.map[by][bx] == TILE_FLOOR:
                break
        boss_hp = 20 + self.level * 8
        self.enemies.append(Entity(f"보스 Lv{self.level}", bx, by, boss_hp, boss_hp, 5 + self.level * 2, is_boss=True))

        # 아이템 배치
        self.items = []
        item_defs = [
            ("체력 포션",  "heal",      10 + self.level * 2),
            ("힘의 룬",    "atk_up",    2),
            ("생명의 크리스탈", "max_hp_up", 10),
        ]
        for iname, ieffect, ival in item_defs:
            while True:
                ix = random.randint(1, W - 2)
                iy = random.randint(1, H - 2)
                if self.map[iy][ix] == TILE_FLOOR:
                    break
            self.items.append(Item(iname, ix, iy, ieffect, ival))

    def _render(self) -> str:
        """현재 맵을 문자열로 렌더링합니다."""
        display = [row[:] for row in self.map]

        for item in self.items:
            if not item.collected and 0 <= item.y < self.MAP_H and 0 <= item.x < self.MAP_W:
                display[item.y][item.x] = TILE_ITEM

        for enemy in self.enemies:
            if enemy.alive() and 0 <= enemy.y < self.MAP_H and 0 <= enemy.x < self.MAP_W:
                display[enemy.y][enemy.x] = enemy.symbol()

        if self.player and 0 <= self.player.y < self.MAP_H and 0 <= self.player.x < self.MAP_W:
            display[self.player.y][self.player.x] = TILE_PLAYER

        border = "─" * (self.MAP_W + 2)
        lines = [f"┌{border}┐"]
        for row in display:
            lines.append("│ " + "".join(row) + " │")
        lines.append(f"└{border}┘")

        # 범례
        lines.append(f"@ 플레이어  {TILE_ENEMY} 적  {TILE_BOSS} 보스  {TILE_ITEM} 아이템  {TILE_EXIT} 출구  █ 벽")
        return "\n".join(lines)

    def _render_status(self) -> str:
        p = self.player
        lines = [
            f"레벨 {self.level}  |  턴 {self.turn}",
            f"HP: {p.hp}/{p.max_hp}  [{p.hp_bar()}]  ATK: {p.atk}",
            f"인벤토리: {', '.join(i.name for i in self.inventory) or '없음'}",
            f"살아있는 적: {sum(1 for e in self.enemies if e.alive())}",
        ]
        return "\n".join(lines)

    def _enemies_act(self) -> list[str]:
        """적들이 행동합니다."""
        logs = []
        p = self.player
        for enemy in self.enemies:
            if not enemy.alive():
                continue
            dx = p.x - enemy.x
            dy = p.y - enemy.y
            dist = abs(dx) + abs(dy)
            if dist == 1:
                dmg = max(1, enemy.atk - random.randint(0, 2))
                p.hp -= dmg
                logs.append(f"  {enemy.name}이 공격! -{dmg} HP")
            elif dist <= 4:
                # 플레이어 방향으로 한 칸 이동
                step_x = (1 if dx > 0 else -1) if dx != 0 else 0
                step_y = (1 if dy > 0 else -1) if dy != 0 else 0 if dx != 0 else (1 if dy > 0 else -1)
                nx, ny = enemy.x + step_x, enemy.y + step_y
                if 0 <= nx < self.MAP_W and 0 <= ny < self.MAP_H:
                    if self.map[ny][nx] != TILE_WALL and not any(e.x == nx and e.y == ny and e.alive() for e in self.enemies):
                        enemy.x, enemy.y = nx, ny
        return logs


_state = GameState()


# ───────────────────────────────────────────────
# 공개 API
# ───────────────────────────────────────────────

def start_game() -> str:
    """새 게임을 시작합니다."""
    _state.reset()
    _state.running = True
    _state.level = 1
    _state._generate_level()
    _state.log = ["게임 시작! 던전을 탐험하세요."]
    result = "\n".join([
        "=== 던전 탐험 시작 ===",
        _state._render(),
        "",
        _state._render_status(),
        "",
        "명령어: move(방향), attack(방향), pickup, use_item(아이템명), look",
    ])
    _save_state(result)
    return result


def get_state() -> str:
    """현재 게임 화면과 상태를 반환합니다."""
    if not _state.running:
        return "게임이 실행 중이 아닙니다. start_game으로 시작하세요."
    lines = [_state._render(), "", _state._render_status()]
    if _state.log:
        lines.append("\n[최근 로그]")
        lines.extend(f"  {l}" for l in _state.log[-5:])
    result = "\n".join(lines)
    _save_state(result)
    return result


def move(direction: str) -> str:
    """플레이어를 이동합니다. 방향: north/south/east/west (또는 n/s/e/w, 북/남/동/서)"""
    if not _state.running:
        return "게임이 실행 중이 아닙니다."
    if _state.game_over or _state.victory:
        return "게임이 종료되었습니다. start_game으로 다시 시작하세요."

    d = DIRECTIONS.get(direction.lower())
    if not d:
        return f"알 수 없는 방향: '{direction}'. north/south/east/west 또는 n/s/e/w를 사용하세요."

    p = _state.player
    nx, ny = p.x + d[0], p.y + d[1]

    if not (0 <= nx < _state.MAP_W and 0 <= ny < _state.MAP_H):
        return "맵 경계입니다."
    if _state.map[ny][nx] == TILE_WALL:
        return "벽이 있습니다."
    if any(e.x == nx and e.y == ny and e.alive() for e in _state.enemies):
        return f"적이 막고 있습니다. attack({direction})으로 공격하세요."

    p.x, p.y = nx, ny
    _state.turn += 1
    _state.log = [f"{direction} 방향으로 이동 ({nx},{ny})"]

    # 아이템 자동 알림
    for item in _state.items:
        if not item.collected and item.x == nx and item.y == ny:
            _state.log.append(f"발 아래에 '{item.name}'이 있습니다! pickup 명령으로 줍기")

    # 출구 도달
    if (nx, ny) == _state.exit_pos:
        alive_enemies = sum(1 for e in _state.enemies if e.alive())
        if alive_enemies == 0:
            _state.level += 1
            _state._generate_level()
            _state.log.append(f"다음 레벨로 이동! (레벨 {_state.level})")
        else:
            _state.log.append(f"출구에 도달했지만 적이 {alive_enemies}명 남아있습니다!")

    # 적 행동
    enemy_logs = _state._enemies_act()
    _state.log.extend(enemy_logs)

    if p.hp <= 0:
        _state.game_over = True
        _state.running = False
        return get_state() + "\n\n💀 게임 오버! start_game으로 다시 시작하세요."

    return get_state()


def attack(direction: str) -> str:
    """방향으로 공격합니다."""
    if not _state.running:
        return "게임이 실행 중이 아닙니다."
    if _state.game_over or _state.victory:
        return "게임이 종료되었습니다."

    d = DIRECTIONS.get(direction.lower())
    if not d:
        return f"알 수 없는 방향: '{direction}'."

    p = _state.player
    tx, ty = p.x + d[0], p.y + d[1]

    target = next((e for e in _state.enemies if e.x == tx and e.y == ty and e.alive()), None)
    if not target:
        return f"({tx},{ty}) 방향에 공격할 대상이 없습니다."

    dmg = max(1, p.atk + random.randint(-1, 2))
    target.hp -= dmg
    _state.turn += 1
    _state.log = [f"{target.name}에게 {dmg} 데미지! (남은 HP: {max(0, target.hp)}/{target.max_hp})"]

    if not target.alive():
        _state.log.append(f"  → {target.name} 처치!")
        if target.is_boss:
            _state.log.append("  🏆 보스를 처치했습니다!")

    # 적 행동
    enemy_logs = _state._enemies_act()
    _state.log.extend(enemy_logs)

    if p.hp <= 0:
        _state.game_over = True
        _state.running = False
        return get_state() + "\n\n💀 게임 오버!"

    return get_state()


def pickup() -> str:
    """발 아래의 아이템을 줍습니다."""
    if not _state.running:
        return "게임이 실행 중이 아닙니다."
    p = _state.player
    item = next((i for i in _state.items if not i.collected and i.x == p.x and i.y == p.y), None)
    if not item:
        return "이 위치에 아이템이 없습니다."
    item.collected = True
    _state.inventory.append(item)
    _state.log = [f"'{item.name}'을 획득했습니다!"]
    return get_state()


def use_item(item_name: str) -> str:
    """인벤토리에서 아이템을 사용합니다."""
    if not _state.running:
        return "게임이 실행 중이 아닙니다."
    item = next((i for i in _state.inventory if i.name == item_name), None)
    if not item:
        inv = [i.name for i in _state.inventory]
        return f"'{item_name}'이 인벤토리에 없습니다. 보유: {', '.join(inv) or '없음'}"
    p = _state.player
    if item.effect == "heal":
        healed = min(item.value, p.max_hp - p.hp)
        p.hp += healed
        _state.log = [f"'{item.name}' 사용 → HP +{healed} (현재 {p.hp}/{p.max_hp})"]
    elif item.effect == "atk_up":
        p.atk += item.value
        _state.log = [f"'{item.name}' 사용 → ATK +{item.value} (현재 {p.atk})"]
    elif item.effect == "max_hp_up":
        p.max_hp += item.value
        p.hp = min(p.hp + item.value, p.max_hp)
        _state.log = [f"'{item.name}' 사용 → 최대 HP +{item.value} (현재 {p.hp}/{p.max_hp})"]
    _state.inventory.remove(item)
    return get_state()


def look() -> str:
    """주변 상황을 자세히 살펴봅니다."""
    if not _state.running:
        return "게임이 실행 중이 아닙니다."
    p = _state.player
    lines = [f"현재 위치: ({p.x}, {p.y})"]
    # 인접 셀 확인
    for dname, (dx, dy) in [("북", (0, -1)), ("남", (0, 1)), ("서", (-1, 0)), ("동", (1, 0))]:
        nx, ny = p.x + dx, p.y + dy
        if not (0 <= nx < _state.MAP_W and 0 <= ny < _state.MAP_H):
            lines.append(f"  {dname}: 맵 경계")
        elif _state.map[ny][nx] == TILE_WALL:
            lines.append(f"  {dname}: 벽")
        else:
            enemy = next((e for e in _state.enemies if e.x == nx and e.y == ny and e.alive()), None)
            item = next((i for i in _state.items if not i.collected and i.x == nx and i.y == ny), None)
            if enemy:
                lines.append(f"  {dname}: {enemy.name} (HP:{enemy.hp}/{enemy.max_hp} ATK:{enemy.atk})")
            elif item:
                lines.append(f"  {dname}: {item.name}")
            elif (nx, ny) == _state.exit_pos:
                alive = sum(1 for e in _state.enemies if e.alive())
                lines.append(f"  {dname}: 출구 {'(진행 가능!)' if alive == 0 else f'(적 {alive}명 남음)'}")
            else:
                lines.append(f"  {dname}: 빈 통로")
    return "\n".join(lines)
