'use strict';

const net  = require('net');
const http = require('http');
const fs   = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const TCP_PORT  = 9876;
const WS_PORT   = 8765;
const HTTP_PORT = 3000;
const MAP_W = 20;
const MAP_H = 12;

// ─────────────────────────────────────────────
// Tile 상수
// ─────────────────────────────────────────────

const T = { WALL: 'wall', FLOOR: 'floor', EXIT: 'exit' };

const DIR = {
  north:[0,-1], n:[0,-1], '북':[0,-1],
  south:[0,+1], s:[0,+1], '남':[0,+1],
  west:[-1, 0], w:[-1,0], '서':[-1, 0],
  east:[+1, 0], e:[+1,0], '동':[+1, 0],
};

// ─────────────────────────────────────────────
// 게임 상태
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
// 난수 (시드 기반 — 맵 생성용)
// ─────────────────────────────────────────────

function makeRng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 0x100000000;
  };
}

// 전투용 난수 (완전 랜덤)
const rand = () => Math.random();

// ─────────────────────────────────────────────
// 맵 생성
// ─────────────────────────────────────────────

function generateLevel() {
  const rng  = makeRng(G.level * 42);
  const ri   = (a, b) => Math.floor(rng() * (b - a + 1)) + a;
  const free = (x, y) => G.map[y]?.[x] === T.FLOOR;

  // 외벽 + 바닥
  G.map = Array.from({ length: MAP_H }, (_, y) =>
    Array.from({ length: MAP_W }, (_, x) =>
      y === 0 || y === MAP_H-1 || x === 0 || x === MAP_W-1 ? T.WALL : T.FLOOR
    )
  );

  // 기둥
  for (let i = 0; i < G.level * 2; i++)
    G.map[ri(2, MAP_H-3)][ri(2, MAP_W-3)] = T.WALL;

  // 플레이어
  if (!G.player)
    G.player = { x:1, y:1, hp:30, maxHp:30, atk: 5+G.level, name:'플레이어' };
  else
    Object.assign(G.player, { x:1, y:1 });

  // 출구
  G.exitPos = [MAP_W-2, MAP_H-2];
  G.map[MAP_H-2][MAP_W-2] = T.EXIT;

  // 적
  const NAMES = ['슬라임','고블린','스켈레톤','오크','트롤'];
  G.enemies = [];
  for (let i = 0; i < 1+G.level; i++) {
    let x, y;
    do { x = ri(2, MAP_W-2); y = ri(2, MAP_H-2); } while (!free(x,y) || (x===1&&y===1));
    const hp = 8 + G.level * 3;
    G.enemies.push({ x, y, hp, maxHp:hp, atk:2+G.level, name:NAMES[i%NAMES.length], isBoss:false });
  }
  // 보스
  let bx, by;
  do { bx = ri(MAP_W>>1, MAP_W-2); by = ri(MAP_H>>1, MAP_H-2); } while (!free(bx,by));
  const bHp = 20 + G.level * 8;
  G.enemies.push({ x:bx, y:by, hp:bHp, maxHp:bHp, atk:5+G.level*2, name:`보스 Lv${G.level}`, isBoss:true });

  // 아이템
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

const alive     = ()     => G.enemies.filter(e => e.hp > 0);
const enemyAt   = (x, y) => G.enemies.find(e => e.hp > 0 && e.x === x && e.y === y);
const publicState = ()   => ({
  running: G.running, level: G.level, turn: G.turn,
  map: G.map, player: { ...G.player },
  enemies: G.enemies.map(e => ({ ...e })),
  items:   G.items.map(i => ({ ...i })),
  exitPos: G.exitPos,
  inventory: G.inventory.map(i => ({ ...i })),
  log: G.log.slice(-8),
  gameOver: G.gameOver,
});

function enemiesAct() {
  const msgs = [];
  const p = G.player;
  for (const e of alive()) {
    const dx = p.x - e.x, dy = p.y - e.y;
    const dist = Math.abs(dx) + Math.abs(dy);
    if (dist === 1) {
      const dmg = Math.max(1, e.atk - Math.floor(rand() * 3));
      p.hp -= dmg;
      msgs.push(`  ${e.name}이 공격! -${dmg} HP`);
    } else if (dist <= 4) {
      const sx = dx !== 0 ? Math.sign(dx) : 0;
      const sy = dx === 0 ? Math.sign(dy) : 0;
      const nx = e.x + sx, ny = e.y + sy;
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

  if (nx < 0||nx >= MAP_W||ny < 0||ny >= MAP_H) return fail('맵 경계입니다.');
  if (G.map[ny][nx] === T.WALL) return fail('벽이 있습니다.');
  if (enemyAt(nx, ny)) return fail(`적이 막고 있습니다. attack(${dir})으로 공격하세요.`);

  [p.x, p.y] = [nx, ny];
  G.turn++;
  G.log = [`${dir} 방향으로 이동 (${nx},${ny})`];

  for (const item of G.items)
    if (!item.collected && item.x === nx && item.y === ny)
      G.log.push(`  발 아래에 '${item.name}'! pickup으로 줍기`);

  if (nx === G.exitPos[0] && ny === G.exitPos[1]) {
    const cnt = alive().length;
    if (cnt === 0) { G.level++; generateLevel(); G.log.push(`다음 레벨로! (Lv ${G.level})`); }
    else G.log.push(`출구: 적 ${cnt}명 남음`);
  }

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
  for (const [dn, [dx, dy]] of [['북',[0,-1]],['남',[0,1]],['서',[-1,0]],['동',[1,0]]]) {
    const [nx, ny] = [x+dx, y+dy];
    if (nx<0||nx>=MAP_W||ny<0||ny>=MAP_H) { lines.push(`  ${dn}: 맵 경계`); continue; }
    if (G.map[ny][nx] === T.WALL) { lines.push(`  ${dn}: 벽`); continue; }
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

const tcpServer = net.createServer(socket => {
  let buf = '';
  socket.on('data', chunk => {
    buf += chunk.toString();
    const nl = buf.indexOf('\n');
    if (nl === -1) return;
    const line = buf.slice(0, nl);
    buf = buf.slice(nl + 1);
    let result;
    try   { result = dispatch(JSON.parse(line)); }
    catch (e) { result = fail(`파싱 오류: ${e.message}`); }
    socket.write(JSON.stringify(result) + '\n');
    if (result.state) broadcast(result.state);
  });
});

// ─────────────────────────────────────────────
// WebSocket 서버 (Node.js → Browser)
// ─────────────────────────────────────────────

const wss = new WebSocketServer({ port: WS_PORT });
wss.on('connection', ws => {
  console.log('브라우저 연결됨');
  if (G.running || G.gameOver) ws.send(JSON.stringify(publicState()));
});

function broadcast(state) {
  const msg = JSON.stringify(state);
  wss.clients.forEach(c => { if (c.readyState === 1) c.send(msg); });
}

// ─────────────────────────────────────────────
// HTTP 서버 (game.html 서빙)
// ─────────────────────────────────────────────

const httpServer = http.createServer((req, res) => {
  fs.readFile(path.join(__dirname, 'game.html'), (err, data) => {
    if (err) { res.writeHead(404); res.end('game.html not found'); return; }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(data);
  });
});

// ─────────────────────────────────────────────
// 시작
// ─────────────────────────────────────────────

tcpServer.listen(TCP_PORT,  () => console.log(`TCP  서버: localhost:${TCP_PORT}`));
httpServer.listen(HTTP_PORT, () => console.log(`HTTP 서버: http://localhost:${HTTP_PORT}`));
wss.on('listening',          () => console.log(`WS   서버: ws://localhost:${WS_PORT}`));
console.log('\n브라우저에서 http://localhost:3000 을 열어주세요.\n');
