'use strict';

/**
 * Game Server — Node.js 기반 던전 탐험 게임 서버
 *
 * 세 가지 인터페이스를 동시에 연다:
 *   TCP  :9876  — Python MCP 서버에서 JSON 명령 수신
 *   WS   :8765  — 게임 상태 변경 시 브라우저에 push
 *   HTTP :3000  — game.html 정적 파일 서빙
 *
 * 데이터 흐름:
 *   Claude → server.py → TCP 9876 → dispatch() → 게임 로직
 *                                                    └→ broadcast() → WS 8765 → 브라우저 Canvas
 */

const net  = require('net');
const http = require('http');
const fs   = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

// 포트 상수
const TCP_PORT  = 9876;   // Python MCP 서버 ↔ Node.js 통신
const WS_PORT   = 8765;   // Node.js ↔ 브라우저 WebSocket
const HTTP_PORT = 3000;   // game.html 서빙

// 맵 크기 (타일 단위)
const MAP_W = 20;
const MAP_H = 12;

// ─────────────────────────────────────────────
// 타일 상수 & 방향 테이블
// ─────────────────────────────────────────────

const T = { WALL: 'wall', FLOOR: 'floor', EXIT: 'exit' };

// 한글/영어/약어를 모두 허용한다 — Claude가 어떤 표현을 쓰더라도 처리됨
const DIR = {
  north:[0,-1], n:[0,-1], '북':[0,-1],
  south:[0,+1], s:[0,+1], '남':[0,+1],
  west:[-1, 0], w:[-1,0], '서':[-1, 0],
  east:[+1, 0], e:[+1,0], '동':[+1, 0],
};

// ─────────────────────────────────────────────
// 게임 전역 상태
// ─────────────────────────────────────────────

let G = emptyState();

function emptyState() {
  return {
    running: false, level: 1, turn: 0,
    map: [], player: null, enemies: [],
    items: [], exitPos: [0,0],
    inventory: [], log: [], gameOver: false,
  };
}

// ─────────────────────────────────────────────
// 난수 생성기
// ─────────────────────────────────────────────

/**
 * 선형 합동 생성기(LCG) 기반 시드 난수.
 * 레벨 번호를 시드로 사용하므로 같은 레벨은 항상 동일한 맵을 생성한다.
 * >>> 0 연산으로 부호 없는 32비트 정수를 유지한다.
 */
function makeRng(seed) {
  let s = seed >>> 0;
  return () => {
    // LCG 파라미터: Numerical Recipes 권장값
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 0x100000000;  // [0, 1) 범위로 정규화
  };
}

// 전투 결과는 시드 없이 완전 랜덤으로 처리
const rand = () => Math.random();

// ─────────────────────────────────────────────
// 맵 생성
// ─────────────────────────────────────────────

function generateLevel() {
  const rng  = makeRng(G.level * 42);           // 레벨마다 다른 시드
  const ri   = (a, b) => Math.floor(rng() * (b - a + 1)) + a;
  const free = (x, y) => G.map[y]?.[x] === T.FLOOR;

  // 외곽 벽 + 내부 바닥
  G.map = Array.from({ length: MAP_H }, (_, y) =>
    Array.from({ length: MAP_W }, (_, x) =>
      y === 0 || y === MAP_H-1 || x === 0 || x === MAP_W-1 ? T.WALL : T.FLOOR
    )
  );

  // 레벨에 비례하는 기둥 배치
  for (let i = 0; i < G.level * 2; i++)
    G.map[ri(2, MAP_H-3)][ri(2, MAP_W-3)] = T.WALL;

  // 플레이어: 첫 시작 시 생성, 레벨 이동 시 위치만 초기화
  if (!G.player)
    G.player = { x:1, y:1, hp:30, maxHp:30, atk: 5+G.level, name:'플레이어' };
  else
    Object.assign(G.player, { x:1, y:1 });

  // 출구는 항상 오른쪽 아래 모서리
  G.exitPos = [MAP_W-2, MAP_H-2];
  G.map[MAP_H-2][MAP_W-2] = T.EXIT;

  // 적 배치: 레벨 + 1마리 일반 적 + 보스 1마리
  const NAMES = ['슬라임','고블린','스켈레톤','오크','트롤'];
  G.enemies = [];
  for (let i = 0; i < 1+G.level; i++) {
    let x, y;
    // 빈 바닥이고 플레이어 시작 위치가 아닌 곳에 배치
    do { x = ri(2, MAP_W-2); y = ri(2, MAP_H-2); } while (!free(x,y) || (x===1&&y===1));
    const hp = 8 + G.level * 3;
    G.enemies.push({ x, y, hp, maxHp:hp, atk:2+G.level, name:NAMES[i%NAMES.length], isBoss:false });
  }
  // 보스는 맵 오른쪽 아래 사분면에 배치
  let bx, by;
  do { bx = ri(MAP_W>>1, MAP_W-2); by = ri(MAP_H>>1, MAP_H-2); } while (!free(bx,by));
  const bHp = 20 + G.level * 8;
  G.enemies.push({ x:bx, y:by, hp:bHp, maxHp:bHp, atk:5+G.level*2, name:`보스 Lv${G.level}`, isBoss:true });

  // 아이템 배치: 각 종류 1개씩
  G.items = [];
  const ITEM_DEFS = [
    { name:'체력 포션',       effect:'heal',       value:10+G.level*2 },
    { name:'힘의 룬',         effect:'atk_up',     value:2 },
    { name:'생명의 크리스탈', effect:'max_hp_up',  value:10 },
  ];
  for (const def of ITEM_DEFS) {
    let x, y;
    do { x = ri(1, MAP_W-2); y = ri(1, MAP_H-2); } while (!free(x,y));
    G.items.push({ ...def, x, y, collected:false });
  }

  G.inventory = [];
}

// ─────────────────────────────────────────────
// 헬퍼
// ─────────────────────────────────────────────

// 살아있는 적만 필터링
const alive = () => G.enemies.filter(e => e.hp > 0);

// 특정 좌표에 있는 살아있는 적 반환
const enemyAt = (x, y) => G.enemies.find(e => e.hp > 0 && e.x === x && e.y === y);

// 브라우저 전송용 상태 스냅샷 (깊은 복사)
const publicState = () => ({
  running: G.running, level: G.level, turn: G.turn,
  map: G.map, player: { ...G.player },
  enemies: G.enemies.map(e => ({ ...e })),
  items:   G.items.map(i => ({ ...i })),
  exitPos: G.exitPos,
  inventory: G.inventory.map(i => ({ ...i })),
  log: G.log.slice(-8),   // 최근 8줄만 전송
  gameOver: G.gameOver,
});

/**
 * 살아있는 모든 적이 행동한다 (맨해튼 거리 기반 AI).
 *   거리 1: 플레이어 공격
 *   거리 2~4: 플레이어 방향으로 한 칸 이동
 *   거리 5+: 대기
 */
function enemiesAct() {
  const msgs = [];
  const p = G.player;
  for (const e of alive()) {
    const dx = p.x - e.x, dy = p.y - e.y;
    const dist = Math.abs(dx) + Math.abs(dy);  // 맨해튼 거리
    if (dist === 1) {
      // 인접 시 공격 — 0~2 랜덤 방어력 차감
      const dmg = Math.max(1, e.atk - Math.floor(rand() * 3));
      p.hp -= dmg;
      msgs.push(`  ${e.name}이 공격! -${dmg} HP`);
    } else if (dist <= 4) {
      // 추적: x축 우선, x가 같으면 y축 이동
      const sx = dx !== 0 ? Math.sign(dx) : 0;
      const sy = dx === 0 ? Math.sign(dy) : 0;
      const nx = e.x + sx, ny = e.y + sy;
      // 벽이나 다른 적이 없을 때만 이동
      if (nx >= 0 && nx < MAP_W && ny >= 0 && ny < MAP_H &&
          G.map[ny][nx] !== T.WALL && !enemyAt(nx, ny))
        [e.x, e.y] = [nx, ny];
    }
  }
  return msgs;
}

// ─────────────────────────────────────────────
// 커맨드 핸들러
// ─────────────────────────────────────────────

function cmdStart() {
  G = emptyState();
  G.running = true; G.level = 1;
  generateLevel();
  G.log = ['게임 시작! 던전을 탐험하세요.'];
  return ok('게임 시작!');
}

function cmdMove(dir) {
  if (!G.running) return fail('게임이 실행 중이 아닙니다.');
  const d = DIR[dir?.toLowerCase()];
  if (!d) return fail(`알 수 없는 방향: ${dir}`);

  const p = G.player;
  const [nx, ny] = [p.x + d[0], p.y + d[1]];

  // 이동 가능성 검사
  if (nx < 0||nx >= MAP_W||ny < 0||ny >= MAP_H) return fail('맵 경계입니다.');
  if (G.map[ny][nx] === T.WALL) return fail('벽이 있습니다.');
  if (enemyAt(nx, ny)) return fail(`적이 막고 있습니다. attack(${dir})으로 공격하세요.`);

  [p.x, p.y] = [nx, ny];
  G.turn++;
  G.log = [`${dir} 방향으로 이동 (${nx},${ny})`];

  // 이동한 칸에 아이템이 있으면 안내
  for (const item of G.items)
    if (!item.collected && item.x === nx && item.y === ny)
      G.log.push(`  발 아래에 '${item.name}'! pickup으로 줍기`);

  // 출구 도달 처리
  if (nx === G.exitPos[0] && ny === G.exitPos[1]) {
    const cnt = alive().length;
    if (cnt === 0) { G.level++; generateLevel(); G.log.push(`다음 레벨로! (Lv ${G.level})`); }
    else G.log.push(`출구: 적 ${cnt}명 남음`);
  }

  // 이동 후 적 행동 → 사망 체크
  G.log.push(...enemiesAct());
  if (p.hp <= 0) { G.gameOver = true; G.running = false; G.log.push('💀 게임 오버!'); }
  return ok(G.log[0]);
}

function cmdAttack(dir) {
  if (!G.running) return fail('게임이 실행 중이 아닙니다.');
  const d = DIR[dir?.toLowerCase()];
  if (!d) return fail(`알 수 없는 방향: ${dir}`);

  const p = G.player;
  const target = enemyAt(p.x + d[0], p.y + d[1]);
  if (!target) return fail(`그 방향에 적이 없습니다.`);

  // 공격력에 0~2 랜덤 보너스
  const dmg = Math.max(1, p.atk + Math.floor(rand() * 3) - 1);
  target.hp -= dmg;
  G.turn++;
  G.log = [`${target.name}에게 ${dmg} 데미지! (HP: ${Math.max(0, target.hp)}/${target.maxHp})`];
  if (target.hp <= 0) {
    G.log.push(`  → ${target.name} 처치!`);
    if (target.isBoss) G.log.push('🏆 보스를 처치했습니다!');
  }
  G.log.push(...enemiesAct());
  if (p.hp <= 0) { G.gameOver = true; G.running = false; G.log.push('💀 게임 오버!'); }
  return ok(G.log[0]);
}

function cmdPickup() {
  if (!G.running) return fail('게임이 실행 중이 아닙니다.');
  const { x, y } = G.player;
  const item = G.items.find(i => !i.collected && i.x === x && i.y === y);
  if (!item) return fail('이 위치에 아이템이 없습니다.');
  item.collected = true;
  G.inventory.push(item);
  G.log = [`'${item.name}'을 획득했습니다!`];
  return ok(G.log[0]);
}

function cmdUseItem(name) {
  if (!G.running) return fail('게임이 실행 중이 아닙니다.');
  const idx = G.inventory.findIndex(i => i.name === name);
  if (idx === -1) return fail(`'${name}'이 인벤토리에 없습니다.`);
  const item = G.inventory.splice(idx, 1)[0];
  const p = G.player;
  // effect 종류에 따라 다른 효과 적용
  if (item.effect === 'heal') {
    const h = Math.min(item.value, p.maxHp - p.hp); p.hp += h;
    G.log = [`'${item.name}' → HP +${h} (${p.hp}/${p.maxHp})`];
  } else if (item.effect === 'atk_up') {
    p.atk += item.value;
    G.log = [`'${item.name}' → ATK +${item.value} (${p.atk})`];
  } else if (item.effect === 'max_hp_up') {
    p.maxHp += item.value; p.hp = Math.min(p.hp + item.value, p.maxHp);
    G.log = [`'${item.name}' → 최대HP +${item.value} (${p.hp}/${p.maxHp})`];
  }
  return ok(G.log[0]);
}

function cmdLook() {
  if (!G.running) return fail('게임이 실행 중이 아닙니다.');
  const { x, y } = G.player;
  const lines = [`현재 위치: (${x}, ${y})`];
  // 4방향 스캔
  for (const [dn, [dx, dy]] of [['북',[0,-1]],['남',[0,1]],['서',[-1,0]],['동',[1,0]]]) {
    const [nx, ny] = [x+dx, y+dy];
    if (nx<0||nx>=MAP_W||ny<0||ny>=MAP_H) { lines.push(`  ${dn}: 맵 경계`); continue; }
    if (G.map[ny][nx] === T.WALL)          { lines.push(`  ${dn}: 벽`);      continue; }
    const e = alive().find(e => e.x===nx && e.y===ny);
    const i = G.items.find(i => !i.collected && i.x===nx && i.y===ny);
    if (e)      lines.push(`  ${dn}: ${e.name} HP(${e.hp}/${e.maxHp})`);
    else if (i) lines.push(`  ${dn}: ${i.name}`);
    else if (nx===G.exitPos[0]&&ny===G.exitPos[1])
                lines.push(`  ${dn}: 출구 ${alive().length===0?'(진행 가능!)':'(적 남음)'}`);
    else        lines.push(`  ${dn}: 빈 통로`);
  }
  G.log = lines;
  return ok(lines.join('\n'));
}

// 응답 포맷: state를 항상 함께 반환 → 브라우저 화면 갱신에 사용
const ok   = msg => ({ ok:true,  message:msg, state: publicState() });
const fail = msg => ({ ok:false, message:msg, state: G.running ? publicState() : null });

function dispatch(cmd) {
  switch (cmd.action) {
    case 'start':    return cmdStart();
    case 'move':     return cmdMove(cmd.direction);
    case 'attack':   return cmdAttack(cmd.direction);
    case 'pickup':   return cmdPickup();
    case 'use_item': return cmdUseItem(cmd.item);
    case 'look':     return cmdLook();
    case 'state':    return G.running ? ok('현재 상태') : fail('게임이 실행 중이 아닙니다.');
    default:         return fail(`알 수 없는 명령: ${cmd.action}`);
  }
}

// ─────────────────────────────────────────────
// TCP 서버 (Python MCP → Node.js)
// ─────────────────────────────────────────────
// 프로토콜: JSON + \n — server.py 의 _send() 와 동일한 규약
// 명령을 처리한 뒤 결과를 JSON + \n 으로 반환하고, 브라우저에 상태를 broadcast한다.

const tcpServer = net.createServer(socket => {
  let buf = '';
  socket.on('data', chunk => {
    buf += chunk.toString();
    const nl = buf.indexOf('\n');
    if (nl === -1) return;  // 아직 한 줄이 완성되지 않음
    const line = buf.slice(0, nl);
    buf = buf.slice(nl + 1);
    let result;
    try   { result = dispatch(JSON.parse(line)); }
    catch (e) { result = fail(`파싱 오류: ${e.message}`); }
    socket.write(JSON.stringify(result) + '\n');
    // 게임 상태가 바뀌었으면 브라우저에 즉시 push
    if (result.state) broadcast(result.state);
  });
});

// ─────────────────────────────────────────────
// WebSocket 서버 (Node.js → Browser)
// ─────────────────────────────────────────────
// 브라우저가 연결되면 현재 상태를 즉시 전송한다 (새로고침 복구).
// 이후 게임 명령이 실행될 때마다 broadcast()로 상태를 push한다.

const wss = new WebSocketServer({ port: WS_PORT });
wss.on('connection', ws => {
  console.log('브라우저 연결됨');
  // 게임이 진행 중이거나 종료 상태면 현재 스냅샷 전송
  if (G.running || G.gameOver) ws.send(JSON.stringify(publicState()));
});

function broadcast(state) {
  const msg = JSON.stringify(state);
  // readyState === 1 (OPEN) 인 클라이언트에만 전송
  wss.clients.forEach(c => { if (c.readyState === 1) c.send(msg); });
}

// ─────────────────────────────────────────────
// HTTP 서버 (game.html 서빙)
// ─────────────────────────────────────────────
// 단순하게 game.html 하나만 서빙한다.
// 실제 게임 데이터는 WebSocket으로 전달되므로 정적 파일 서빙만 한다.

const httpServer = http.createServer((req, res) => {
  fs.readFile(path.join(__dirname, 'game.html'), (err, data) => {
    if (err) { res.writeHead(404); res.end('game.html not found'); return; }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(data);
  });
});

// ─────────────────────────────────────────────
// 서버 시작
// ─────────────────────────────────────────────

tcpServer.listen(TCP_PORT,   () => console.log(`TCP  서버: localhost:${TCP_PORT}`));
httpServer.listen(HTTP_PORT, () => console.log(`HTTP 서버: http://localhost:${HTTP_PORT}`));
wss.on('listening',          () => console.log(`WS   서버: ws://localhost:${WS_PORT}`));
console.log('\n브라우저에서 http://localhost:3000 을 열어주세요.\n');
