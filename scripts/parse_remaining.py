#!/usr/bin/env python3
"""解析剩余文章（模拟卷、其他题库）"""

import re, json, html, os, sys
from urllib.request import urlopen, Request
from urllib.error import URLError
from collections import OrderedDict

BASE_URL = "https://www.ycjjr.net/article/"
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

REMAINING = [
    # 模拟卷（综合）
    {"id": 108448, "科目": "综合", "来源": "模拟试题（常考点）", "类型": "模拟卷", "file": "mock-01.json"},
    {"id": 108449, "科目": "综合", "来源": "模拟试题（常考点2）", "类型": "模拟卷", "file": "mock-02.json"},
    {"id": 108447, "科目": "综合", "来源": "模拟题", "类型": "模拟卷", "file": "mock-03.json"},
    # 精编版
    {"id": 108450, "科目": "综合", "来源": "精编版", "类型": "主题库", "file": "other-01.json"},
    # 科目一 额外题库
    {"id": 108451, "科目": "科目一", "来源": "思想政治与法律基础_题库一", "类型": "主题库", "file": "s1-qb-11.json"},
    {"id": 108452, "科目": "科目一", "来源": "思想政治与法律基础_题库二", "类型": "主题库", "file": "s1-qb-12.json"},
    {"id": 108453, "科目": "科目一", "来源": "思想政治与法律基础_题库三", "类型": "主题库", "file": "s1-qb-13.json"},
    # 科目二 额外题库
    {"id": 108454, "科目": "科目二", "来源": "演出市场政策与经纪实务_考试题库一", "类型": "主题库", "file": "s2-qb-11.json"},
    {"id": 108455, "科目": "科目二", "来源": "演出市场政策与经纪实务_考试题库二", "类型": "主题库", "file": "s2-qb-12.json"},
    {"id": 108456, "科目": "科目二", "来源": "演出市场政策与经纪实务_考试题库三", "类型": "主题库", "file": "s2-qb-13.json"},
]

def fetch(aid):
    url = f"{BASE_URL}{aid}.html"
    req = Request(url, headers=headers)
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

def extract_answer(text):
    m = re.search(r'【答案】\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper().strip()
    m = re.search(r'【参考答案】\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper().strip()
    m = re.search(r'[（(]\s*(?:参考)?答案\s*[：:]\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper().strip()
    m = re.search(r'(?:^|\s)(?:参考)?答案\s*[：:]\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper().strip()
    return ""

def line_has_answer(line):
    if re.search(r'【答案】|【参考答案】', line): return True
    if re.search(r'[（(]\s*(?:参考)?答案\s*[：:]\s*[A-D]', line): return True
    if re.search(r'(?:^|\s)(?:参考)?答案\s*[：:]\s*[A-Da-d]', line): return True
    return False

def parse_format_A(lines):
    """逐行解析：题号、题干、选项行、答案行"""
    questions = []
    i = 0
    current_q = None
    current_options = OrderedDict()
    current_ans = ""
    collecting = False
    seen = set()

    while i < len(lines):
        line = lines[i]
        if re.match(r'^(第[A-Z\d]+页|首页|上一页|下一页|末页|相关文章|考试题库|搜索)', line):
            i += 1; continue

        m = re.match(r'^(\d+)[、.．]', line)
        if m:
            qnum = int(m.group(1))
            if 1 <= qnum <= 200:
                if current_q is not None and current_ans and dict(current_options):
                    q_text = re.sub(r'^\d+[、.．]\s*', '', current_q).strip()
                    q_text = re.split(r'【答案】|【参考答案】', q_text)[0].strip()
                    if q_text and len(q_text) > 5:
                        dk = (q_text[:60], current_ans)
                        if dk not in seen:
                            seen.add(dk)
                            questions.append({"题号": len(questions)+1, "题干": q_text, "选项": dict(current_options), "答案": current_ans})
                current_q = line
                current_options = OrderedDict()
                current_ans = ""
                collecting = True
                i += 1; continue

        if collecting and current_q:
            om = re.match(r'^([A-Da-d])[.、．\s]', line)
            if om:
                k = om.group(1).upper()
                v = re.sub(r'^[A-Da-d][.、．\s]+', '', line).strip()
                v = re.split(r'【答案】|【参考答案】|答案[：:]|（参考答案', v)[0].strip()
                # 清理尾部 HTML 残留
                v = re.sub(r'\s*"\s*/?>.*$', '', v).strip()
                current_options[k] = v
                i += 1; continue

        if line_has_answer(line):
            ans = extract_answer(line)
            if ans: current_ans = ans
            i += 1; continue

        # 题干延续
        if current_q and not collecting:
            current_q += " " + line
        i += 1

    # last q
    if current_q and current_ans and dict(current_options):
        q_text = re.sub(r'^\d+[、.．]\s*', '', current_q).strip()
        q_text = re.split(r'【答案】|【参考答案】', q_text)[0].strip()
        if q_text and len(q_text) > 5:
            dk = (q_text[:60], current_ans)
            if dk not in seen:
                questions.append({"题号": len(questions)+1, "题干": q_text, "选项": dict(current_options), "答案": current_ans})

    return questions

def parse_format_B(text):
    """【题干X】格式"""
    questions = []
    segs = re.split(r'【题干(\d+)】', text)
    seen = set()
    for i in range(1, len(segs), 2):
        if i+1 >= len(segs): break
        qnum = int(segs[i])
        content = segs[i+1]
        ans = extract_answer(content)
        if not ans: continue
        content_clean = re.sub(r'【参考答案】\s*[A-Da-d]*', '', content).strip()

        # extract options
        options = OrderedDict()
        opts = re.findall(r'([A-Da-d])\s*[.、．]\s*([^A-Da-d]+?)(?=[A-Za-z][.、．]|【|$)', content_clean)
        if opts:
            question_text = re.split(r'[A-Da-d]\s*[.、．]', content_clean)[0].strip()
            for k, v in opts:
                options[k.upper()] = v.strip()
        else:
            question_text = content_clean

        dk = (question_text[:60], ans)
        if dk not in seen:
            seen.add(dk)
            questions.append({"题号": len(questions)+1, "题干": question_text, "选项": dict(options), "答案": ans})

    return questions

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    total_q = 0
    for meta in REMAINING:
        aid = meta["id"]
        print(f"📥 a{aid} ({meta['来源']})...", end=" ")
        try:
            raw = fetch(aid)
        except Exception as e:
            print(f"❌ {e}"); continue

        text = clean(raw)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # detect format
        has_tigan = bool(re.search(r'【题干\d+】', text))
        # Count 【答案】 markers
        ans_markers = len(re.findall(r'【答案】', raw))
        has_format_a_answers = ans_markers > 0 or bool(re.search(r'[（(]?\s*(?:参考)?答案\s*[：:]\s*[A-D]', text))

        if has_tigan:
            questions = parse_format_B(text)
            print(f"格式B → {len(questions)}题", end="")
        elif has_format_a_answers:
            questions = parse_format_A(lines)
            print(f"格式A → {len(questions)}题", end="")
        else:
            questions = []
            print("未检测到答案格式 → 0题", end="")

        # annotate
        for q in questions:
            q["id"] = f"q_{meta['科目'][:2]}_{aid}_{q['题号']:03d}"
            q["科目"] = meta["科目"]
            q["来源"] = meta["来源"]
            q["类型"] = meta["类型"]
            if len(q["答案"]) >= 2:
                q["答案"] = ''.join(sorted(q["答案"]))
            q["题型"] = "多选题" if len(q["答案"]) >= 2 else "单选题"

        if questions:
            fpath = os.path.join(DATA_DIR, meta["file"])
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            print(f" → {meta['file']}")
        else:
            print()

        total_q += len(questions)

    print(f"\n✅ 剩余文章解析完成！新增 {total_q} 题")

if __name__ == "__main__":
    main()
