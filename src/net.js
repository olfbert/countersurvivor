
// =====================================================================
// Mehrspieler (optional, gleiches WLAN): Raumcode ueber die PeerJS-Vermittlung, danach direkt per WebRTC.
// Der Host rechnet die Welt (Gegner, Wellen, Bosse). Jeder rechnet sich selbst: Waffen, Geld, Level, Beute.
// =====================================================================
const NET = { role: null, peer: null, code: '', name: '', idx: 0, nextIdx: 1, players: new Map(), ev: null, st: null, inRound: false,
  mirrors: new Map(), pend: new Map(), dmgQ: new Map(), stunQ: [], tick: 0, snapT: 0, stateT: 0, names: {}, bossInfo: null,
  avatars: new Map(), avatarList: [], rTurrets: [], rRoombas: [], tags: new Map(), lightCache: new Map() };
const NET_PREFIX = 'cssurv-';
const NET_MAX = 8; // Spieler pro Raum inkl. Host (Bandbreite des Host-Handys)
const QS = new URLSearchParams(location.search);

function loadPeerLib() {
  if (window.Peer) return Promise.resolve();
  return new Promise((res, rej) => {
    const s = document.createElement('script'); s.src = 'peerjs.min.js';
    s.onload = res; s.onerror = () => rej(new Error('peerjs.min.js konnte nicht geladen werden'));
    document.head.appendChild(s);
  });
}
function peerOpts() {
  const q = QS.get('peer');
  if (!q) return { debug: 1 };
  const [host, port] = q.split(':');
  return { host, port: +port || 9000, path: '/', secure: false, debug: 1 };
}
let CT_MODEL = null;
async function loadCtModel() {
  if (CT_MODEL) return;
  const mp = await loadPack('url:models_ct.bin');
  for (const m of mp.man.models) { CT_MODEL = await buildModel(m, mp.part); MODELS.push(CT_MODEL); }
}
function netName() {
  const n = ($('#mpName').value || '').trim().slice(0, 12) || 'Spieler';
  settings.mpName = n; saveSettings();
  return n;
}
function netStatus(s) { $('#mpStatus').innerHTML = s; }
function netSend(c, m) { if (c && c.open) try { c.send(m); } catch (e) { /* Verbindung weg */ } }
function netSendAll(m, except) { for (const P of NET.players.values()) if (P !== except) netSend(P.ev, m); }
function netReset() {
  if (NET.peer) try { NET.peer.destroy(); } catch (e) { /* egal */ }
  Object.assign(NET, { role: null, peer: null, code: '', ev: null, st: null, inRound: false, bossInfo: null });
  NET.players.clear(); NET.mirrors.clear(); NET.pend.clear(); NET.dmgQ.clear(); NET.stunQ = [];
  NET.avatars.clear(); NET.avatarList = []; NET.rTurrets = []; NET.rRoombas = [];
  for (const el of NET.tags.values()) el.remove();
  NET.tags.clear();
}
function netLobby() {
  const names = NET.role === 'host'
    ? [NET.name + ' (Host)', ...[...NET.players.values()].map(P => P.name)]
    : Object.values(NET.names);
  if (NET.role === 'host') netStatus(`Raum <b style="font-size:20px;letter-spacing:.1em">${NET.code}</b> · Code an die Mitspieler geben<br>Im Raum (${names.length}/${NET_MAX}): ${names.join(', ')}`);
  else if (NET.role === 'guest') netStatus(`Verbunden mit Raum <b>${NET.code}</b> · Im Raum (${names.length}/${NET_MAX}): ${names.join(', ') || '…'}<br>Der Host startet die Runde.`);
  const sb = $('#startBtn');
  if (NET.role === 'guest') { sb.disabled = true; sb.textContent = 'WARTE AUF HOST'; }
  else { sb.disabled = !NET.ready; sb.textContent = NET.role === 'host' ? 'SPIELEN (alle)' : 'SPIELEN'; }
  $('#mpLeave').style.display = NET.role ? '' : 'none';
  $('#mpHost').disabled = $('#mpJoin').disabled = !!NET.role;
  document.querySelectorAll('#mapPick button').forEach(b => { b.disabled = NET.role === 'guest'; });
}

// ---- Host
async function netHost() {
  netStatus('Erstelle Raum …');
  await loadPeerLib(); await loadCtModel();
  netReset();
  NET.role = 'host'; NET.name = netName(); NET.idx = 0; NET.nextIdx = 1;
  const tryOpen = () => new Promise((res, rej) => {
    const code = String(1000 + Math.floor(Math.random() * 9000));
    const peer = new Peer(NET_PREFIX + code, peerOpts());
    peer.on('open', () => { NET.code = code; res(peer); });
    peer.on('error', err => { if (err.type === 'unavailable-id') { peer.destroy(); res(null); } else rej(err); });
  });
  let peer = null;
  for (let i = 0; i < 5 && !peer; i++) peer = await tryOpen();
  if (!peer) throw new Error('kein freier Raumcode');
  NET.peer = peer;
  peer.on('connection', c => netHostConn(c));
  peer.on('error', err => console.warn('PeerJS', err.type));
  peer.on('disconnected', () => { try { peer.reconnect(); } catch (e) { /* laufende Verbindungen bleiben */ } });
  netLobby();
}
function netHostConn(c) {
  let P = NET.players.get(c.peer);
  if (!P && NET.players.size >= NET_MAX - 1) { // Raum voll: freundlich abweisen
    if (c.label === 'ev') c.on('open', () => { netSend(c, { t: 'full', max: NET_MAX }); setTimeout(() => c.close(), 500); });
    else setTimeout(() => c.close(), 500);
    return;
  }
  if (!P) {
    P = { id: c.peer, idx: NET.nextIdx++, name: 'Spieler', o: [0, 0, 0], yaw: 0, pitch: 0, ducked: false, alive: false, inRound: false,
      moving: false, node: -1, turrets: [], roombas: [], ev: null, st: null };
    NET.players.set(c.peer, P);
  }
  if (c.label === 'st') { P.st = c; c.on('data', d => netHostState(P, d)); }
  else {
    P.ev = c;
    c.on('data', m => netHostMsg(P, m));
    c.on('close', () => netDrop(P));
  }
}
function netDrop(P) {
  if (!NET.players.has(P.id)) return;
  NET.players.delete(P.id);
  toast(P.name + ' hat den Raum verlassen');
  netBroadcastPlayers(); netLobby();
}
function netBroadcastPlayers() {
  const list = { 0: NET.name };
  for (const P of NET.players.values()) list[P.idx] = P.name;
  NET.names = list;
  netSendAll({ t: 'players', list });
}
function netHostMsg(P, m) {
  if (m.t === 'hello') {
    P.name = String(m.name || 'Spieler').slice(0, 12);
    if (m.map !== MAP.id) { netSend(P.ev, { t: 'map', map: MAP.id }); return; }
    netSend(P.ev, { t: 'welcome', idx: P.idx });
    netBroadcastPlayers(); netLobby();
    toast(P.name + ' ist beigetreten');
    if (NET.inRound && !game.over) netSend(P.ev, { t: 'start', time: game.time, boss: NET.bossInfo });
  } else if (m.t === 'dmg') {
    for (const [id, dmg, head, wid] of m.d) { const e = enemyById(id); if (e) hostDamageRemote(e, dmg, !!head, P, wid); }
  } else if (m.t === 'stun') {
    for (const [id, t] of m.l) { const e = enemyById(id); if (e && e.state === ALIVE && !e.boss) e.stun = Math.max(e.stun || 0, t); }
  } else if (m.t === 'zone') {
    zones.push({ ghost: true, p: m.p, r: m.r, t: 0, dur: m.dur, slow: m.slow, seed: Math.random() * 100 });
  } else if (m.t === 'boom') {
    netShowBoom(m); netSendAll(m, P);
  } else if (m.t === 'dead') {
    P.alive = false;
  } else if (m.t === 'bye') {
    netDrop(P);
  }
}
let enemyIndex = new Map(), enemyIndexFrame = -1;
function enemyById(id) {
  if (enemyIndexFrame !== frameNo) { enemyIndexFrame = frameNo; enemyIndex = new Map(enemies.map(e => [e.id, e])); }
  return enemyIndex.get(id);
}
// Treffer eines Gastes: Schaden am echten Gegner, Belohnung (Geld, Kill) bekommt der Gast
function hostDamageRemote(e, dmg, head, P, wid) {
  if (e.state !== ALIVE) return;
  e.hp -= dmg; e.flash = 1;
  if (e.hp > 0) return;
  sfx(head ? 'headshot' : 'die', { pos: [e.x, e.y, e.z + 40], vol: e.boss ? 1 : 0.5, gap: e.boss ? 0 : 0.11, pitch: e.boss ? 0.75 : 1 });
  e.state = DYING; e.t = 0; e.f = 0; e.fuse = -1;
  e.seq = e.m.seq[head ? 'head' : DEATHS[(Math.random() * DEATHS.length) | 0]];
  netSend(P.ev, { t: 'kill', id: e.id, head, wid, xp: e.xp, elite: e.elite, boss: e.boss ? e.boss.name : null, key: e.key, x: e.x, y: e.y, z: e.z, scale: e.scale });
  if (e === game.boss) netBossDown(e, P.name);
}
function netBossDown(e, by) {
  game.boss = null;
  const s = e.boss.name + ' besiegt' + (by ? ' (' + by + ')' : '') + '!';
  toast(s); sfx('enemydown', { vol: 0.8, delay: 0.5, important: true });
  netSendAll({ t: 'toast', s, snd: 'enemydown' }); netSendAll({ t: 'bossdown' });
}
const qi = v => Math.max(-32767, Math.min(32767, Math.round(v * 4)));
function netHostState(P, d) {
  if (d instanceof Blob) { d.arrayBuffer().then(b => netHostState(P, b)); return; }
  const v = new DataView(d);
  if (v.getUint8(0) !== 2) return;
  let o = 1;
  P.o = [v.getFloat32(o, true), v.getFloat32(o + 4, true), v.getFloat32(o + 8, true)]; o += 12;
  P.yaw = v.getUint8(o++) / 256 * Math.PI * 2; P.pitch = v.getInt8(o++) / 100;
  const fl = v.getUint8(o++);
  P.alive = !!(fl & 1); P.ducked = !!(fl & 2); P.moving = !!(fl & 4); P.inRound = !!(fl & 8);
  o++;   // HP (nur Anzeige)
  [P.turrets, o] = readTurrets(v, o);
  [P.roombas, o] = readRoombas(v, o);
}
function writeTurrets(v, o, list) {
  v.setUint8(o++, list.length);
  for (const T of list) { v.setInt16(o, qi(T.x), true); v.setInt16(o + 2, qi(T.y), true); v.setInt16(o + 4, qi(T.z), true); o += 6; v.setUint8(o++, ((T.yaw / (Math.PI * 2)) * 256) & 255); v.setInt8(o++, Math.round(Math.max(-1.6, Math.min(1.6, T.aim)) * 70)); }
  return o;
}
function readTurrets(v, o) {
  const n = v.getUint8(o++), out = [];
  for (let i = 0; i < n; i++) { out.push({ x: v.getInt16(o, true) / 4, y: v.getInt16(o + 2, true) / 4, z: v.getInt16(o + 4, true) / 4, yaw: v.getUint8(o + 6) / 256 * Math.PI * 2, aim: v.getInt8(o + 7) / 70 }); o += 8; }
  return [out, o];
}
function writeRoombas(v, o, list) {
  v.setUint8(o++, list.length);
  for (const R of list) { v.setInt16(o, qi(R.x), true); v.setInt16(o + 2, qi(R.y), true); v.setInt16(o + 4, qi(R.z), true); o += 6; v.setUint8(o++, ((R.yaw / (Math.PI * 2)) * 256) & 255); }
  return o;
}
function readRoombas(v, o) {
  const n = v.getUint8(o++), out = [];
  for (let i = 0; i < n; i++) { out.push({ x: v.getInt16(o, true) / 4, y: v.getInt16(o + 2, true) / 4, z: v.getInt16(o + 4, true) / 4, yaw: v.getUint8(o + 6) / 256 * Math.PI * 2 }); o += 7; }
  return [out, o];
}
const ENEMY_BYTES = 24;
function netHostSnapshot(P) {
  const ow = (list, n) => list.slice(0, n);
  const near = [];
  for (const e of enemies) if (e === game.boss || (Math.abs(e.x - P.o[0]) < 2600 && Math.abs(e.y - P.o[1]) < 2600)) near.push(e);
  if (near.length > 900) near.length = 900;
  // andere Spieler: Host selbst + uebrige Gaeste
  const others = [{ idx: 0, o: player.o, yaw: player.yaw, alive: !game.dead && !game.over, ducked: !!player.ducked, moving: Math.hypot(player.v[0], player.v[1]) > 40, turrets: ow(turrets, 3), roombas: ow(roombas, 3) }];
  for (const Q of NET.players.values()) if (Q !== P && Q.inRound) others.push({ idx: Q.idx, o: Q.o, yaw: Q.yaw, alive: Q.alive, ducked: Q.ducked, moving: Q.moving, turrets: Q.turrets, roombas: Q.roombas });
  const shots = eShots.slice(0, 120);
  const size = 1 + 4 + 4 + 2 + 1 + 1 + near.length * ENEMY_BYTES + others.length * (1 + 6 + 1 + 1 + 1 + 3 * 8 + 1 + 3 * 7) + shots.length * 6;
  const buf = new ArrayBuffer(size), v = new DataView(buf);
  let o = 0;
  v.setUint8(o++, 1);
  v.setFloat32(o, game.time, true); o += 4;
  v.setFloat32(o, game.boss ? game.boss.hp : -1, true); o += 4;
  v.setUint16(o, near.length, true); o += 2;
  v.setUint8(o++, others.length); v.setUint8(o++, shots.length);
  for (const e of near) {
    v.setUint32(o, e.id, true); v.setInt16(o + 4, qi(e.x), true); v.setInt16(o + 6, qi(e.y), true); v.setInt16(o + 8, qi(e.z), true);
    v.setUint8(o + 10, ((((e.yaw % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2)) / (Math.PI * 2) * 256) & 255);
    v.setUint8(o + 11, MODELS.indexOf(e.m));
    v.setUint8(o + 12, e.seq);
    v.setUint8(o + 13, (e.state !== ALIVE ? 1 : 0) | (e.elite ? 2 : 0) | (e.boss ? 4 : 0) | (e.bomber ? 8 : 0) | (e.stun > 0 ? 16 : 0));
    v.setUint16(o + 14, Math.min(65535, Math.max(0, Math.round(e.f * 32))), true);
    v.setUint8(o + 16, Math.min(255, Math.round(e.flash * 255)));
    v.setUint8(o + 17, Math.min(255, Math.round(e.scale * 40)));
    v.setFloat32(o + 18, e.hp, true);
    v.setUint8(o + 22, Math.min(255, Math.round((e.sink || 0) * 2)));
    v.setUint8(o + 23, 0);
    o += ENEMY_BYTES;
  }
  for (const Q of others) {
    v.setUint8(o++, Q.idx);
    v.setInt16(o, qi(Q.o[0]), true); v.setInt16(o + 2, qi(Q.o[1]), true); v.setInt16(o + 4, qi(Q.o[2]), true); o += 6;
    v.setUint8(o++, ((((Q.yaw % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2)) / (Math.PI * 2) * 256) & 255);
    v.setUint8(o++, (Q.alive ? 1 : 0) | (Q.ducked ? 2 : 0) | (Q.moving ? 4 : 0));
    o++;
    o = writeTurrets(v, o, Q.turrets.slice(0, 3));
    o = writeRoombas(v, o, Q.roombas.slice(0, 3));
  }
  for (const s of shots) { v.setInt16(o, qi(s.p[0]), true); v.setInt16(o + 2, qi(s.p[1]), true); v.setInt16(o + 4, qi(s.p[2]), true); o += 6; }
  return buf.slice(0, o);
}
// Ziele der Gegner: alle lebenden Spieler
function worldTargets() {
  const L = [];
  if (!game.over && !game.dead) L.push({ local: true, o: player.o, eye: eyePos(), P: null });
  if (NET.role === 'host' && !game.over) for (const P of NET.players.values()) if (P.alive && P.inRound)
    L.push({ local: false, o: P.o, eye: [P.o[0], P.o[1], P.o[2] + (P.ducked ? -6 : MOVE.view)], P });
  return L;
}
function hurtTarget(T, dmg) { if (T.local) hurtPlayer(dmg); else netSend(T.P.ev, { t: 'hit', dmg: Math.round(dmg * 10) / 10 }); }
function netScale() { let n = 0; if (NET.role === 'host') for (const P of NET.players.values()) if (P.alive && P.inRound) n++; return 1 + 0.5 * n; }

// ---- Gast
async function netJoin(code) {
  code = String(code || '').replace(/\D/g, '').slice(0, 4);
  if (code.length !== 4) { netStatus('Bitte den 4-stelligen Raumcode eingeben.'); return; }
  netStatus('Verbinde mit Raum ' + code + ' …');
  await loadPeerLib(); await loadCtModel();
  netReset();
  NET.role = 'guest'; NET.code = code; NET.name = netName();
  const peer = NET.peer = new Peer(peerOpts());
  await new Promise((res, rej) => { peer.on('open', res); peer.on('error', rej); });
  peer.on('error', err => { netStatus(err.type === 'peer-unavailable' ? `Raum <b>${code}</b> nicht gefunden.` : 'Verbindungsfehler: ' + err.type); if (err.type === 'peer-unavailable') { netReset(); netLobby(); } });
  const id = NET_PREFIX + code;
  NET.ev = peer.connect(id, { label: 'ev', serialization: 'json', reliable: true });
  NET.st = peer.connect(id, { label: 'st', serialization: 'raw', reliable: false });
  NET.ev.on('open', () => netSend(NET.ev, { t: 'hello', name: NET.name, map: MAP.id }));
  NET.ev.on('data', netGuestMsg);
  NET.ev.on('close', netLost);
  NET.st.on('data', netGuestSnap);
}
function netLost() {
  if (NET.role !== 'guest') return;
  const wasRound = NET.inRound;
  netReset(); netLobby();
  toast('Verbindung zum Host verloren');
  if (wasRound) toMainMenu();
  netStatus('Verbindung zum Host verloren.');
}
function netGuestMsg(m) {
  if (m.t === 'map') {
    netStatus('Der Host spielt ' + m.map + ' – lade Map …');
    settings.map = m.map; saveSettings();
    location.href = `?map=${encodeURIComponent(m.map)}&join=${NET.code}&name=${encodeURIComponent(NET.name)}${QS.get('peer') ? '&peer=' + QS.get('peer') : ''}`;
  } else if (m.t === 'full') {
    const code = NET.code; NET.role = null; netReset(); netLobby();
    netStatus(`Raum <b>${code}</b> ist voll (max. ${m.max} Spieler).`);
  } else if (m.t === 'welcome') { NET.idx = m.idx; netLobby(); }
  else if (m.t === 'players') { NET.names = m.list; netLobby(); }
  else if (m.t === 'start') netGuestStart(m);
  else if (m.t === 'kill') netGuestKill(m);
  else if (m.t === 'hit') hurtPlayer(m.dmg);
  else if (m.t === 'toast') { toast(m.s); if (m.snd) sfx(m.snd, { vol: 0.85, important: true }); }
  else if (m.t === 'boss') NET.bossInfo = m.b;
  else if (m.t === 'bossdown') { NET.bossInfo = null; game.boss = null; }
  else if (m.t === 'boom') netShowBoom(m);
  else if (m.t === 'end') { if (!game.over) endRound(m.won && !game.dead); }
  else if (m.t === 'lobby') { if (NET.inRound || game.over) toMainMenu(true); }
}
function netGuestStart(m) {
  NET.inRound = true;
  audioInit();
  for (const id of ['start', 'dead', 'menu', 'shop']) $('#' + id).classList.remove('show');
  $('#hud').classList.add('show');
  restartRound();
  game.time = m.time || 0;
  NET.bossInfo = m.boss || null;
  playing = true;
  refreshMenu();
}
function netGuestKill(m) {
  const w = m.wid ? game.weapons.find(x => x.id === m.wid) : null;
  const fake = { x: m.x, y: m.y, z: m.z, node: navNodeAt(m.x, m.y, m.z, 30), xp: m.xp, elite: m.elite, boss: m.boss ? { name: m.boss } : null, scale: m.scale || 1, key: m.key };
  game.kills++; if (w) w.kills++;
  killfeed(fake, w, m.head);
  dropLoot(fake);
  sfx(m.head ? 'headshot' : 'die', { pos: [m.x, m.y, m.z + 40], vol: 0.5, gap: 0.11 });
}
// Schaden des Gastes: sofort sichtbar (Blitz, Ton), der Host entscheidet ueber den Kill
function guestDamage(e, dmg, head, w, quiet) {
  if (e.state !== ALIVE || e.predDead) return false;
  const real = Math.min(dmg, Math.max(0, e.hp));
  if (w) w.dmg += real;
  e.hp -= dmg; if (!quiet) e.flash = 1;
  if (!quiet) sfx(head ? 'headshot' : 'bhit_flesh', { pos: [e.x, e.y, e.z + 40], vol: head ? 0.55 : 0.4, gap: head ? 0.06 : 0.05 });
  const q = NET.dmgQ.get(e.id) || [0, 0, w ? w.id : null];
  q[0] += dmg; q[1] = q[1] || (head ? 1 : 0); if (w) q[2] = w.id;
  NET.dmgQ.set(e.id, q);
  const pd = NET.pend.get(e.id) || { d: 0, t: 0 }; pd.d += dmg; pd.t = game.time; NET.pend.set(e.id, pd);
  if (e.hp <= 0) e.predDead = true;
  return false;
}
function netGuestSnap(d) {
  if (d instanceof Blob) { d.arrayBuffer().then(netGuestSnap); return; }
  if (!NET.inRound) return;
  const v = new DataView(d);
  if (v.getUint8(0) !== 1) return;
  let o = 1;
  const time = v.getFloat32(o, true); o += 4;
  const bossHp = v.getFloat32(o, true); o += 4;
  const nE = v.getUint16(o, true); o += 2;
  const nP = v.getUint8(o++), nS = v.getUint8(o++);
  if (!game.over && Math.abs(time - game.time) > 0.25) game.time = time;
  const seen = new Set();
  let boss = null;
  for (let i = 0; i < nE; i++) {
    const id = v.getUint32(o, true), x = v.getInt16(o + 4, true) / 4, y = v.getInt16(o + 6, true) / 4, z = v.getInt16(o + 8, true) / 4;
    const yaw = v.getUint8(o + 10) / 256 * Math.PI * 2, mi = v.getUint8(o + 11), seq = v.getUint8(o + 12), fl = v.getUint8(o + 13);
    const f = v.getUint16(o + 14, true) / 32, flash = v.getUint8(o + 16) / 255, scale = v.getUint8(o + 17) / 40, hp = v.getFloat32(o + 18, true), sink = v.getUint8(o + 22) / 2;
    o += ENEMY_BYTES;
    const m = MODELS[mi]; if (!m) continue;
    let e = NET.mirrors.get(id);
    if (!e) {
      e = { id, m, key: m.key, x, y, z, tx: x, ty: y, tz: z, yaw, tyaw: yaw, node: -1, hp, maxHp: hp, scale, elite: false, boss: null, bomber: false,
        tint: [1, 1, 1], state: ALIVE, t: 0, seq, f, flash: 0, sink: 0, light: [1, 1, 1], stun: 0, slow: 1, miss: 0, lightT: 0 };
      NET.mirrors.set(id, e);
    }
    e.tx = x; e.ty = y; e.tz = z; e.tyaw = yaw; e.scale = scale; e.sink = sink; e.miss = 0;
    if (e.seq !== seq || Math.abs(e.f - f) > 4) { e.seq = seq; e.f = f; }
    e.flash = Math.max(e.flash, flash);
    const dying = !!(fl & 1);
    if (dying && e.state === ALIVE) { e.state = DYING; e.t = 0; }
    e.elite = !!(fl & 2); e.bomber = !!(fl & 8);
    e.tint = fl & 4 ? [1.15, 1.0, 0.95] : e.elite ? [1.5, 0.75, 0.65] : [1, 1, 1];
    if (!dying) {
      const pd = NET.pend.get(id), pend = pd && game.time - pd.t < 0.4 ? pd.d : 0;
      e.hp = hp - pend; e.predDead = e.hp <= 0;
      e.maxHp = Math.max(e.maxHp, hp);
    }
    if (fl & 4) {
      const info = NET.bossInfo || { name: 'Boss', kind: 'riese', hp };
      e.boss = { name: info.name, kind: info.kind }; e.maxHp = info.hp || e.maxHp;
      if (!dying) boss = e;
    }
    seen.add(id);
  }
  for (const [id, e] of NET.mirrors) if (!seen.has(id) && ++e.miss > 2) NET.mirrors.delete(id);
  enemies = [...NET.mirrors.values()];
  game.boss = boss && bossHp > 0 ? boss : null;
  // andere Spieler
  const seenP = new Set();
  NET.rTurrets = []; NET.rRoombas = [];
  for (let i = 0; i < nP; i++) {
    const idx = v.getUint8(o++);
    const px = v.getInt16(o, true) / 4, py = v.getInt16(o + 2, true) / 4, pz = v.getInt16(o + 4, true) / 4; o += 6;
    const yaw = v.getUint8(o++) / 256 * Math.PI * 2, fl = v.getUint8(o++); o++;
    let T, R;
    [T, o] = readTurrets(v, o); [R, o] = readRoombas(v, o);
    netAvatar(idx, [px, py, pz], yaw, fl, NET.names[idx]);
    NET.rTurrets.push(...T); NET.rRoombas.push(...R);
    seenP.add(idx);
  }
  for (const idx of [...NET.avatars.keys()]) if (!seenP.has(idx)) netDropAvatar(idx);
  eShots = [];
  for (let i = 0; i < nS; i++) { eShots.push({ p: [v.getInt16(o, true) / 4, v.getInt16(o + 2, true) / 4, v.getInt16(o + 4, true) / 4], v: [0, 0, 0], t: 0, dmg: 0 }); o += 6; }
}
// Spiegel-Gegner zwischen den Snapshots weich bewegen und animieren
function netGuestEnemies(dt) {
  const k = Math.min(1, dt * 12);
  for (const e of enemies) {
    e.flash = Math.max(0, e.flash - dt * 7);
    e.x += (e.tx - e.x) * k; e.y += (e.ty - e.y) * k; e.z += (e.tz - e.z) * k;
    const dy = ((e.tyaw - e.yaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI; e.yaw += dy * k;
    e.f += dt * e.m.seqs[e.seq].fps;
    if (e.state !== ALIVE) e.t += dt;
    if (e.stun > 0) e.stun -= dt;
    e.lightT -= dt;
    if (e.lightT <= 0) {
      e.lightT = 0.3 + Math.random() * 0.2;
      const n = navNodeAt(e.x, e.y, e.z, 30);
      if (n >= 0) { e.node = n; const L = NAV.light; e.light = [L[n * 3] * e.tint[0], L[n * 3 + 1] * e.tint[1], L[n * 3 + 2] * e.tint[2]]; }
    }
  }
}

// ---- Andere Spieler als GIGN-Figuren
function netAvatar(idx, o, yaw, fl, name) {
  if (!CT_MODEL) return;
  let a = NET.avatars.get(idx);
  if (!a) {
    a = { idx, m: CT_MODEL, key: 'gign', x: o[0], y: o[1], z: o[2] - 36, tx: o[0], ty: o[1], tz: o[2] - 36, yaw, tyaw: yaw, seq: CT_MODEL.seq.idle1, f: 0,
      scale: 1, light: [1, 1, 1], flash: 0, sink: 0, state: ALIVE, tint: [1, 1, 1], alive: true, name: name || 'Spieler', lightT: 0 };
    NET.avatars.set(idx, a);
  }
  a.tx = o[0]; a.ty = o[1]; a.tz = o[2] - 36 - (fl & 2 ? 10 : 0); a.tyaw = yaw; a.name = name || a.name;
  const alive = !!(fl & 1);
  if (!alive && a.alive) { a.seq = CT_MODEL.seq[DEATHS[0]]; a.f = 0; }
  if (alive && !a.alive) a.seq = CT_MODEL.seq.idle1;
  a.alive = alive;
  if (alive) { const want = fl & 4 ? CT_MODEL.seq.run : CT_MODEL.seq.idle1; if (a.seq !== want) { a.seq = want; a.f = 0; } }
  NET.avatarList = [...NET.avatars.values()];
}
function netDropAvatar(idx) {
  NET.avatars.delete(idx);
  const t = NET.tags.get(idx); if (t) { t.remove(); NET.tags.delete(idx); }
  NET.avatarList = [...NET.avatars.values()];
}
function netHostAvatars() {
  const seen = new Set();
  NET.rTurrets = []; NET.rRoombas = [];
  for (const P of NET.players.values()) {
    if (!P.inRound) continue;
    netAvatar(P.idx, P.o, P.yaw, (P.alive ? 1 : 0) | (P.ducked ? 2 : 0) | (P.moving ? 4 : 0), P.name);
    NET.rTurrets.push(...P.turrets); NET.rRoombas.push(...P.roombas);
    seen.add(P.idx);
  }
  for (const idx of [...NET.avatars.keys()]) if (!seen.has(idx)) netDropAvatar(idx);
}
function netAnimateAvatars(dt) {
  const k = Math.min(1, dt * 12);
  for (const a of NET.avatarList) {
    a.x += (a.tx - a.x) * k; a.y += (a.ty - a.y) * k; a.z += (a.tz - a.z) * k;
    const dy = ((a.tyaw - a.yaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI; a.yaw += dy * k;
    a.f += dt * a.m.seqs[a.seq].fps;
    a.lightT -= dt;
    if (a.lightT <= 0) { a.lightT = 0.4; const n = navNodeAt(a.x, a.y, a.z, 30); if (n >= 0) a.light = [NAV.light[n * 3], NAV.light[n * 3 + 1], NAV.light[n * 3 + 2]]; }
  }
}
// Licht fuer fremde Tuerme/Roombas (Position aendert sich selten)
function netLight(x, y, z) {
  const key = ((x / 32) | 0) + ',' + ((y / 32) | 0) + ',' + ((z / 32) | 0);
  let L = NET.lightCache.get(key);
  if (!L) { L = propLight(x, y, z); NET.lightCache.set(key, L); }
  return L;
}
function netRemoteTurrets() { return NET.rTurrets.map(T => ({ x: T.x, y: T.y, z: T.z, yaw: T.yaw, aim: T.aim, t: 9, fireAnim: 0, light: netLight(T.x, T.y, T.z) })); }
function netRemoteRoombas() { return NET.rRoombas.map(R => ({ x: R.x, y: R.y, z: R.z, yaw: R.yaw, light: netLight(R.x, R.y, R.z) })); }
// Namen ueber den Koepfen
function netTags(VP) {
  const W = canvas.clientWidth, H = canvas.clientHeight;
  for (const a of NET.avatarList) {
    let el = NET.tags.get(a.idx);
    if (!el) { el = document.createElement('div'); el.className = 'ntag'; $('#hud').appendChild(el); NET.tags.set(a.idx, el); }
    const x = a.x, y = a.y, z = a.z + 84;
    const cx = VP[0] * x + VP[4] * y + VP[8] * z + VP[12], cy = VP[1] * x + VP[5] * y + VP[9] * z + VP[13], cw = VP[3] * x + VP[7] * y + VP[11] * z + VP[15];
    const dist = Math.hypot(x - player.o[0], y - player.o[1]);
    if (cw <= 1 || dist > 2400 || !playing) { el.style.display = 'none'; continue; }
    el.style.display = '';
    if (el.textContent !== a.name + (a.alive ? '' : ' ✝')) el.textContent = a.name + (a.alive ? '' : ' ✝');
    el.style.transform = `translate(${((cx / cw) * 0.5 + 0.5) * W}px, ${(0.5 - (cy / cw) * 0.5) * H}px) translate(-50%, -100%)`;
  }
}
// Explosionen der anderen sichtbar machen (ohne Schaden)
function netShowBoom(m) {
  fx.push({ type: 'boom', p: m.p, r: m.r, t: 0, life: 0.7 });
  sfx(m.snd || 'explode', { pos: m.p, vol: 0.8, gap: 0.06, far: 3500 });
  const dp = Math.hypot(player.o[0] - m.p[0], player.o[1] - m.p[1]);
  game.shake = Math.max(game.shake, Math.max(0, 1 - dp / 900) * 0.6);
}
function netBoom(p, r, snd) {
  if (NET.role === 'host') netSendAll({ t: 'boom', p, r, snd });
  else if (NET.role === 'guest') netSend(NET.ev, { t: 'boom', p, r, snd });
}

// ---- pro Frame
function netTick(dt) {
  if (NET.role === 'host') {
    netHostAvatars();
    netAnimateAvatars(dt);
    NET.snapT -= dt;
    if (NET.inRound && NET.snapT <= 0) {
      NET.snapT = 1 / 15;
      for (const P of NET.players.values()) if (P.st && P.st.open && P.inRound) try { P.st.send(netHostSnapshot(P)); } catch (e) { /* voll */ }
    }
    // alle tot -> Runde verloren
    if (NET.inRound && !game.over && game.dead && ![...NET.players.values()].some(P => P.alive && P.inRound)) endRound(false);
  } else if (NET.role === 'guest') {
    netAnimateAvatars(dt);
    NET.stateT -= dt;
    if (NET.stateT <= 0) {
      NET.stateT = 1 / 20;
      if (NET.st && NET.st.open) {
        const buf = new ArrayBuffer(1 + 12 + 4 + 1 + 3 * 8 + 1 + 3 * 7), v = new DataView(buf);
        let o = 0;
        v.setUint8(o++, 2);
        v.setFloat32(o, player.o[0], true); v.setFloat32(o + 4, player.o[1], true); v.setFloat32(o + 8, player.o[2], true); o += 12;
        v.setUint8(o++, ((((player.yaw % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2)) / (Math.PI * 2) * 256) & 255);
        v.setInt8(o++, Math.round(Math.max(-1.27, Math.min(1.27, player.pitch)) * 100));
        v.setUint8(o++, (!game.dead && !game.over ? 1 : 0) | (player.ducked ? 2 : 0) | (Math.hypot(player.v[0], player.v[1]) > 40 ? 4 : 0) | (NET.inRound ? 8 : 0));
        v.setUint8(o++, Math.max(0, Math.min(255, Math.round(game.hp))));
        o = writeTurrets(v, o, turrets.slice(0, 3));
        o = writeRoombas(v, o, roombas.slice(0, 3));
        try { NET.st.send(buf.slice(0, o)); } catch (e) { /* voll */ }
      }
      if (NET.dmgQ.size) { netSend(NET.ev, { t: 'dmg', d: [...NET.dmgQ].map(([id, q]) => [id, Math.round(q[0] * 10) / 10, q[1], q[2]]) }); NET.dmgQ.clear(); }
      const st = [];
      for (const e of enemies) if (e.stun > (e.stunSent || 0) + 0.05) { st.push([e.id, Math.round(e.stun * 10) / 10]); e.stunSent = e.stun; }
      for (const e of enemies) if (e.stun <= 0) e.stunSent = 0;
      if (st.length) netSend(NET.ev, { t: 'stun', l: st });
      for (const [id, pd] of NET.pend) if (game.time - pd.t > 1) NET.pend.delete(id);
    }
  }
}
function netLocalDeath() {
  game.dead = true; game.deathT = 0;
  input.fwd = input.side = 0;
  toast('Gefallen – du schaust zu, bis die Runde endet');
  sfx('die', { vol: 0.8, important: true });
  if (NET.role === 'guest') netSend(NET.ev, { t: 'dead' });
}
// Lobby-Knoepfe
$('#mpToggle').addEventListener('click', () => { const b = $('#mpBox'); b.style.display = b.style.display === 'none' ? '' : 'none'; });
$('#mpName').value = settings.mpName || '';
$('#mpHost').addEventListener('click', () => netHost().catch(err => { netReset(); netLobby(); netStatus('Raum konnte nicht erstellt werden: ' + (err.type || err.message)); }));
$('#mpJoin').addEventListener('click', () => netJoin($('#mpCode').value).catch(err => { netReset(); netLobby(); netStatus('Beitreten fehlgeschlagen: ' + (err.type || err.message)); }));
$('#mpLeave').addEventListener('click', () => { if (NET.role === 'guest') netSend(NET.ev, { t: 'bye' }); if (NET.role === 'host') netSendAll({ t: 'lobby' }); netReset(); netLobby(); netStatus('Raum verlassen. Einzelspieler.'); });
