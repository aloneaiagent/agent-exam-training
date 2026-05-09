#!/usr/bin/env python3
"""构建 index.json 和 all_questions.json"""
import json, os, glob

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 科目映射
SUBJECT_MAP = {
    "s1-qb-": "科目一",
    "s2-qb-": "科目二",
    "mock-": "综合",
    "other-": "综合",
}

# Exact-filename subject override for files that don't fit prefix patterns
SUBJECT_OVERRIDE = {
    "ycjjr-108319": "综合",
    "ycjjr-108320": "综合",
    "ycjjr-108324": "综合",
    "ycjjr-108325": "综合",
    "ycjjr-108327": "综合",
    "ycjjr-108348": "综合",
}

TYPE_MAP = {
    "s1-qb-": "主题库",
    "s2-qb-": "主题库",
    "mock-": "模拟卷",
    "other-": "主题库",
    "ycjjr-108319": "模拟卷",
    "ycjjr-108320": "模拟卷",
    "ycjjr-108324": "模拟卷",
    "ycjjr-108325": "模拟卷",
    "ycjjr-108327": "模拟卷",
    "ycjjr-108348": "模拟卷",
}

SOURCE_NAMES = {
    "s1-qb-01": "思想政治与法律基础_一",
    "s1-qb-02": "思想政治与法律基础_二",
    "s1-qb-03": "思想政治与法律基础_三",
    "s1-qb-04": "思想政治与法律基础_四",
    "s1-qb-05": "思想政治与法律基础_五",
    "s1-qb-06": "思想政治与法律基础_六",
    "s1-qb-07": "思想政治与法律基础_七",
    "s1-qb-08": "思想政治与法律基础_八",
    "s1-qb-09": "思想政治与法律基础_九",
    "s1-qb-10": "思想政治与法律基础_十",
    "s1-qb-11": "思想政治与法律基础_题库一",
    "s1-qb-12": "思想政治与法律基础_题库二",
    "s1-qb-13": "思想政治与法律基础_题库三",
    "s2-qb-01": "演出市场政策与经纪实务_一",
    "s2-qb-02": "演出市场政策与经纪实务_二",
    "s2-qb-03": "演出市场政策与经纪实务_三",
    "s2-qb-04": "演出市场政策与经纪实务_四",
    "s2-qb-05": "演出市场政策与经纪实务_五",
    "s2-qb-06": "演出市场政策与经纪实务_六",
    "s2-qb-07": "演出市场政策与经纪实务_七",
    "s2-qb-08": "演出市场政策与经纪实务_八",
    "s2-qb-09": "演出市场政策与经纪实务_九",
    "s2-qb-10": "演出市场政策与经纪实务_十",
    "s2-qb-11": "演出市场政策与经纪实务_考试题库一",
    "s2-qb-12": "演出市场政策与经纪实务_考试题库二",
    "s2-qb-13": "演出市场政策与经纪实务_考试题库三",
    "mock-01": "模拟试题（常考点）",
    "mock-02": "模拟试题（常考点2）",
    "mock-03": "模拟题",
    "other-01": "精编版",
    "ycjjr-108319": "政策法规与经纪实务模拟题一",
    "ycjjr-108320": "政策法规与经纪实务模拟题二",
    "ycjjr-108324": "舞台艺术基础知识模拟题一",
    "ycjjr-108325": "舞台艺术基础知识模拟题二",
    "ycjjr-108327": "政策法规与经纪实务模拟题三",
    "ycjjr-108348": "舞台艺术基础知识考试练习题",
}

# 找到所有 json 文件 (排除 index.json, all_questions.json)
data_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
data_files = [f for f in data_files
             if not f.endswith("index.json")
             and not f.endswith("all_questions.json")
             and not f.endswith("progress.json")
             and not f.endswith("progress.json.bak")]

all_questions = []
index = {}

for fpath in data_files:
    fname = os.path.basename(fpath).replace(".json", "")
    with open(fpath, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    if not questions:
        continue

    all_questions.extend(questions)

    # Determine subject and type from prefix (or exact override)
    subject = "综合"
    qtype = "主题库"
    if fname in SUBJECT_OVERRIDE:
        subject = SUBJECT_OVERRIDE[fname]
    else:
        for prefix, s in SUBJECT_MAP.items():
            if fname.startswith(prefix):
                subject = s
                break
    for prefix, t in TYPE_MAP.items():
        if fname.startswith(prefix):
            qtype = t
            break

    source_name = SOURCE_NAMES.get(fname, fname)

    if subject not in index:
        index[subject] = {"主题库": {}, "模拟卷": {}}
    if qtype not in index[subject]:
        index[subject][qtype] = {}

    index[subject][qtype][source_name] = {
        "文件": f"{fname}.json",
        "总题数": len(questions),
        "单选题": len([q for q in questions if q.get("题型") == "单选题"]),
        "多选题": len([q for q in questions if q.get("题型") == "多选题"]),
    }

# Add subtotals
for subject in ["科目一", "科目二", "综合"]:
    if subject not in index:
        index[subject] = {"主题库": {}, "模拟卷": {}}
    for qtype in ["主题库", "模拟卷"]:
        srcs = index[subject][qtype]
        if srcs:
            index[subject][qtype]["_小计"] = {
                "来源数": len([k for k in srcs if not k.startswith("_")]),
                "总题数": sum(s["总题数"] for k, s in srcs.items() if not k.startswith("_")),
                "单选题": sum(s["单选题"] for k, s in srcs.items() if not k.startswith("_")),
                "多选题": sum(s["多选题"] for k, s in srcs.items() if not k.startswith("_")),
            }

# Save
with open(os.path.join(DATA_DIR, "index.json"), 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA_DIR, "all_questions.json"), 'w', encoding='utf-8') as f:
    json.dump(all_questions, f, ensure_ascii=False, indent=2)

print(f"✅ 索引构建完成！")
print(f"   总题目数: {len(all_questions)}")
for subject in ["科目一", "科目二", "综合"]:
    s_qs = [q for q in all_questions if q.get("科目") == subject]
    if s_qs:
        print(f"   {subject}: {len(s_qs)} 题")
