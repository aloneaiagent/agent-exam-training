#!/usr/bin/env python3
"""
Phase 1: 数据编译 — 将 ycjjr.net 文章解析为结构化 JSON

用法:
  python3 parse_articles.py

输出:
  ../data/index.json        ← 全量索引
  ../data/km1.01.json       ← 科目一_题库一
  ../data/km1.02.json       ← ...
  ../data/km2.01.json       ← 科目二_题库一
  ../data/km2.10.json       ← ...
  ../data/mock.01.json      ← 模拟卷
  ../data/mock.02.json
  ../data/mock.03.json
"""

import re, json, html, os, sys
from urllib.request import urlopen
from urllib.error import URLError
from collections import OrderedDict

# ═══════════════════════════════════════════════════════
# 文章清单 & 元数据
# ═══════════════════════════════════════════════════════

BASE_URL = "https://www.ycjjr.net/article/"

ARTICLES = [
    # ── 科目一：思想政治与法律基础 ──
    {"id": 108379, "科目": "科目一", "来源": "思想政治与法律基础_一", "类型": "主题库"},
    {"id": 108380, "科目": "科目一", "来源": "思想政治与法律基础_二", "类型": "主题库"},
    {"id": 108381, "科目": "科目一", "来源": "思想政治与法律基础_三", "类型": "主题库"},
    {"id": 108382, "科目": "科目一", "来源": "思想政治与法律基础_四", "类型": "主题库"},
    {"id": 108383, "科目": "科目一", "来源": "思想政治与法律基础_五", "类型": "主题库"},
    {"id": 108384, "科目": "科目一", "来源": "思想政治与法律基础_六", "类型": "主题库"},
    {"id": 108385, "科目": "科目一", "来源": "思想政治与法律基础_七", "类型": "主题库"},
    {"id": 108386, "科目": "科目一", "来源": "思想政治与法律基础_八", "类型": "主题库"},
    {"id": 108387, "科目": "科目一", "来源": "思想政治与法律基础_九", "类型": "主题库"},
    {"id": 108388, "科目": "科目一", "来源": "思想政治与法律基础_十", "类型": "主题库"},

    # ── 科目二：演出市场政策与经纪实务 ──
    {"id": 108369, "科目": "科目二", "来源": "演出市场政策与经纪实务_一", "类型": "主题库"},
    {"id": 108370, "科目": "科目二", "来源": "演出市场政策与经纪实务_二", "类型": "主题库"},
    {"id": 108371, "科目": "科目二", "来源": "演出市场政策与经纪实务_三", "类型": "主题库"},
    {"id": 108372, "科目": "科目二", "来源": "演出市场政策与经纪实务_四", "类型": "主题库"},
    {"id": 108373, "科目": "科目二", "来源": "演出市场政策与经纪实务_五", "类型": "主题库"},
    {"id": 108374, "科目": "科目二", "来源": "演出市场政策与经纪实务_六", "类型": "主题库"},
    {"id": 108375, "科目": "科目二", "来源": "演出市场政策与经纪实务_七", "类型": "主题库"},
    {"id": 108376, "科目": "科目二", "来源": "演出市场政策与经纪实务_八", "类型": "主题库"},
    {"id": 108377, "科目": "科目二", "来源": "演出市场政策与经纪实务_九", "类型": "主题库"},
    {"id": 108378, "科目": "科目二", "来源": "演出市场政策与经纪实务_十", "类型": "主题库"},

    # ── 模拟卷 ──
    {"id": 108448, "科目": "综合", "来源": "模拟试题（常考点）", "类型": "模拟卷"},
    {"id": 108449, "科目": "综合", "来源": "模拟试题（常考点2）", "类型": "模拟卷"},
    {"id": 108447, "科目": "综合", "来源": "模拟题", "类型": "模拟卷"},
    {"id": 108450, "科目": "综合", "来源": "精编版", "类型": "主题库"},

    # ── 科目一 额外题库（from page 1） ──
    {"id": 108451, "科目": "科目一", "来源": "思想政治与法律基础_题库一", "类型": "主题库"},
    {"id": 108452, "科目": "科目一", "来源": "思想政治与法律基础_题库二", "类型": "主题库"},
    {"id": 108453, "科目": "科目一", "来源": "思想政治与法律基础_题库三", "类型": "主题库"},

    # ── 科目二 额外题库（from page 1） ──
    {"id": 108454, "科目": "科目二", "来源": "演出市场政策与经纪实务_考试题库一", "类型": "主题库"},
    {"id": 108455, "科目": "科目二", "来源": "演出市场政策与经纪实务_考试题库二", "类型": "主题库"},
    {"id": 108456, "科目": "科目二", "来源": "演出市场政策与经纪实务_考试题库三", "类型": "主题库"},
]


# ═══════════════════════════════════════════════════════
# HTML 获取
# ═══════════════════════════════════════════════════════

def fetch_article(aid: int) -> str:
    """获取文章 HTML"""
    url = f"{BASE_URL}{aid}.html"
    try:
        with urlopen(url, timeout=20) as resp:
            raw = resp.read()
            # 尝试检测编码
            encoding = resp.headers.get_content_charset() or 'utf-8'
            return raw.decode(encoding, errors='replace')
    except URLError as e:
        print(f"  ⚠️  获取失败 {aid}: {e}")
        return ""
    except Exception as e:
        print(f"  ⚠️  未知错误 {aid}: {e}")
        return ""


# ═══════════════════════════════════════════════════════
# HTML 清洗
# ═══════════════════════════════════════════════════════

def clean_html(html_text: str) -> list[str]:
    """
    去掉 script/style 标签，去掉 HTML 标签，
    解码 HTML 实体，返回非空行列表。
    注意：要求仅保留文章真正的内容区域，避开模板/元数据/相关文章区。
    """
    # 去掉 script / style / 注释
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # 去掉 HTML 标签
    text = re.sub(r'<[^>]+>', '\n', text)
    # 解码实体
    text = html.unescape(text)
    # 整理空白
    text = re.sub(r'\xa0', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\u3000', ' ', text)
    # 去掉 HTML 属性残留如 " /"
    text = re.sub(r'"\s*/?>', '', text)
    # 分行取非空
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return lines


# ═══════════════════════════════════════════════════════
# 选项提取
# ═══════════════════════════════════════════════════════

def extract_options(lines: list[str], start_idx: int) -> tuple[dict[str, str], int]:
    """从 start_idx 往后提取 A/B/C/D 选项行, 返回 (选项字典, 最后行号+1)"""
    options = OrderedDict()
    i = start_idx
    # 跳过空行和题干延续行（以中文标点、字母、数字开头的不算新题的行）
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^([A-Da-d])[.、．\s]', line)
        if m:
            opt_key = m.group(1).upper()
            opt_text = re.sub(r'^[A-Da-d][.、．\s]+', '', line).strip()
            # 去掉尾部的 【答案】 内容
            opt_text = re.split(r'【答案】|【参考答案】', opt_text)[0].strip()
            options[opt_key] = opt_text
            i += 1
        else:
            # 如果遇到另一行不是选项格式，停止
            # 检查是否可能是选项的延续行
            if options and re.match(r'^[A-Da-d]', line):
                # 可能是放在行首的单字母但不是选项格式，跳过
                i += 1
                continue
            break
    return options, i


# ═══════════════════════════════════════════════════════
# 统一的答案提取
# ═══════════════════════════════════════════════════════

def extract_answer(text: str) -> str:
    """从文本中提取答案，支持多种格式"""
    # 【答案】X 或 【参考答案】X
    m = re.search(r'【答案】\s*([A-Da-d]+)', text)
    if m:
        return m.group(1).upper().strip()
    m = re.search(r'【参考答案】\s*([A-Da-d]+)', text)
    if m:
        return m.group(1).upper().strip()
    # （答案：X）或 (答案：X) 或 （参考答案：X）
    m = re.search(r'[（(]\s*(?:参考)?答案\s*[：:]\s*([A-Da-d]+)\s*[）)]', text)
    if m:
        return m.group(1).upper().strip()
    # 答案：X 或 参考答案：X
    m = re.search(r'(?:参考)?答案\s*[：:]\s*([A-Da-d]+)', text)
    if m:
        # 只取行首或选项结尾附近的结果，避免误抓题干中的"答案"二字
        prefix = text[:m.start()][-30:]
        if not re.search(r'[。，；]', prefix[-5:]):
            return m.group(1).upper().strip()
    return ""


# ═══════════════════════════════════════════════════════
# 判断行是否包含可用的答案标记
# ═══════════════════════════════════════════════════════

def line_has_answer(line: str) -> bool:
    """判断此行是否是答案行（包含明确的答案标记）"""
    if re.search(r'【答案】|【参考答案】', line):
        return True
    if re.search(r'[（(]\s*(?:参考)?答案\s*[：:]\s*[A-D]', line):
        return True
    # 答案：X  或 参考答案：X
    if re.search(r'(?:^|\s)(?:参考)?答案\s*[：:]\s*[A-Da-d]', line):
        return True
    return False


# ═══════════════════════════════════════════════════════
# 辅助：将收集到的问题片段整理为字典
# ═══════════════════════════════════════════════════════

def _finalize_question(q_text: str, options: OrderedDict, answer: str):
    """整理问题片段为标准字典，返回 None 表示无效"""
    q_text_clean = re.sub(r'^\d+[、.．]\s*', '', q_text).strip()
    # 去掉尾部答案标记（可能因内联而残留）
    q_text_clean = re.split(r'【答案】|【参考答案】', q_text_clean)[0].strip()
    q_text_clean = re.sub(r'答案[：:].*$', '', q_text_clean).strip()
    has_options = bool(dict(options) if options else {})
    has_ans = bool(answer)
    if q_text_clean and has_ans and has_options and len(q_text_clean) > 5:
        return {
            "题号": 0,
            "题号原文": 0,
            "题干": q_text_clean,
            "选项": dict(options),
            "答案": answer
        }
    return None


# ═══════════════════════════════════════════════════════
# 题目解析：格式 C — 完全内嵌式（所有内容在一行内）
# 如: "1、题干... A.xxx B.xxx C.xxx D.xxx 【答案】X"
# ═══════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════
# 辅助：从文本中提取同一行的内嵌选项 A/B/C/D
# ═══════════════════════════════════════════════════════

def extract_inline_options(text: str, start_pos: int = 0) -> tuple[OrderedDict, int]:
    """从文本中提取同一行的内嵌选项 A/B/C/D
    返回 (选项字典, 最后匹配结束位置)
    匹配格式如: A.xxx B.xxx C.xxx D.xxx
    """
    options = OrderedDict()
    text_after = re.sub(r'^\d+[、.．]\s*', '', text[start_pos:])
    if not re.search(r'[A-Da-d]\.', text_after):
        return options, start_pos
    parts = re.split(r'(?=[A-Da-d]\.)', text_after)
    if len(parts) > 1:
        for p in parts:
            m = re.match(r'([A-Da-d])\.(.+)', p.strip())
            if m:
                key = m.group(1).upper()
                val = m.group(2).strip().rstrip(',').strip()
                options[key] = val
        return options, start_pos + len(text_after)
    return options, start_pos


# ═══════════════════════════════════════════════════════
# 题目解析：格式 C — 完全内嵌式（答案必须有 【答案】）
# ═══════════════════════════════════════════════════════

def parse_questions_format_C(full_text: str) -> list[dict]:
    """
    格式: 每道题的题干、选项、答案全部嵌在同一文本段落内
    如: "1、题干... A.xxx B.xxx C.xxx D.xxx 【答案】X"
    """
    questions = []
    pattern = re.compile(
        r'(?:(\d+)[、.．]\s*'  # 题号
        r'.*?'  # 题干
        r'[A-Da-d]\.\s*'  # A.
        r'.*?'  # A内容
        r'[A-Da-d]\.\s*'  # B.
        r'.*?'  # B内容
        r'[A-Da-d]\.\s*'  # C.
        r'.*?'  # C内容
        r'[A-Da-d]\.\s*'  # D.
        r'.*?'  # D内容
        r'【答案】\s*([A-Da-d]+))',  # 【答案】X
        re.DOTALL
    )
    
    for match in pattern.finditer(full_text):
        qnum = int(match.group(1))
        ans = match.group(2).upper().strip()
        q_full = match.group(0)
        
        # 从完整匹配中提取题干
        opt_start = re.search(r'[A-Da-d]\.\s*', q_full)
        if not opt_start:
            continue
        question_text = q_full[:opt_start.start()].strip()
        question_text = re.sub(r'^\d+[、.．]\s*', '', question_text).strip()
        
        # 提取选项
        options = OrderedDict()
        opt_matches = list(re.finditer(r'([A-Da-d])\.\s*', q_full))
        for i, om in enumerate(opt_matches):
            opt_key = om.group(1).upper()
            opt_start_pos = om.end()
            opt_end = opt_matches[i + 1].start() if i + 1 < len(opt_matches) else q_full.rfind('【答案】')
            opt_text = q_full[opt_start_pos:opt_end].strip().rstrip(',').strip()
            options[opt_key] = opt_text
        
        if question_text and ans and len(options) >= 2:
            questions.append({
                "题号": len(questions) + 1,
                "题号原文": qnum,
                "题干": question_text,
                "选项": dict(options),
                "答案": ans
            })
    
    return questions


# ═══════════════════════════════════════════════════════
# 题目解析：格式 A — 数字+题干 ... 【答案】X（逐行解析）
# ═══════════════════════════════════════════════════════

def parse_questions_format_A(lines: list[str]) -> list[dict]:
    """
    格式: 1、题干... 选项行... 【答案】X
    特点：题号后跟 、 或 .
    答案标记为 【答案】X 或 【参考答案】X
    """
    questions = []
    i = 0
    current_q = None
    current_options = OrderedDict()
    collecting_options = False
    _seen_dups = set()  # 去重

    while i < len(lines):
        line = lines[i]

        # 跳过明显的干扰行
        if re.match(r'^(第[A-Z\d]+页|首页|上一页|下一页|末页|相关文章|考试题库|搜索)', line):
            i += 1
            continue

        # 检查是否是题号行: 1、 或 1. 或 1．
        m = re.match(r'^(\d+)[、.．]', line)
        if m:
            qnum = int(m.group(1))
            if 1 <= qnum <= 200:
                # 如果有上一题未完成，保存
                if current_q is not None:
                    finished_question = _finalize_question(current_q, current_options, current_ans)
                    if finished_question:
                        dup_key = (finished_question['题干'][:60], finished_question['答案'])
                        if dup_key not in _seen_dups:
                            _seen_dups.add(dup_key)
                            finished_question['题号'] = len(questions) + 1
                            questions.append(finished_question)

                # 新题目开始
                current_q = line
                current_options = OrderedDict()
                current_ans = ""
                collecting_options = True
                
                # 检查同一行是否内嵌了选项（如 "题干... A.xxx B.xxx C.xxx D.xxx 【答案】X"）
                inline_opts, inline_end = extract_inline_options(line, 0)
                if inline_opts:
                    current_options = inline_opts
                    # 检查同一行是否有答案
                    ans = extract_answer(line)
                    if ans:
                        current_ans = ans
                
                i += 1
                continue

        # 收集选项
        if collecting_options and current_q is not None:
            om = re.match(r'^([A-Da-d])[.、．\s]', line)
            if om:
                opt_key = om.group(1).upper()
                opt_text = re.sub(r'^[A-Da-d][.、．\s]+', '', line).strip()
                # 去掉答案标记
                opt_text = re.split(r'【答案】|【参考答案】|答案[：:]', opt_text)[0].strip()
                current_options[opt_key] = opt_text
                i += 1
                continue

        # 检查是否是答案行（支持多种格式）
        if line_has_answer(line):
            ans = extract_answer(line)
            if ans:
                current_ans = ans
            i += 1
            continue

        # 如果是题干延续行（没有题号，不是选项，不是答案）
        if current_q is not None and not collecting_options:
            current_q += " " + line

        i += 1

    # 最后一题
    if current_q is not None and current_q:
        q_text = re.sub(r'^\d+[、.．]\s*', '', current_q).strip()
        q_text = re.split(r'【答案】|【参考答案】|答案[：:]', q_text)[0].strip()
        has_options = bool(dict(current_options))
        has_ans = bool(current_ans)
        if q_text and has_ans and has_options and len(q_text) > 5:
            dup_key = (q_text[:30], current_ans)
            if dup_key not in _seen_dups:
                questions.append({
                    "题号": len(questions) + 1,
                    "题号原文": 0,
                    "题干": q_text,
                    "选项": dict(current_options),
                    "答案": current_ans if current_ans else ""
                })

    return questions


# ═══════════════════════════════════════════════════════
# 题目解析：格式 B — 【题干X】... 【参考答案】X
# ═══════════════════════════════════════════════════════

def parse_questions_format_B(lines: list[str]) -> list[dict]:
    """
    格式: 【题干1】题干... 【参考答案】ABCD
    使用显式的 【题干X】 标记
    """
    questions = []
    full_text = '\n'.join(lines)

    # 分段按 【题干X】 分割
    segments = re.split(r'【题干(\d+)】', full_text)
    # segments[0] 是前导文字，之后是 [num, text, num, text, ...]
    for i in range(1, len(segments), 2):
        if i + 1 >= len(segments):
            break
        qnum = int(segments[i])
        content = segments[i + 1]

        # 提取答案
        ans_m = re.search(r'【参考答案】\s*([A-Da-d]+)', content)
        ans = ans_m.group(1).upper().strip() if ans_m else ""

        # 去掉答案标记
        content = re.sub(r'【参考答案】\s*[A-Da-d]*', '', content).strip()

        # 提取题干（截取到选项开始之前）
        # 查找选项
        options = OrderedDict()
        opt_matches = list(re.finditer(r'([A-Da-d])[.、．\s]', content))
        if opt_matches:
            first_opt = opt_matches[0].start()
            question_text = content[:first_opt].strip()
            # 提取各个选项
            for j, om in enumerate(opt_matches):
                opt_key = om.group(1).upper()
                opt_start = om.start()
                opt_end = opt_matches[j + 1].start() if j + 1 < len(opt_matches) else len(content)
                opt_text = content[opt_start:opt_end].strip()
                opt_text = re.sub(r'^[A-Da-d][.、．\s]+', '', opt_text).strip()
                options[opt_key] = opt_text
        else:
            question_text = content

        question_text = question_text.strip()
        if question_text and ans:
            questions.append({
                "题号": len(questions) + 1,
                "题号原文": qnum,
                "题干": question_text,
                "选项": dict(options),
                "答案": ans
            })

    return questions


# ═══════════════════════════════════════════════════════
# 检测题型：单选还是多选
# ═══════════════════════════════════════════════════════

def detect_type(answer: str) -> str:
    """根据答案字符串判断题型"""
    if not answer:
        return "单选题"
    # 去掉可能的标点
    clean = re.sub(r'[^A-D]', '', answer.upper())
    if len(clean) >= 2:
        return "多选题"
    return "单选题"


# ═══════════════════════════════════════════════════════
# 主流程：解析一篇文章
# ═══════════════════════════════════════════════════════

def parse_article(meta: dict) -> list[dict]:
    """解析一篇文章，返回题目列表"""
    aid = meta["id"]
    print(f"  📥 article {aid} ({meta['来源']})...", end=" ")

    html_text = fetch_article(aid)
    if not html_text:
        print("❌ 获取失败")
        return []

    lines = clean_html(html_text)

    # 检测格式类型
    full_text = '\n'.join(lines)
    has_tigan = bool(re.search(r'【题干\d+】', full_text))
    has_inline_q = bool(re.search(r'【答案】', full_text))
    # 格式C特征：题号 + A. + B. + C. + D. + 【答案】 在一段连续文本中
    has_inline_all = bool(re.search(r'\d+[、.．].*?[A-Da-d]\..*?[A-Da-d]\..*?[A-Da-d]\..*?[A-Da-d]\..*?【答案】', full_text, re.DOTALL))

    if has_tigan:
        questions = parse_questions_format_B(lines)
        print(f"格式B → {len(questions)}题", end=" ")
    elif has_inline_all:
        questions = parse_questions_format_C(full_text)
        print(f"格式C → {len(questions)}题", end=" ")
    else:
        questions = parse_questions_format_A(lines)
        print(f"格式A → {len(questions)}题", end=" ")

    # 标注科目、来源、题型
    for q in questions:
        q["科目"] = meta["科目"]
        q["来源"] = meta["来源"]
        q["类型"] = meta["类型"]
        q["题型"] = detect_type(q["答案"])
        # 答案排序（多选题标准化）
        if len(q["答案"]) >= 2:
            q["答案"] = ''.join(sorted(q["答案"]))
        # 生成唯一 ID
        q["id"] = f"q_{meta['科目'][:2]}_{aid}_{q['题号']:03d}"

    print(f"({meta['科目']} · {len([q for q in questions if q['题型']=='单选题'])}单选 + "
          f"{len([q for q in questions if q['题型']=='多选题'])}多选)")

    return questions


# ═══════════════════════════════════════════════════════
# JSON 序列化
# ═══════════════════════════════════════════════════════

def save_json(data: list[dict], path: str):
    """保存为格式化 JSON"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def main():
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(DATA_DIR, exist_ok=True)

    all_questions = []
    index = {
        "科目一": {"主题库": {}, "模拟卷": {}},
        "科目二": {"主题库": {}, "模拟卷": {}},
        "综合": {"主题库": {}, "模拟卷": {}},
    }

    file_counter = {"科目一": 0, "科目二": 0}

    for meta in ARTICLES:
        questions = parse_article(meta)
        if not questions:
            print("  ⚠️  跳过（0 题）")
            continue

        all_questions.extend(questions)

        # 决定输出文件名（全部英文）
        km = meta["科目"]
        src = meta["来源"]
        qtype = meta["类型"]

        if qtype == "模拟卷":
            # 按科目分组
            if km == "科目一":
                filename = f"s1-mock-{file_counter.get('s1_mock', 0) + 1:02d}.json"
            elif km == "科目二":
                filename = f"s2-mock-{file_counter.get('s2_mock', 0) + 1:02d}.json"
            else:
                filename = f"mock-{meta['id']}.json"
        else:
            if km == "科目一":
                file_counter["科目一"] += 1
                filename = f"s1-qb-{file_counter['科目一']:02d}.json"
            elif km == "科目二":
                file_counter["科目二"] += 1
                filename = f"s2-qb-{file_counter['科目二']:02d}.json"
            else:
                filename = f"other-{meta['id']}.json"
        
        # 追踪模拟卷计数器
        if qtype == "模拟卷":
            if km == "科目一":
                file_counter['s1_mock'] = file_counter.get('s1_mock', 0) + 1
            elif km == "科目二":
                file_counter['s2_mock'] = file_counter.get('s2_mock', 0) + 1

        filepath = os.path.join(DATA_DIR, filename)
        save_json(questions, filepath)
        print(f"    → {filename}")

        # 更新索引
        d_src = index[km][qtype]
        d_src[src] = {
            "文件": filename,
            "文章ID": meta["id"],
            "总题数": len(questions),
            "单选题": len([q for q in questions if q["题型"] == "单选题"]),
            "多选题": len([q for q in questions if q["题型"] == "多选题"]),
        }

    # 生成全量索引
    # 添加汇总统计
    for km in ["科目一", "科目二", "综合"]:
        for qt in ["主题库", "模拟卷"]:
            srcs = index[km][qt]
            if srcs:
                index[km][qt]["_小计"] = {
                    "来源数": len(srcs),
                    "总题数": sum(s["总题数"] for s in srcs.values()),
                    "单选题": sum(s["单选题"] for s in srcs.values()),
                    "多选题": sum(s["多选题"] for s in srcs.values()),
                }

    save_json(all_questions, os.path.join(DATA_DIR, "all_questions.json"))
    save_json(index, os.path.join(DATA_DIR, "index.json"))

    print(f"\n{'='*50}")
    print(f"✅ 解析完成！")
    print(f"   总题目数: {len(all_questions)}")
    print(f"   科目一: {len([q for q in all_questions if q['科目']=='科目一'])} 题")
    print(f"   科目二: {len([q for q in all_questions if q['科目']=='科目二'])} 题")
    print(f"   综合: {len([q for q in all_questions if q['科目']=='综合'])} 题")
    print(f"   数据文件: {DATA_DIR}/")


if __name__ == "__main__":
    main()
