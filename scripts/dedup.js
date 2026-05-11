// Deduplicate fully identical questions across topic files
// Keep first occurrence, remove subsequent duplicates
const fs = require('fs');
const path = require('path');

const dataDir = path.join(__dirname, '..', 'data');
const files = fs.readdirSync(dataDir)
  .filter(f => /^s[12]-qb-\d+\.json$/.test(f))
  .sort();

const seen = new Map(); // key -> {file, index}
const removals = [];   // per-file removal indices
for (const f of files) removals[f] = new Set();

// First pass: mark duplicates
for (const f of files) {
  const fp = path.join(dataDir, f);
  const qs = JSON.parse(fs.readFileSync(fp, 'utf8'));
  for (let i = 0; i < qs.length; i++) {
    const q = qs[i];
    const key = q.题干 + '|||' + JSON.stringify(q.选项 || {}) + '|||' + q.答案;
    if (seen.has(key)) {
      removals[f].add(i);
    } else {
      seen.set(key, {file: f, index: i, id: q.id});
    }
  }
}

// Second pass: write filtered files
let totalRemoved = 0;
const changes = [];
for (const f of files) {
  const fp = path.join(dataDir, f);
  const qs = JSON.parse(fs.readFileSync(fp, 'utf8'));
  const rm = removals[f];
  if (rm.size === 0) continue;
  const filtered = qs.filter((_, i) => !rm.has(i));
  // Re-number 题号
  filtered.forEach((q, idx) => { q.题号 = idx + 1; });
  fs.writeFileSync(fp, JSON.stringify(filtered, null, 2), 'utf8');
  totalRemoved += rm.size;
  changes.push(`${f}: -${rm.size} (${qs.length}→${filtered.length})`);
}

console.log(`去重完成。移除了 ${totalRemoved} 条完全重复题。`);
console.log('变更详情:');
changes.forEach(c => console.log('  ' + c));
