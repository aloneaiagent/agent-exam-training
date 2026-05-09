#!/usr/bin/env python3
"""修复解析 108453 和 108451"""
import re, json, html, os, sys
from urllib.request import urlopen, Request
from collections import OrderedDict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
headers = {'User-Agent': 'Mozilla/5.0'}

def fetch(aid):
    url = f"https://www.ycjjr.net/article/{aid}.html"
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

def extract_ans(text):
    m = re.search(r'【答案】\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper()
    m = re.search(r'【参考答案】\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper()
    m = re.search(r'参考答案[：:]\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper()
    m = re.search(r'(?:^|\s)(?:参考)?答案[：:]\s*([A-Da-d]+)', text)
    if m: return m.group(1).upper()
    return ''

def parse_108453():
    """[单选题]1.xxx 格式"""
    raw = fetch(108453)
    text = clean(raw)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 3]
    
    # 找出实际内容区（跳过元数据重复）
    qs = []
    i = 0
    current_q = None
    current_ans = ''
    current_opts = OrderedDict()
    collecting = False
    seen = set()
    
    while i < len(lines):
        line = lines[i]
        # 匹配 [单选题]1.xxx 或 [单选题]1、xxx
        m = re.match(r'^\[(?:单选|多选|判断)题\]\s*(\d+)[.．、]?\s*', line)
        if m:
            qnum = int(m.group(1))
            if 1 <= qnum <= 200:
                # finalize previous
                if current_q and current_ans and current_opts:
                    q_text = re.sub(r'^\[(?:单选|多选|判断)题\]\s*\d+[.．、]?\s*', '', current_q).strip()
                    if q_text and len(q_text) > 5:
                        dk = (q_text[:60], current_ans)
                        if dk not in seen:
                            seen.add(dk)
                            qs.append({"题号": len(qs)+1, "题干": q_text, "选项": dict(current_opts), "答案": current_ans})
                
                current_q = line
                current_opts = OrderedDict()
                current_ans = ''
                collecting = True
                i += 1
                continue
        
        if collecting and current_q:
            om = re.match(r'^([A-Da-d])[.、．\s]', line)
            if om:
                k = om.group(1).upper()
                v = re.sub(r'^[A-Da-d][.、．\s]+', '', line).strip()
                v = re.split(r'【答案】|【参考答案】|参考答案', v)[0].strip()
                # 去掉末尾的 " />" HTML 残留
                v = re.sub(r'\s*"\s*/?>.*$', '', v).strip()
                current_opts[k] = v
                i += 1
                continue
        
        # 检测答案行
        ans = extract_ans(line)
        if ans:
            current_ans = ans
            i += 1
            continue
        
        if current_q:
            current_q += ' ' + line
        i += 1
    
    # last
    if current_q and current_ans and current_opts:
        q_text = re.sub(r'^\[(?:单选|多选|判断)题\]\s*\d+[.．、]?\s*', '', current_q).strip()
        if q_text and len(q_text) > 5:
            dk = (q_text[:60], current_ans)
            if dk not in seen:
                qs.append({"题号": len(qs)+1, "题干": q_text, "选项": dict(current_opts), "答案": current_ans})
    
    # annotate
    for q in qs:
        q['id'] = f"q_科一_108453_{q['题号']:03d}"
        q['科目'] = '科目一'
        q['来源'] = '思想政治与法律基础_题库三'
        q['类型'] = '主题库'
        if len(q['答案']) >= 2:
            q['答案'] = ''.join(sorted(q['答案']))
        q['题型'] = '多选题' if len(q['答案']) >= 2 else '单选题'
    
    return qs


def parse_108451():
    """带文字解析的选择题"""
    raw = fetch(108451)
    text = clean(raw)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 3]
    
    # 找到实际内容起点（从第二个"一、选择题"开始，跳过元数据）
    content_start = 0
    found_first = False
    for i, l in enumerate(lines):
        if '一、选择题' in l:
            if not found_first:
                found_first = True
            else:
                content_start = i + 1
                break
    
    # 提取选择题 Q&A
    q_lines = []  # 题干行
    opt_groups = []  # 选项组
    current_opts = OrderedDict()
    current_q = ''
    
    i = content_start
    # 先提取所有题干和选项
    while i < len(lines):
        line = lines[i]
        if line == '一、选择题' or '二、填空题' in line or '###' in line or '答案及解析' in line:
            if current_q and current_opts:
                q_lines.append(current_q)
                opt_groups.append(dict(current_opts))
            if '二、填空题' in line or '###' in line:
                break
            current_q = ''
            current_opts = OrderedDict()
            i += 1
            continue
        
        om = re.match(r'^([A-Da-d])[.、．\s]', line)
        if om:
            k = om.group(1).upper()
            v = re.sub(r'^[A-Da-d][.、．\s]+', '', line).strip()
            v = re.sub(r'\s*"\s*/?>.*$', '', v).strip()
            if k == 'A' and current_q:
                # 新题开始，保存上一题
                q_lines.append(current_q)
                opt_groups.append(dict(current_opts))
                current_q = ''
                current_opts = OrderedDict()
            elif not current_q and not current_opts:
                # 刚开始第一题，选项先缓存在第一个有效 q 之前
                pass
            current_opts[k] = v
        elif re.search(r'[？?]', line) or re.search(r'(是|包括|体现在|目标是|标志是|特征|矛盾|理念|战略|奋斗|核心)', line[:10]):
            # 题干行
            if current_q and current_opts:
                q_lines.append(current_q)
                opt_groups.append(dict(current_opts))
                current_q = ''
                current_opts = OrderedDict()
            current_q = line
        
        i += 1
    
    if current_q and current_opts:
        q_lines.append(current_q)
        opt_groups.append(dict(current_opts))
    
    # 提取答案解析
    ans_start = None
    for i, l in enumerate(lines):
        if '答案及解析' in l and '一、选择题' in lines[i+1:i+3]:
            ans_start = i
            break
    
    ans_texts = []
    if ans_start:
        for l in lines[ans_start:]:
            if l.startswith('解析：') or l.startswith('解析:'):
                ans_texts.append(l[3:].strip())
            elif '三、多选题' in l or '二、填空题' in l:
                continue
            elif '###' in l and '答案' not in l:
                break
    
    # 将文字解析映射到选项字母
    def match_answer_text(question_text, options, ans_text):
        """从选项文字匹配答案文本的关键内容"""
        if not options or not ans_text:
            return ''
        # 直接检查答案文本是否包含选项文本（或反之）
        best = None
        for k, v in options.items():
            # 去掉选项中的修饰词
            v_clean = v.strip()
            if v_clean and (v_clean in ans_text or ans_text[:10] in v_clean):
                if best is None:
                    best = k
                # 更长的匹配更可靠
                if len(v_clean) > len(options.get(best, '')):
                    best = k
        return best or ''
    
    questions = []
    seen = set()
    for qi, (q_text, opts) in enumerate(zip(q_lines[:len(ans_texts)], opt_groups[:len(ans_texts)])):
        ans_text = ans_texts[qi] if qi < len(ans_texts) else ''
        ans_letter = match_answer_text(q_text, opts, ans_text)
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
        })
    
    # 多选题部分
    multi_start = None
    for i, l in enumerate(lines):
        if '三、多选题' in l:
            multi_start = i
            break
    
    if multi_start:
        multi_qs = []
        i = multi_start + 1
        cur_q = ''
        cur_opts = OrderedDict()
        
        while i < len(lines):
            line = lines[i]
            if '###' in line or '考试题库' in line:
                if cur_q and cur_opts:
                    multi_qs.append((cur_q, dict(cur_opts)))
                break
            
            # 检查答案行如 A、B、C、D
            if re.match(r'^[A-Da-d][、，,]\s*[A-Da-d]', line):
                ans = ''.join(sorted(re.findall(r'[A-Da-d]', line))).upper()
                if cur_q and cur_opts:
                    multi_qs.append((cur_q, dict(cur_opts), ans))
                cur_q = ''
                cur_opts = OrderedDict()
                i += 1
                continue
            
            om = re.match(r'^([A-Da-d])[.、．\s]', line)
            if om:
                k = om.group(1).upper()
                v = re.sub(r'^[A-Da-d][.、．\s]+', '', line).strip()
                cur_opts[k] = v
            elif not re.match(r'^[A-Da-d][、，,]', line) and not line.startswith('解析'):
                if cur_q:
                    cur_q += ' ' + line
                else:
                    cur_q = line
            i += 1
        
        for mq in multi_qs:
            if len(mq) == 3:
                q_text, opts, ans = mq
            else:
                continue
            if not ans or not opts:
                continue
            dk = (q_text[:60], ans)
            if dk in seen:
                continue
            seen.add(dk)
            questions.append({
                "题号": len(questions) + 1,
                "题干": q_text,
                "选项": opts,
                "答案": ans,
            })
    
    # annotate
    for q in questions:
        q['id'] = f"q_科一_108451_{q['题号']:03d}"
        q['科目'] = '科目一'
        q['来源'] = '思想政治与法律基础_题库一'
        q['类型'] = '主题库'
        if len(q['答案']) >= 2:
            q['答案'] = ''.join(sorted(q['答案']))
        q['题型'] = '多选题' if len(q['答案']) >= 2 else '单选题'
    
    return questions


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("📥 Parsing 108453 (思政题库三)...")
    qs453 = parse_108453()
    print(f"  → {len(qs453)} 题")
    with open(os.path.join(DATA_DIR, 's1-qb-13.json'), 'w', encoding='utf-8') as f:
        json.dump(qs453, f, ensure_ascii=False, indent=2)
    
    print("📥 Parsing 108451 (思政题库一)...")
    qs451 = parse_108451()
    print(f"  → {len(qs451)} 题")
    with open(os.path.join(DATA_DIR, 's1-qb-11.json'), 'w', encoding='utf-8') as f:
        json.dump(qs451, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！新增 {len(qs451) + len(qs453)} 题")
    print(f"   108451: {len(qs451)} 题")
    print(f"   108453: {len(qs453)} 题")

if __name__ == '__main__':
    main()
