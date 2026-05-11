// Remove near-duplicates: same stem + same answer, different (but similar) options
// Keep first occurrence per stem, remove subsequent from later files
const fs = require('fs');
const path = require('path');

const dataDir = path.join(__dirname, '..', 'data');
const files = fs.readdirSync(dataDir)
  .filter(f => /^s[12]-qb-\d+\.json$/.test(f))
  .sort();

const seenStemAns = new Map(); // "stem|||answer" -> {file}
const removals = {};
for (const f of files) removals[f] = [];

for (const f of files) {
  const fp = path.join(dataDir, f);
  const qs = JSON.parse(fs.readFileSync(fp, 'utf8'));
  for (let i = 0; i < qs.length; i++) {
    const q = qs[i];
    const key = q.题干 + '|||' + q.答案;
    if (seenStemAns.has(key)) {
      removals[f].push(i);
      console.log(`REMOVE: ${f}#${i+1} (${q.id}) — dup of ${seenStemAns.get(key)}`);
    } else {
      seenStemAns.set(key, `${f}#${i+1} (${q.id})`);
    }
  }
}

let totalRemoved = 0;
for (const f of files) {
  const rm = removals[f];
  if (rm.length === 0) continue;
  const fp = path.join(dataDir, f);
  const qs = JSON.parse(fs.readFileSync(fp, 'utf8'));
  const rmSet = new Set(rm);
  const filtered = qs.filter((_, i) => !rmSet.has(i));
  filtered.forEach((q, idx) => { q.题号 = idx + 1; });
  fs.writeFileSync(fp, JSON.stringify(filtered, null, 2), 'utf8');
  totalRemoved += rm.length;
  console.log(`  ${f}: -${rm.length} (${qs.length}→${filtered.length})`);
}
console.log(`\nTotal near-duplicates removed: ${totalRemoved}`);
