#!/usr/bin/env python3
"""解析 108451：无编号选择题 + 文字解析答案"""
import re, json, html, os
from urllib.request import urlopen, Request
from collections import OrderedDict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
headers = {'User-Agent': 'Mozilla/5.0'}

def fetch(aid):
    req = Request(f"https://www.ycjjr.net/article/{aid}.html", headers=headers)
    with urlopen(req, timeout=15) as resp:
        raw = resp.read()
        enc = resp.headers.get_content_charset() or 'utf-8'
        return raw.decode(enc, errors='replace')

def clean(text):
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)
    text = re.sub(r'\"\s*/?>', '', text)
    return text

raw = fetch(108451)
text = clean(raw)
lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 3]

# 找到第二个"一、选择题"作为内容起点
content_start = 0
count = 0
for i, l in enumerate(lines):
    if '一、选择题' in l:
        count += 1
        if count == 2:
            content_start = i + 1
            break

# 提取选择题内容（到第一个 ### 或 二、填空题 为止）
content_lines = []
for i in range(content_start, len(lines)):
    l = lines[i]
    if l.startswith('###') or '二、填空题' in l:
        break
    content_lines.append(l)

# 按组解析：每个选择题 = [题干, A行, B行, C行, D行]
groups = []
cur_q = ''
cur_opts = OrderedDict()
for l in content_lines:
    if l == '一、选择题':
        continue
    om = re.match(r'^([A-D])[.、．]\s*', l)
    if om:
        k = om.group(1)
        v = re.sub(r'^[A-D][.、．]\s*', '', l).strip()
        cur_opts[k] = v
        if k == 'D':
            if cur_q and cur_opts:
                groups.append((cur_q, dict(cur_opts)))
            cur_q = ''
            cur_opts = OrderedDict()
    else:
        # 新题干
        if cur_q and cur_opts:
            groups.append((cur_q, dict(cur_opts)))
            cur_q = ''
            cur_opts = OrderedDict()
        cur_q = l

# 提取答案解析
ans_lines = []
in_ans = False
for l in lines:
    if '答案及解析' in l:
        in_ans = True
        continue
    if in_ans:
        if '三、多选题' in l:
            break
        if '一、选择题' in l:
            continue
        if l.startswith('解析：') or l.startswith('解析:'):
            ans_lines.append(l[3:].strip())
        elif l.startswith('###'):
            break

# 将解析映射到选项字母
def match_answer(opts, ans_text):
    if not opts or not ans_text:
        return ''
    # 方法1：看答案文本是否明确包含选项文本
    best_k = ''
    best_len = 0
    for k, v in opts.items():
        v_clean = v.strip().rstrip('。，.')
        # 检查选项文本是否包含在答案中（且选项较长，避免误匹配短文本）
        if len(v_clean) >= 4 and v_clean in ans_text:
            if len(v_clean) > best_len:
                best_len = len(v_clean)
                best_k = k
    if best_k:
        return best_k
    # 方法2：看答案中是否包含选项的关键词
    for k, v in opts.items():
        # 提取关键词（去掉修饰词）
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', v_clean)
        for kw in keywords[:3]:
            if len(kw) >= 4 and kw in ans_text:
                return k
    return ''

questions = []
seen = set()
for (q_text, opts), ans_text in zip(groups, ans_lines):
    ans_letter = match_answer(opts, ans_text)
    if not ans_letter:
        continue
    dk = (q_text[:60], ans_letter)
    if dk in seen:
        continue
    seen.add(dk)
    questions.append({
        "题号": len(questions) + 1,
        "题干": q_text,
        "选项": opts,
        "答案": ans_letter,
        "解析": ans_text,
        "id": f"q_科一_108451_{len(questions)+1:03d}",
        "科目": "科目一",
        "来源": "思想政治与法律基础_题库一",
        "类型": "主题库",
        "题型": "单选题"
    })

print(f"108451 → {len(questions)} 题")
for q in questions:
    a = q['答案']
    opt = q['选项'].get(a, '')
    print(f"  Q{q['题号']}: {q['题干'][:50]}... → {a}. {opt[:40]}...")

os.makedirs(DATA_DIR, exist_ok=True)
with open(os.path.join(DATA_DIR, 's1-qb-11.json'), 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)
print(f"\n✅ 已保存 s1-qb-11.json")
