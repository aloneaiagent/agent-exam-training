#!/usr/bin/env python3
"""
解析 ycjjr.net 剩余 6 篇文章并合并进 all_questions.json.
"""

import re, json, html, os, sys
from urllib.request import urlopen, Request
from collections import OrderedDict

BASE_URL = "https://www.ycjjr.net/article/"
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
H = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

ARTICLES = [
    {"id": 108319, "科目": "科目一", "来源": "政策法规与经纪实务模拟题一"},
    {"id": 108320, "科目": "科目一", "来源": "政策法规与经纪实务模拟题二"},
    {"id": 108324, "科目": "科目二", "来源": "舞台艺术基础知识模拟题一"},
    {"id": 108325, "科目": "科目二", "来源": "舞台艺术基础知识模拟题二"},
    {"id": 108327, "科目": "科目一", "来源": "政策法规与经纪实务模拟题三"},
    {"id": 108348, "科目": "科目二", "来源": "舞台艺术基础知识考试练习题"},
]

NAV = ['首页','新版在线','考试信息','常见问题','导航','当前位置','admin','℃','-->',
       '苏ICP','联系我们','版权所有','关于我们','上一篇','下一篇','相关文章','搜索',
       '考试题库最新','考试题库热点','相关演出经纪人考试','|','苏公网安备',
       '试试用"←"','演出经纪人考试题库（']

def fetch(aid):
    url = f"{BASE_URL}{aid}.html"
    req = Request(url, headers=H)
    with urlopen(req, timeout=15) as resp:
        raw = resp.read()
        enc = resp.headers.get_content_charset() or 'utf-8'
        return raw.decode(enc, errors='replace')

def clean(raw):
    t = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL|re.IGNORECASE)
    t = re.sub(r'<style[^>]*>.*?</style>', '', t, flags=re.DOTALL|re.IGNORECASE)
    t = re.sub(r'<!--.*?-->', '', t, flags=re.DOTALL)
    # Block-level tags → newline; inline tags → just strip
    t = re.sub(r'<(?:br\s*/?|/p|/div|/tr|/td|/li|/h[1-6]|/dl|/dd|/dt)>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'[\xa0\u3000]', ' ', t)
    t = re.sub(r'&nbsp;', ' ', t)
    return t

def nav_filter(lines):
    out = []
    for l in lines:
        if any(w in l for w in NAV if w): continue
        if l.startswith('考试题库') and len(l) <= 10: continue
        if l in ('单选题','【单选题】','练习题及答案','练习题','（多选题）','多选题'): continue
        if l.startswith('演出经纪人'): continue
        out.append(l)
    return out

# ─── Helpers ───
def ans_in_paren(s):
    m = re.search(r'[（(]\s*([A-Da-dEF]{1,8})\s*[)）]', s)
    if m:
        a = m.group(1).upper().strip()
        if re.match(r'^[A-DEF]{1,8}$', a): return a
    return None

def ans_in_ref(s):
    m = re.search(r'(?:参考|参考答案)[：:]\s*([A-Da-dEF对错]+)', s)
    if m:
        raw = m.group(1).upper().strip()
        if raw in ('对','正确'): return 'A'
        if raw in ('错','错误'): return 'B'
        if re.match(r'^[A-DEF]{1,8}$', raw): return raw
    return None

def clean_qtext(s):
    s = re.sub(r'[（(]\s*[A-Da-d]+\s*[)）]', '', s).strip()
    s = re.sub(r'\(\s*\)', '', s).strip()
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def save_q(qs, seen, q_text, opts, ans):
    t = clean_qtext(q_text)
    if len(t) < 3 or not ans or not opts: return
    # Normalize judge
    if len(opts) == 2 and list(opts.keys()) == ['A','B'] and opts['A'] in ('正确','对') and opts['B'] in ('错误','错'):
        pass  # it's fine
    k = (t[:60], ans)
    if k in seen: return
    seen.add(k)
    if len(ans) >= 2: ans = ''.join(sorted(ans))
    qs.append({"题号": len(qs)+1, "题干": t, "选项": dict(opts), "答案": ans})

def split_inline_opts(line):
    """Split 'A 柴可夫斯基    B 福金    C 斯特拉文斯    D 丹钦科' into ordered dict"""
    opts = OrderedDict()
    # Multiple letters followed by space/tab → separator
    parts = re.split(r'(?=[A-Da-d]\s{2,})', line)
    if len(parts) < 2:
        # Try another pattern: single-letter + space or dot
        parts = re.findall(r'([A-Da-d])\s*[.、．\s]\s*([^A-D]+?)(?=[A-Da-d]\s*[.、．\s]|$)', line)
        if parts:
            opts = OrderedDict()
            for k, v in parts:
                opts[k.upper()] = v.strip()
            return opts
        return None
    for p in parts:
        m = re.match(r'\s*([A-Da-d])\s+(.+)', p)
        if m:
            opts[m.group(1).upper()] = m.group(2).strip()
    return opts if opts else None

# ════════════════════════════════════
# Parser 1: inline answer (108319, 108327)
# ════════════════════════════════════

def parse_inline(text):
    lines = nav_filter([l.strip() for l in text.split('\n') if l.strip()])
    if not lines: return []

    qs, seen = [], set()
    i = 0
    cur_q = None
    cur_opts = OrderedDict()
    cur_ans = None
    found_ans = False

    while i < len(lines):
        l = lines[i]

        # Skip section markers
        if re.match(r'^[【\[]?\s*(?:单选题|多选题|判断题)', l):
            i += 1; continue

        qm = re.match(r'^(\d+)\s*[、.．]\s*(.*)', l)
        if qm:
            if cur_q is not None and cur_ans and cur_opts:
                save_q(qs, seen, cur_q, cur_opts, cur_ans)
            cur_q = qm.group(2)
            cur_opts = OrderedDict()
            cur_ans = ans_in_paren(l)
            found_ans = bool(cur_ans)
            if cur_ans:
                cur_q = re.sub(r'[（(]\s*[A-Da-d]+\s*[)）]', '', cur_q).strip()
            i += 1; continue

        # Check if this is an inline-options line: starts with A. and contains more A-D markers
        # e.g. "A.10日          B.15日          C.20日          D.30日"
        # Try inline first (requires >=2 options to avoid single A.xxx matches)
        inline_opts = split_inline_opts(l)
        if inline_opts and len(inline_opts) >= 2:
            cur_opts = inline_opts
            i += 1; continue

        # Standard option (single-letter prefix like A., B., C., D.)
        om = re.match(r'^([A-Da-d])\s*[.、．]', l)
        if om and cur_q is not None:
            key = om.group(1).upper()
            val = re.sub(r'^[A-Da-d]\s*[.、．]\s*', '', l).strip()
            cur_opts[key] = val
            i += 1; continue

        # Answer in parens (separate line after options)
        if not found_ans and cur_q is not None:
            a = ans_in_paren(l)
            if a:
                cur_ans = a; found_ans = True
                i += 1; continue

        i += 1

    if cur_q is not None and cur_ans and cur_opts:
        save_q(qs, seen, cur_q, cur_opts, cur_ans)
    return qs

# ════════════════════════════════════
# Parser 2: 参考答案：X (108324, 108348)
# ════════════════════════════════════

def parse_ref_answer(text):
    lines = nav_filter([l.strip() for l in text.split('\n') if l.strip()])
    if not lines: return []

    blocks = []
    cur = None
    for l in lines:
        qm = re.match(r'^(\d+)\s*[、.．]', l)
        ra = bool(re.search(r'(?:参考|参考答案)[：:]', l))
        if qm:
            if cur is not None: blocks.append(cur)
            cur = {'qnum': int(qm.group(1)), 'lines': [l]}
        elif ra and cur is not None:
            cur['lines'].append(l)
            blocks.append(cur)
            cur = None
        elif cur is not None:
            cur['lines'].append(l)
    if cur is not None: blocks.append(cur)

    qs, seen = [], set()
    for blk in blocks:
        opts = OrderedDict()
        ans = None
        q_text = None
        for li, l in enumerate(blk['lines']):
            if li == 0:
                m = re.match(r'^\d+\s*[、.．]\s*(.*)', l)
                if m:
                    q_text = m.group(1).strip()
                    a = ans_in_paren(l)
                    if a:
                        ans = a
                        q_text = re.sub(r'[（(]\s*[A-Da-d]+\s*[)）]', '', q_text).strip()
                continue
            ra = ans_in_ref(l)
            if ra:
                ans = ra; continue
            om = re.match(r'^([A-Da-d])\s*[.、．]', l)
            if om:
                opts[om.group(1).upper()] = re.sub(r'^[A-Da-d]\s*[.、．]\s*', '', l).strip()
            else:
                # Check for inline options: "A xxx B xxx C xxx D xxx"
                inline_opts = split_inline_opts(l)
                if inline_opts:
                    opts = inline_opts
        if q_text and ans is not None and len(opts) >= 2:
            save_q(qs, seen, q_text, opts, ans)
    return qs

# ════════════════════════════════════
# Parser 3: 108320 — answers at end
# ════════════════════════════════════

def parse_108320(text):
    lines = nav_filter([l.strip() for l in text.split('\n') if l.strip()])
    if not lines: return []

    # Find answer section
    ans_idx = next((i for i, l in enumerate(lines) if '单选答案' in l), len(lines))
    q_raw = lines[:ans_idx]
    ans_raw_text = '\n'.join(lines[ans_idx:])

    # ── Build answer map ──
    amap = {}

    # Single choice: "1—5 BDBCb  6—10 DCABB"
    for m in re.finditer(r'(\d+)[—\-～~到到](\d+)\s+([A-Da-d\s]+?)(?=\d+[—\-～~到到]|$|多选|判断)', ans_raw_text):
        s, e = int(m.group(1)), int(m.group(2))
        clean = ''.join(c for c in m.group(3).upper().strip() if c in 'ABCD ')
        parts = clean.split()
        if not parts: parts = [c for c in clean if c in 'ABCD']
        for j, a in enumerate(parts):
            if s + j <= e: amap[s + j] = a

    # Multi-choice: "1.acd  2.abd"
    for m in re.finditer(r'(\d+)\.\s*([A-Da-d]+)', ans_raw_text):
        amap[int(m.group(1))] = ''.join(sorted(m.group(2).upper()))

    # Judge: "1—5 对错错错错"
    for m in re.finditer(r'(\d+)[—\-～~到到](\d+)\s+([对错]+)', ans_raw_text):
        s, e = int(m.group(1)), int(m.group(2))
        for j, ch in enumerate(m.group(3)):
            amap[s + j] = 'A' if ch == '对' else 'B'

    # ── Merge question lines into blocks ──
    merged = []
    for l in q_raw:
        if re.match(r'^\d+[、.．]', l):
            merged.append(l)
        elif re.match(r'^[A-Da-d]\s*[、.．\s]', l):
            merged.append(l)
        else:
            if merged: merged[-1] += ' ' + l

    qs, seen = [], set()
    cur, cur_qtext, cur_opts = None, '', OrderedDict()
    section = '单选题'

    for blk in merged:
        if '单选题' in blk: section = '单选题'; continue
        if '多选题' in blk: section = '多选题'; continue
        if '判断题' in blk: section = '判断题'; continue

        qm = re.match(r'^(\d+)[、.．]\s*(.*)', blk)
        if qm:
            if cur is not None and cur_opts:
                a = amap.get(cur, '')
                if a: save_q(qs, seen, cur_qtext, cur_opts, a)
            cur = int(qm.group(1))
            cur_qtext = qm.group(2).strip()
            cur_qtext = re.sub(r'[（(]\s*[)）]\s*\d*页?', '', cur_qtext).strip()
            cur_qtext = re.sub(r'\s+\d+页', '', cur_qtext).strip()
            cur_qtext = re.sub(r'[（(]\s*[)）]', '', cur_qtext).strip()
            cur_opts = OrderedDict()
            continue

        om = re.match(r'^([A-Da-d])\s*[、.．\s]', blk)
        if om and cur is not None:
            key = om.group(1).upper()
            val = re.sub(r'^[A-Da-d]\s*[、.．\s]+', '', blk).strip()
            cur_opts[key] = val
            continue

    if cur is not None and cur_opts:
        a = amap.get(cur, '')
        if a: save_q(qs, seen, cur_qtext, cur_opts, a)

    return qs

# ════════════════════════════════════
# Parser 4: 108325 — mixed inline + multi-line + judge
# ════════════════════════════════════

def parse_108325(text):
    lines = nav_filter([l.strip() for l in text.split('\n') if l.strip()])
    if not lines: return []

    # Pre-merge multi-line answer pattern:
    # "1．戏剧的功能包括（" + "ABCD" + "）功能。"
    merged = []
    i = 0
    while i < len(lines):
        l = lines[i]
        if '（' in l and '）' not in l and i + 2 < len(lines):
            n1, n2 = lines[i+1].strip(), lines[i+2].strip() if i+2 < len(lines) else ''
            if re.match(r'^[A-Da-dEF]{2,}$', n1) and ('）' in n2 or re.match(r'^[A-Da-dEF]{2,}$', n2)):
                letters = n1.upper()
                if '）' not in n2: letters += ''.join(c for c in n2.upper() if c in 'ABCDEF')
                letters = ''.join(sorted(set(letters) & set('ABCDEF')))
                l = l.replace('（', f'（{letters}）')
                if '）' not in l: l += '）'
                i += 3
                continue
        merged.append(l)
        i += 1

    qs, seen = [], set()
    i = 0
    cur_q = None
    cur_opts = OrderedDict()
    cur_ans = None
    found_ans = False

    while i < len(merged):
        l = merged[i]

        if '单选题' in l: i += 1; continue
        if '多选题' in l: i += 1; continue
        if '判断题' in l: i += 1; continue

        qm = re.match(r'^(\d+)\s*[、.．]\s*(.*)', l)
        if qm:
            if cur_q is not None and cur_ans and cur_opts:
                save_q(qs, seen, cur_q, cur_opts, cur_ans)
            elif cur_q is not None and cur_ans and not cur_opts:
                # Judge
                save_q(qs, seen, cur_q, {'A': '正确', 'B': '错误'}, cur_ans)

            cur_q = qm.group(2)
            cur_opts = OrderedDict()
            cur_ans = ans_in_paren(l)
            found_ans = bool(cur_ans)
            if cur_ans:
                cur_q = re.sub(r'[（(]\s*[A-Da-d]+\s*[)）]', '', cur_q).strip()
            i += 1; continue

        # Standalone ABCD (multi-answer)
        if not found_ans and re.match(r'^[A-Da-dEF]{2,}$', l.strip()):
            a = l.strip().upper()
            if all(c in 'ABCDEF' for c in a):
                cur_ans = ''.join(sorted(a)); found_ans = True
                i += 1; continue

        # Judge "A 正确 B 错误" pattern
        # Inline options check first (A.xxx B.xxx C.xxx D.xxx on one line)
        if cur_q is not None and len(cur_opts) == 0:
            inline_opts = split_inline_opts(l)
            if inline_opts and len(inline_opts) >= 2:
                cur_opts = inline_opts
                i += 1; continue

        judge_opts = split_judge_options(l)
        if judge_opts and cur_q is not None:
            cur_opts = judge_opts
            i += 1; continue

        # Standard option
        om = re.match(r'^([A-Da-d])\s*[.、．\s]', l)
        if om and cur_q is not None:
            # Don't capture if it's "A 正确 B 错误" pattern
            val = re.sub(r'^[A-Da-d]\s*[.、．\s]+', '', l).strip()
            if val in ('正确', '错误') and i+1 < len(merged) and re.match(r'^[A-Da-d]\s*[.、．\s]', merged[i+1]):
                # This is judge pattern
                judge = OrderedDict()
                judge['A'] = val
                i += 1
                next_l = merged[i]
                n_om = re.match(r'^([A-Da-d])\s*[.、．\s]', next_l)
                if n_om:
                    n_val = re.sub(r'^[A-Da-d]\s*[.、．\s]+', '', next_l).strip()
                    judge[n_om.group(1).upper()] = n_val
                cur_opts = judge
                i += 1; continue
            cur_opts[om.group(1).upper()] = val
            i += 1; continue

        # Answer in parens
        if not found_ans and cur_q is not None:
            a = ans_in_paren(l)
            if a: cur_ans = a; found_ans = True; i += 1; continue

        i += 1

    if cur_q is not None and cur_ans:
        if cur_opts: save_q(qs, seen, cur_q, cur_opts, cur_ans)
        else: save_q(qs, seen, cur_q, {'A': '正确', 'B': '错误'}, cur_ans)
    return qs

def split_judge_options(l):
    """Check if line is 'A 正确 B 错误' or 'A 正确 B 错' pattern"""
    m = re.match(r'^[A-D]\s+(正确|对)\s+[A-D]\s+(错误|错)', l)
    if m: return OrderedDict([('A', '正确'), ('B', '错误')])
    m = re.match(r'^[A-D]\s+(正确|对)\s{3,}[A-D]\s+(错误|错)', l)
    if m: return OrderedDict([('A', '正确'), ('B', '错误')])
    return None

# ════════════════════════════════════
# Main
# ════════════════════════════════════

def main():
    all_new = []

    for meta in ARTICLES:
        aid, source, subject = meta['id'], meta['来源'], meta['科目']
        print(f"📥 {aid} ({source})...", end=' '); sys.stdout.flush()

        try:
            raw = fetch(aid)
        except Exception as e:
            print(f"❌ {e}"); continue

        text = clean(raw)
        parser = {108319: parse_inline, 108320: parse_108320,
                  108324: parse_ref_answer, 108325: parse_108325,
                  108327: parse_inline, 108348: parse_ref_answer}
        questions = parser[aid](text)

        for q in questions:
            opts = q['选项']
            if len(opts) == 2 and list(opts.keys()) == ['A','B'] and opts['A'] == '正确' and opts['B'] == '错误':
                q['题型'] = '判断题'
            elif len(q['答案']) >= 2:
                q['题型'] = '多选题'
            else:
                q['题型'] = '单选题'
            if len(q['答案']) >= 2:
                q['答案'] = ''.join(sorted(q['答案']))
            q['id'] = f"q_{subject[:2]}_{aid}_{q['题号']:03d}"
            q['科目'] = subject
            q['来源'] = source
            q['类型'] = '模拟卷'

        all_new.extend(questions)
        fname = f"ycjjr-{aid}.json"
        with open(os.path.join(DATA_DIR, fname), 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(questions)}题")

    print(f"\n📊 共解析 {len(all_new)} 题")

    # ── Merge into all_questions.json ──
    all_path = os.path.join(DATA_DIR, 'all_questions.json')
    existing = []
    if os.path.exists(all_path):
        with open(all_path) as f: existing = json.load(f)
        print(f"📚 现有题库: {len(existing)} 题")

    existing = [e for e in existing if not isinstance(e, str)]
    existing_keys = set()
    for q in existing:
        existing_keys.add((q.get('题干','')[:60], q.get('答案','')))

    new_count = dup_count = 0
    max_qnum = max((q.get('题号',0) for q in existing), default=0)
    for q in all_new:
        k = (q['题干'][:60], q['答案'])
        if k not in existing_keys:
            existing_keys.add(k); max_qnum += 1; q['题号'] = max_qnum
            existing.append(q); new_count += 1
        else: dup_count += 1

    with open(all_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"✅ 新增 {new_count} 题, 跳过 {dup_count} 重复, 总量 {len(existing)} 题")

    # ── Rebuild index ──
    print("\n🔨 重建索引...")
    build = os.path.join(os.path.dirname(__file__), 'build_index.py')
    if os.path.exists(build):
        import subprocess
        r = subprocess.run(['python3', build], capture_output=True, text=True)
        for line in (r.stdout if r.returncode == 0 else r.stderr).split('\n'):
            print(f'  {line}')
    else:
        print('  ⚠️  build_index.py not found')

if __name__ == '__main__':
    main()
