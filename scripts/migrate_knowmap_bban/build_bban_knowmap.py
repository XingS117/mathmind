"""
Build 人教 B 版 (2019) 高中数学知识图谱, 并把 knowmap.json 里的高中部分替换掉。

数据依据:
- 教材册/章: 人民教育出版社 pep.com.cn 官网 (2026-07-09 抓取的 _temp/pep.txt)
- 节: 人教 B 版教材通行目录 (若与教材新版细节有差异, 后续可微调)

初中 3 册 (cz_qs1/2, cz_bs1/2, cz_js1/2) 保持不变。
旧高中 id -> 新高中 id 通过 OLD_TO_NEW 表迁移: seed_questions.json 与 db.questions.knowmap_nodes.
"""
from __future__ import annotations
import json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOWMAP = os.path.join(ROOT, "data", "knowmap.json")
SEED    = os.path.join(ROOT, "data", "seed_questions.json")
DB      = os.path.join(ROOT, "data", "mathmind.db")

# -------------------------------------------------------------------
# 人教 B 版高中数学 (2019) 目录 —— 章级源自 pep.com.cn 抓取, 节级源自 B 版教材通行目录.
# 每册 = (book_id, book_label, book_name, [(chap_id, chap_title, [section_titles])])
BBAN = [
    ("bx1", "必修一", "必修第一册", [
        ("c1", "第一章 集合与常用逻辑用语", [
            "1.1 集合",
            "1.2 常用逻辑用语",
        ]),
        ("c2", "第二章 等式与不等式", [
            "2.1 等式",
            "2.2 不等式",
        ]),
        ("c3", "第三章 函数", [
            "3.1 函数的概念与性质",
            "3.2 函数与方程、不等式之间的关系",
            "3.3 函数的应用(一)",
            "3.4 数学建模活动: 决定苹果的最佳出售时间点",
        ]),
    ]),
    ("bx2", "必修二", "必修第二册", [
        ("c4", "第四章 指数函数、对数函数与幂函数", [
            "4.1 指数与指数函数",
            "4.2 对数与对数函数",
            "4.3 指数函数与对数函数的关系",
            "4.4 幂函数",
            "4.5 增长速度的比较",
            "4.6 函数的应用(二)",
            "4.7 数学建模活动: 生长规律的描述",
        ]),
        ("c5", "第五章 统计与概率", [
            "5.1 统计",
            "5.2 数学探究活动: 由编号样本估计总体的分布",
            "5.3 概率",
            "5.4 统计与概率的应用",
        ]),
        ("c6", "第六章 平面向量初步", [
            "6.1 平面向量及其线性运算",
            "6.2 向量基本定理与向量的坐标",
            "6.3 平面向量线性运算的应用",
        ]),
    ]),
    ("bx3", "必修三", "必修第三册", [
        ("c7", "第七章 三角函数", [
            "7.1 任意角的概念与弧度制",
            "7.2 任意角的三角函数",
            "7.3 三角函数的性质与图像",
            "7.4 数学建模活动: 周期现象的描述",
        ]),
        ("c8", "第八章 向量的数量积与三角恒等变换", [
            "8.1 向量的数量积",
            "8.2 三角恒等变换",
        ]),
    ]),
    ("bx4", "必修四", "必修第四册", [
        ("c9", "第九章 解三角形", [
            "9.1 正弦定理与余弦定理",
            "9.2 正弦定理与余弦定理的应用",
            "9.3 数学探究活动: 得到不确定的三角形吗",
        ]),
        ("c10", "第十章 复数", [
            "10.1 复数及其几何意义",
            "10.2 复数的运算",
            "10.3 复数的三角形式及其运算",
        ]),
        ("c11", "第十一章 立体几何初步", [
            "11.1 空间几何体",
            "11.2 平面的基本事实与推论",
            "11.3 空间中的平行关系",
            "11.4 空间中的垂直关系",
            "11.5 空间中的距离",
            "11.6 简单几何体的再认识",
            "11.7 数学探究活动: 长方体中的几何量的计算",
        ]),
    ]),
    ("xb1", "选择性必修一", "选择性必修第一册", [
        ("c1", "第一章 空间向量与立体几何", [
            "1.1 空间向量及其运算",
            "1.2 空间向量在立体几何中的应用",
        ]),
        ("c2", "第二章 平面解析几何", [
            "2.1 坐标法",
            "2.2 直线及其方程",
            "2.3 圆及其方程",
            "2.4 曲线与方程",
            "2.5 椭圆及其方程",
            "2.6 双曲线及其方程",
            "2.7 抛物线及其方程",
            "2.8 直线与圆锥曲线的位置关系",
        ]),
    ]),
    ("xb2", "选择性必修二", "选择性必修第二册", [
        ("c3", "第三章 排列、组合与二项式定理", [
            "3.1 排列与组合",
            "3.2 二项式定理",
        ]),
        ("c4", "第四章 概率与统计", [
            "4.1 条件概率与事件的独立性",
            "4.2 随机变量",
            "4.3 统计模型",
        ]),
    ]),
    ("xb3", "选择性必修三", "选择性必修第三册", [
        ("c5", "第五章 数列", [
            "5.1 数列基础",
            "5.2 等差数列",
            "5.3 等比数列",
            "5.4 数学归纳法",
            "5.5 数列的应用",
        ]),
        ("c6", "第六章 导数及其应用", [
            "6.1 导数",
            "6.2 利用导数研究函数的性质",
            "6.3 利用导数解决实际问题",
            "6.4 数学探究活动: 生长规律的描述",
        ]),
    ]),
]

# 旧 A 版 id -> 新 B 版 id: 尽可能语义对齐
OLD_TO_NEW = {
    # 必修第一册
    "bx1_c1_s1": "bx1_c1_s1",  # 集合 -> 1.1 集合
    "bx1_c1_s2": "bx1_c1_s1",
    "bx1_c1_s3": "bx1_c1_s1",
    "bx1_c1_s4": "bx1_c1_s2",  # 充分必要条件 -> 常用逻辑用语
    "bx1_c1_s5": "bx1_c1_s2",  # 全称/存在量词 -> 常用逻辑用语
    "bx1_c2_s1": "bx1_c2_s2",  # 不等式性质 -> 2.2 不等式
    "bx1_c2_s2": "bx1_c2_s2",
    "bx1_c2_s3": "bx1_c2_s2",
    "bx1_c3_s1": "bx1_c3_s1",  # 函数概念 -> 3.1
    "bx1_c3_s2": "bx1_c3_s1",  # 函数性质 -> 3.1
    "bx1_c3_s3": "bx2_c4_s4",  # 幂函数 -> B 版在 4.4
    "bx1_c3_s4": "bx1_c3_s3",  # 函数应用 -> 3.3
    "bx1_c4_s1": "bx2_c4_s1",  # 指数 -> B 版指数函数在 必修二 4.1
    "bx1_c4_s2": "bx2_c4_s1",
    "bx1_c4_s3": "bx2_c4_s2",
    "bx1_c4_s4": "bx2_c4_s2",
    "bx1_c4_s5": "bx2_c4_s6",  # 函数应用二 -> 4.6
    "bx1_c5_s1": "bx3_c7_s1",  # 三角函数在 B 版必修三 7.x
    "bx1_c5_s2": "bx3_c7_s2",
    "bx1_c5_s3": "bx3_c7_s2",
    "bx1_c5_s4": "bx3_c7_s3",
    "bx1_c5_s5": "bx3_c8_s2",  # 三角恒等变换 -> 8.2
    "bx1_c5_s6": "bx3_c7_s3",
    "bx1_c5_s7": "bx3_c7_s4",
    # 必修第二册 A -> B
    "bx2_c1_s1": "bx2_c6_s1",  # 平面向量 -> B 版必修二 6.x
    "bx2_c1_s2": "bx2_c6_s1",
    "bx2_c1_s3": "bx2_c6_s2",
    "bx2_c1_s4": "bx2_c6_s3",
    "bx2_c2_s1": "bx4_c10_s1",  # 复数 -> B 版必修四 10.x
    "bx2_c2_s2": "bx4_c10_s2",
    "bx2_c2_s3": "bx4_c10_s3",
    "bx2_c3_s1": "bx4_c11_s1",  # 立体几何 -> B 版必修四 11.x
    "bx2_c3_s2": "bx4_c11_s1",
    "bx2_c3_s3": "bx4_c11_s6",
    "bx2_c3_s4": "bx4_c11_s2",
    "bx2_c3_s5": "bx4_c11_s3",
    "bx2_c3_s6": "bx4_c11_s4",
    "bx2_c4_s1": "bx2_c5_s1",  # 统计 -> B 版必修二 5.1
    "bx2_c4_s2": "bx2_c5_s1",
    "bx2_c5_s1": "bx2_c5_s3",  # 概率 -> B 版必修二 5.3
    "bx2_c5_s2": "bx2_c5_s3",
    "bx2_c5_s3": "bx2_c5_s3",
    # 选择性必修第一册
    "xb1_c1_s1": "xb1_c1_s1",
    "xb1_c1_s2": "xb1_c1_s1",
    "xb1_c1_s3": "xb1_c1_s1",
    "xb1_c1_s4": "xb1_c1_s2",
    "xb1_c2_s1": "xb1_c2_s2",  # 直线倾斜角/斜率 -> 2.2 直线及其方程
    "xb1_c2_s2": "xb1_c2_s2",
    "xb1_c2_s3": "xb1_c2_s2",
    "xb1_c2_s4": "xb1_c2_s3",
    "xb1_c2_s5": "xb1_c2_s3",
    "xb1_c3_s1": "xb1_c2_s5",  # 椭圆
    "xb1_c3_s2": "xb1_c2_s6",  # 双曲线
    "xb1_c3_s3": "xb1_c2_s7",  # 抛物线
    # 选择性必修第二册 A: 数列 & 导数 -> B 版第三册
    "xb2_c1_s1": "xb3_c5_s1",  # 数列概念 -> B 版第三册 5.1
    "xb2_c1_s2": "xb3_c5_s2",
    "xb2_c1_s3": "xb3_c5_s3",
    "xb2_c1_s4": "xb3_c5_s4",
    "xb2_c2_s1": "xb3_c6_s1",  # 导数 -> B 版第三册 6.1
    "xb2_c2_s2": "xb3_c6_s1",
    "xb2_c2_s3": "xb3_c6_s2",
    # 选择性必修第三册 A: 计数原理 / 随机变量 / 成对数据 -> B 版第二册
    "xb3_c1_s1": "xb2_c3_s1",
    "xb3_c1_s2": "xb2_c3_s1",
    "xb3_c1_s3": "xb2_c3_s2",
    "xb3_c2_s1": "xb2_c4_s1",
    "xb3_c2_s2": "xb2_c4_s2",
    "xb3_c2_s3": "xb2_c4_s2",
    "xb3_c2_s4": "xb2_c4_s2",
    "xb3_c2_s5": "xb2_c4_s2",
    "xb3_c3_s1": "xb2_c4_s3",
    "xb3_c3_s2": "xb2_c4_s3",
    "xb3_c3_s3": "xb2_c4_s3",
    # 章级 id 也可能被直接绑定
    "bx1_c1": "bx1_c1", "bx1_c2": "bx1_c2", "bx1_c3": "bx1_c3",
    "bx1_c4": "bx2_c4", "bx1_c5": "bx3_c7",
    "bx2_c1": "bx2_c6", "bx2_c2": "bx4_c10", "bx2_c3": "bx4_c11",
    "bx2_c4": "bx2_c5", "bx2_c5": "bx2_c5",
    "xb1_c1": "xb1_c1", "xb1_c2": "xb1_c2", "xb1_c3": "xb1_c2",
    "xb2_c1": "xb3_c5", "xb2_c2": "xb3_c6",
    "xb3_c1": "xb2_c3", "xb3_c2": "xb2_c4", "xb3_c3": "xb2_c4",
    # 册级
    "bx1": "bx1", "bx2": "bx2",
    "xb1": "xb1", "xb2": "xb3", "xb3": "xb2",
}


def build_high_school_nodes() -> list[dict]:
    nodes: list[dict] = []
    for book_i, (bid, blabel, bname, chaps) in enumerate(BBAN, start=1):
        chap_ids = [f"{bid}_{cid}" for cid, _, _ in chaps]
        nodes.append({
            "id": bid,
            "name": bname,
            "parent_id": None,
            "level": 1,
            "prerequisites": [],
            "children": chap_ids,
            "book_label": blabel,
            "sort_order": book_i,
            "grade_level": "高中",
        })
        for chap_i, (cid, ctitle, sections) in enumerate(chaps, start=1):
            full_cid = f"{bid}_{cid}"
            sec_ids = [f"{full_cid}_s{i}" for i in range(1, len(sections)+1)]
            nodes.append({
                "id": full_cid,
                "name": ctitle,
                "parent_id": bid,
                "level": 2,
                "prerequisites": [],
                "children": sec_ids,
                "book_label": blabel,
                "sort_order": chap_i,
                "grade_level": "高中",
            })
            for sec_i, sec_title in enumerate(sections, start=1):
                sid = f"{full_cid}_s{sec_i}"
                nodes.append({
                    "id": sid,
                    "name": sec_title,
                    "parent_id": full_cid,
                    "level": 3,
                    "prerequisites": [],
                    "children": [],
                    "book_label": blabel,
                    "sort_order": sec_i,
                    "grade_level": "高中",
                })
    return nodes


def replace_high_school(km: dict) -> tuple[dict, set[str], set[str]]:
    old_hs_ids = {n["id"] for n in km["nodes"] if n.get("grade_level") == "高中"}
    kept = [n for n in km["nodes"] if n.get("grade_level") != "高中"]
    new_hs = build_high_school_nodes()
    new_hs_ids = {n["id"] for n in new_hs}
    km2 = dict(km)
    km2["nodes"] = kept + new_hs
    return km2, old_hs_ids, new_hs_ids


def _map_ids(id_list: list[str], new_hs_ids: set[str], old_hs_ids: set[str]) -> list[str]:
    out: list[str] = []
    for x in id_list:
        if x in new_hs_ids:  # already B 版, keep
            out.append(x)
        elif x in old_hs_ids:
            mapped = OLD_TO_NEW.get(x)
            if mapped and mapped in new_hs_ids:
                out.append(mapped)
            else:
                out.append(x)  # broken, keep for manual audit
        else:  # 初中或未知
            out.append(x)
    # 去重保序
    seen = set(); res = []
    for x in out:
        if x not in seen:
            seen.add(x); res.append(x)
    return res


def migrate_seed(new_hs_ids: set[str], old_hs_ids: set[str]) -> None:
    with open(SEED, encoding="utf-8") as f:
        data = json.load(f)
    changed = 0
    for q in data:
        old = list(q.get("knowmap_nodes") or [])
        new = _map_ids(old, new_hs_ids, old_hs_ids)
        if new != old:
            q["knowmap_nodes"] = new
            changed += 1
    with open(SEED, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"seed_questions.json migrated: {changed} rows")


def migrate_db(new_hs_ids: set[str], old_hs_ids: set[str]) -> None:
    if not os.path.exists(DB):
        print("db not found, skip")
        return
    conn = sqlite3.connect(DB)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, knowmap_nodes FROM questions")
        rows = cur.fetchall()
        changed = 0
        for qid, raw in rows:
            if not raw:
                continue
            try:
                # 存的时候是 JSON 字符串, 有时被再包一层字符串
                val = json.loads(raw)
                if isinstance(val, str):
                    val = json.loads(val)
                if not isinstance(val, list):
                    continue
                new = _map_ids(val, new_hs_ids, old_hs_ids)
                if new != val:
                    cur.execute("UPDATE questions SET knowmap_nodes=? WHERE id=?",
                                (json.dumps(new, ensure_ascii=False), qid))
                    changed += 1
            except Exception as e:
                print(f"db row {qid} parse error: {e}, raw={raw!r}")
        conn.commit()
        print(f"db questions migrated: {changed} rows")
    finally:
        conn.close()


def main() -> None:
    with open(KNOWMAP, encoding="utf-8") as f:
        km = json.load(f)
    old_hs_count = sum(1 for n in km["nodes"] if n.get("grade_level") == "高中")
    km2, old_hs_ids, new_hs_ids = replace_high_school(km)
    with open(KNOWMAP, "w", encoding="utf-8") as f:
        json.dump(km2, f, ensure_ascii=False, indent=2)
    print(f"knowmap.json rewritten: hs {old_hs_count} -> {len(new_hs_ids)} nodes (total {len(km2['nodes'])})")
    migrate_seed(new_hs_ids, old_hs_ids)
    migrate_db(new_hs_ids, old_hs_ids)


if __name__ == "__main__":
    main()