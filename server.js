#!/usr/bin/env node
// Lightweight local backend for 演出经纪人题库
// - File-based storage (local) or PostgreSQL (when DATABASE_URL is set)
// - Add/edit users in USERS below.

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, 'data');
const DB_PATH = path.join(DATA_DIR, 'progress.json');
const PORT = Number(process.env.PORT || 8080);

// ===================== Storage =====================
// Uses PostgreSQL when DATABASE_URL env var is set (Render), otherwise file-based.

let pgPool = null;
const usePostgres = !!process.env.DATABASE_URL;

if (usePostgres) {
  const { Pool } = require('pg');
  pgPool = new Pool({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
}

async function initDb() {
  if (!usePostgres) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    if (!fs.existsSync(DB_PATH)) {
      const users = {};
      for (const username of Object.keys(USERS)) users[username] = defaultProgress();
      fs.writeFileSync(DB_PATH, JSON.stringify({ users }, null, 2));
    }
    return;
  }
  // PostgreSQL: create table if not exists
  await pgPool.query(`
    CREATE TABLE IF NOT EXISTS progress (
      username TEXT PRIMARY KEY,
      records JSONB DEFAULT '{}',
      wrong JSONB DEFAULT '[]',
      stats JSONB DEFAULT '{"total":0,"correct":0}',
      generated_at TIMESTAMPTZ DEFAULT NOW()
    )
  `);
  // Ensure all USERS have a row
  for (const username of Object.keys(USERS)) {
    await pgPool.query(
      'INSERT INTO progress (username) VALUES ($1) ON CONFLICT (username) DO NOTHING',
      [username]
    );
  }
}

function defaultProgress() {
  return { records: {}, wrong: [], stats: { total: 0, correct: 0 } };
}

async function readDb() {
  if (!usePostgres) {
    initDb();
    try {
      const db = JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
      db.users ||= {};
      for (const username of Object.keys(USERS)) db.users[username] ||= defaultProgress();
      return db;
    } catch {
      return { users: Object.fromEntries(Object.keys(USERS).map(u => [u, defaultProgress()])) };
    }
  }
  // PostgreSQL
  const result = await pgPool.query('SELECT username, records, wrong, stats FROM progress');
  const users = {};
  for (const username of Object.keys(USERS)) users[username] = defaultProgress();
  for (const row of result.rows) {
    users[row.username] = {
      records: row.records || {},
      wrong: row.wrong || [],
      stats: row.stats || { total: 0, correct: 0 },
    };
  }
  return { users };
}

async function writeDb(db) {
  // PostgreSQL: only the users table is passed in
  if (!usePostgres) {
    const tmp = `${DB_PATH}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(db, null, 2));
    fs.renameSync(tmp, DB_PATH);
    return;
  }
  for (const [username, progress] of Object.entries(db.users || {})) {
    await pgPool.query(
      `UPDATE progress SET records = $1, wrong = $2, stats = $3, generated_at = NOW() WHERE username = $4`,
      [progress.records || {}, JSON.stringify(progress.wrong || []), progress.stats || { total: 0, correct: 0 }, username]
    );
  }
}

// ===================== Users =====================
const USERS = {
  wang: { password: 'wangwang', role: 'student' },
  fly: { password: 'wangwang', role: 'student' },
  guan: { password: 'wangwang', role: 'student' },
  li: { password: 'wangwang', role: 'admin' },
};

// ===================== Sessions =====================
const sessions = new Map(); // token -> { username, role, createdAt }

// ===================== Caches & Helpers =====================
let questionMetaCache = null;
function loadQuestionMeta() {
  if (questionMetaCache) return questionMetaCache;
  questionMetaCache = {};
  const allPath = path.join(DATA_DIR, 'all_questions.json');
  try {
    const arr = JSON.parse(fs.readFileSync(allPath, 'utf8'));
    for (const q of arr) questionMetaCache[q.id] = { type: q['题型'] || '', subject: q['科目'] || '' };
  } catch {}
  return questionMetaCache;
}

function rate(correct, total) { return total ? Math.round(correct / total * 100) : 0; }

function calcRate(records, filterFn) {
  let total = 0, correct = 0;
  const meta = loadQuestionMeta();
  for (const [qid, rec] of Object.entries(records || {})) {
    const q = meta[qid] || {};
    if (!filterFn(q, qid, rec)) continue;
    total++;
    if (rec && rec.correct) correct++;
  }
  return { total, correct, accuracy: rate(correct, total) };
}

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 2_000_000) { reject(new Error('body too large')); req.destroy(); }
    });
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); } catch (e) { reject(e); }
    });
  });
}

function auth(req) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  const session = sessions.get(token);
  return session ? { token, ...session } : null;
}

function contentType(file) {
  const ext = path.extname(file).toLowerCase();
  return {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml; charset=utf-8',
  }[ext] || 'application/octet-stream';
}

function safeStaticPath(urlPath) {
  const pathname = decodeURIComponent(urlPath.split('?')[0]);
  const rel = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const full = path.resolve(ROOT, rel);
  if (!full.startsWith(ROOT)) return null;
  return full;
}

function userSummary(username, progress) {
  const records = progress.records || {};
  const meta = loadQuestionMeta();
  // Only count records for questions that still exist
  const validRecords = Object.fromEntries(Object.entries(records).filter(([qid]) => meta[qid]));
  const answered = Object.keys(validRecords).length;
  const single = calcRate(validRecords, q => q.type === '单选题');
  const multi = calcRate(validRecords, q => q.type === '多选题');
  const judge = calcRate(validRecords, q => q.type === '判断题');
  const s1 = calcRate(validRecords, q => q.subject === '科目一');
  const s2 = calcRate(validRecords, q => q.subject === '科目二');
  return {
    username,
    lastLogin: (progress.stats && progress.stats.lastLogin) || null,
    answered,
    xp: Object.values(validRecords).reduce((sum, rec) => sum + (rec.correct ? 10 : 2), 0),
    achievements: (progress.game && progress.game.unlocked) ? Object.keys(progress.game.unlocked) : [],
    gameXp: (progress.game && progress.game.xp) || 0,
    singleAccuracy: single.accuracy, singleDone: single.total,
    multiAccuracy: multi.accuracy, multiDone: multi.total,
    judgeAccuracy: judge.accuracy, judgeDone: judge.total,
    subject1Accuracy: s1.accuracy, subject1Done: s1.total,
    subject2Accuracy: s2.accuracy, subject2Done: s2.total,
  };
}

// ===================== API Routes =====================
async function handleApi(req, res) {
  try {
    if (req.method === 'POST' && req.url === '/api/login') {
      const { username, password } = await readBody(req);
      const u = USERS[String(username || '').trim()];
      if (!u || u.password !== String(password || '')) return sendJson(res, 401, { error: '用户名或密码错误' });
      const token = crypto.randomBytes(24).toString('hex');
      sessions.set(token, { username: String(username).trim(), role: u.role, createdAt: Date.now() });
      const db = await readDb();
      const uname = String(username).trim();
      const userProgress = db.users[uname] || defaultProgress();
      userProgress.stats = userProgress.stats || { total: 0, correct: 0 };
      userProgress.stats.lastLogin = Date.now();
      db.users[uname] = userProgress;
      await writeDb(db);
      return sendJson(res, 200, { token, username: uname, role: u.role, progress: userProgress });
    }

    if (req.method === 'GET' && req.url === '/api/me') {
      const s = auth(req);
      if (!s) return sendJson(res, 401, { error: '未登录' });
      const db = await readDb();
      return sendJson(res, 200, { username: s.username, role: s.role, progress: db.users[s.username] || defaultProgress() });
    }

    if (req.method === 'POST' && req.url === '/api/progress') {
      const s = auth(req);
      if (!s) return sendJson(res, 401, { error: '未登录' });
      const { progress } = await readBody(req);
      const safeProgress = progress && typeof progress === 'object' ? progress : defaultProgress();
      safeProgress.records ||= {};
      safeProgress.wrong ||= [];
      safeProgress.stats ||= { total: 0, correct: 0 };
      const db = await readDb();
      db.users[s.username] = safeProgress;
      await writeDb(db);
      return sendJson(res, 200, { ok: true });
    }

    if (req.method === 'GET' && req.url === '/api/version') {
      return sendJson(res, 200, { version: '6.0.0', totalQuestions: 2091, subjects: { '科目一': 885, '科目二': 781, '综合': 425 } });
    }

    if (req.method === 'GET' && req.url === '/api/admin/stats') {
      const s = auth(req);
      if (!s) return sendJson(res, 401, { error: '未登录' });
      if (s.role !== 'admin') return sendJson(res, 403, { error: '无后台权限' });
      const db = await readDb();
      const users = Object.keys(USERS).map(username => userSummary(username, db.users[username] || defaultProgress()));
      return sendJson(res, 200, { users, generatedAt: Date.now() });
    }

    return sendJson(res, 404, { error: 'not found' });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'server error' });
  }
}

// ===================== Server =====================
const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) return handleApi(req, res);
  const file = safeStaticPath(req.url);
  if (!file || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('Not found');
  }
  res.writeHead(200, {
    'Content-Type': contentType(file),
    'Cache-Control': file.endsWith('.html') ? 'no-store' : 'no-cache',
  });
  fs.createReadStream(file).pipe(res);
});

// ===================== Start =====================
(async () => {
  await initDb();
  server.listen(PORT, '0.0.0.0', () => {
    console.log(`题库系统已启动：http://localhost:${PORT}`);
    console.log(`存储模式：${usePostgres ? 'PostgreSQL' : '文件(本地)'}`);
    if (!usePostgres) console.log(`后台账号：li / wangwang`);
  });
})();
