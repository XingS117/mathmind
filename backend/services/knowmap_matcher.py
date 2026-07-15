"""Match free-text knowledge point labels to fixed knowmap nodes.

The upload flow returns a list of ``knowledge_points`` from the LLM
(e.g. ``["等腰三角形的性质", "三角形中位线定理"]``). Users then have to
bind the question to one or more nodes in the knowmap tree
(e.g. ``"5.1 等腰三角形"``).

Doing the mapping manually is painful because:

- Node names are prefixed with ``"1.1 "`` style chapter numbers.
- LLM labels use verbose Chinese phrases; nodes use short textbook titles.
- One LLM label ("三角形中位线定理") often maps to a single node
  ("5.3 三角形的中位线") whose name is missing the trailing "定理".
- 人教 B 版 (2019) 使用「XX 及其方程」「随机变量」「简单几何体」等
  与教学口径不完全一致的节名, LLM 常输出「XX 的标准方程」「离散型
  随机变量的分布列」「三棱锥的体积」等等, 需要一层别名映射。

``suggest_nodes`` returns the best matching node IDs so the frontend
can show them as clickable AI suggestions. Matching is deterministic,
in-process, and dependency-free (no extra LLM call).
"""

import re
from typing import Iterable

_CHAPTER_PREFIX = re.compile(r"^\s*(?:第[\d一二三四五六七八九十百]+[章节部分]\s*)?\d*(?:\.\d+){0,2}\s*")
_SUFFIX_NOISE = (
    "的标准方程", "的一般方程", "的参数方程", "的极坐标方程",
    "的方程", "及其方程",
    "的定义", "的概念", "的性质", "的判定", "的判定与性质",
    "的应用", "的运算", "的四则运算", "的表示", "的表示方法",
    "的图像与性质", "的图像和性质", "的图像", "的图象",
    "求和", "求和公式", "求解", "通项", "通项公式",
    "定理", "问题", "方法", "模型", "综合", "综合问题",
)
_LABEL_NOISE = ("求参数", "求值", "综合探究", "综合应用", "初步认识",
                "简单应用", "实际应用", "实际问题", "应用问题")

# Terms that are technically 2+ Chinese chars but carry no topical
# signal on their own; they mostly appear as suffixes of many nodes
# ("...性质", "函数的概念") so matching them alone produces junk.
_STOP_TERMS = frozenset({
    "性质", "概念", "判定", "定义", "定理", "运算", "计算",
    "图像", "图象", "表示", "应用", "问题", "关系", "方法", "变换",
    "综合", "求和", "通项",
})


# --- 别名/等价术语表 (人教 B 版目录 <-> 教学口径常见说法) --------------------
#
# Key   : LLM/教学口径 常见知识点关键词 (子串, 大小写敏感)
# Value : 该关键词等价映射到的 "教材节名核心词" 列表
#          -> 匹配时会用这些核心词去跟 knowmap 节点名对比
#
# 例:  "椭圆的标准方程" 里含 "椭圆" -> 映射到 "椭圆及其方程" 里的 "椭圆"
#      不用改这里, 是被 _SUFFIX_NOISE 剥掉「的标准方程」之后自然匹配到的;
#      本表主要处理无法通过纯剥后缀达成对齐的 case.
_ALIAS_MAP: dict[str, tuple[str, ...]] = {
    # -- B 版「常用逻辑用语」章下没有细节节, 教学常见术语需回落到章 --
    "充分条件": ("常用逻辑用语",),
    "必要条件": ("常用逻辑用语",),
    "充要条件": ("常用逻辑用语",),
    "全称量词": ("常用逻辑用语",),
    "存在量词": ("常用逻辑用语",),
    "命题": ("常用逻辑用语",),
    "逻辑联结词": ("常用逻辑用语",),
    # -- 立体几何 (B 版 必修四 11.x 三视图/表面积/体积统统在「11.1 空间几何体」
    #    和「11.6 简单几何体的再认识」两个节内) --
    "三视图": ("空间几何体",),
    "直观图": ("立体图形", "空间几何体"),
    "三棱锥": ("空间几何体", "简单几何体"),
    "四棱锥": ("空间几何体", "简单几何体"),
    "多面体": ("空间几何体", "简单几何体"),
    "棱柱": ("空间几何体", "简单几何体"),
    "棱锥": ("空间几何体", "简单几何体"),
    "圆柱": ("空间几何体", "简单几何体"),
    "圆锥": ("空间几何体", "简单几何体"),
    "球": ("空间几何体", "简单几何体"),
    "表面积": ("简单几何体", "空间几何体"),
    "体积": ("简单几何体", "空间几何体"),
    # -- 圆锥曲线各要素回落到 XX及其方程 --
    "离心率": ("椭圆", "双曲线", "抛物线"),
    "渐近线": ("双曲线",),
    "焦点弦": ("椭圆", "双曲线", "抛物线"),
    "准线": ("抛物线",),
    "焦半径": ("椭圆", "双曲线", "抛物线"),
    # -- 直线与圆 --
    "斜率": ("直线",),
    "倾斜角": ("直线",),
    "两点距离": ("直线",),
    "点到直线距离": ("直线",),
    # -- 概率与统计 B 版把分布列/期望/方差/正态分布统统放进「4.2 随机变量」--
    "分布列": ("随机变量",),
    "期望": ("随机变量",),
    "方差": ("随机变量",),
    "正态分布": ("随机变量",),
    "二项分布": ("随机变量",),
    "超几何分布": ("随机变量",),
    "离散型随机变量": ("随机变量",),
    "条件概率": ("条件概率", "随机变量"),
    "独立事件": ("条件概率", "独立性"),
    # -- 数列 --
    "错位相减": ("等比数列",),
    "裂项相消": ("数列",),
    "数列求和": ("数列",),
    # -- 三角 --
    "正弦定理": ("正弦定理", "余弦定理", "解三角形"),
    "余弦定理": ("正弦定理", "余弦定理", "解三角形"),
    "解三角形": ("正弦定理", "余弦定理", "解三角形"),
    "诱导公式": ("三角函数",),
    "和差角": ("三角恒等变换",),
    "二倍角": ("三角恒等变换",),
    "辅助角": ("三角恒等变换",),
    # -- 导数 --
    "切线方程": ("导数",),
    "极值": ("导数", "函数中的应用", "研究函数"),
    "单调区间": ("导数", "研究函数"),
    # -- 向量 --
    "数量积": ("数量积", "空间向量"),
    "点乘": ("数量积",),
    "投影向量": ("数量积",),
    "二面角": ("空间向量", "立体几何"),
    "法向量": ("空间向量",),
    # -- 平面向量 --
    "共线向量": ("平面向量",),
    "向量基本定理": ("向量基本定理",),
    # -- 复数 --
    "复数的模": ("复数",),
    "复数的辐角": ("复数",),
    "复数的三角形式": ("复数",),
}


def _strip_chapter_prefix(name: str) -> str:
    name = (name or "").strip()
    # Some node names look like ``"第1章 集合"`` or ``"1.1 集合的概念"`` or
    # ``"第一章 三角函数"``. Strip both formats so the head noun lines up
    # with LLM free-text labels.
    m = _CHAPTER_PREFIX.match(name)
    if m and m.end() > 0:
        name = name[m.end():].strip()
    return name


def _core_terms(text: str, joined_all: str | None = None) -> list[str]:
    """Split a label like "等腰三角形的性质" into core searchable terms.

    Removes common trailing modifiers ("的性质"/"定理"/...) so the head
    noun ("等腰三角形") can still line up with the shorter node name.
    """
    text = (text or "").strip()
    if not text:
        return []
    for noise in _LABEL_NOISE:
        if text.endswith(noise) and len(text) > len(noise):
            text = text[: -len(noise)].strip()
    parts = {text}
    core = text
    changed = True
    while changed:
        changed = False
        for suf in _SUFFIX_NOISE:
            if core.endswith(suf) and len(core) > len(suf):
                core = core[: -len(suf)]
                parts.add(core)
                changed = True
                break
    for splitter in ("与", "和", "、", ","):
        for chunk in text.split(splitter):
            chunk = chunk.strip()
            if chunk and chunk != text:
                parts.add(chunk)
    # 别名扩展: 命中的关键词额外把 alias 目标核心词也当作 term 加入.
    # 若 label 已含某个 alias 目标 (说明用户已明确到该实体, 例如
    # "椭圆的标准方程" 含 "椭圆"), 则只保留那一个目标, 避免把兄弟节点
    # (双曲线/抛物线) 也拉进来.
    # 别名扩展 (在整份 labels 联合体上判断"显式头名词"):
    # - 若整份 kp 列表里已明确出现某个 alias 目标 (例如 "椭圆"), 则只保留
    #   显式出现过的目标, 避免"椭圆的标准方程 + 焦点弦长"把双曲线/抛物线
    #   一起拉进来.
    scope = joined_all if joined_all is not None else text
    for keyword, aliases in _ALIAS_MAP.items():
        if keyword not in text:
            continue
        explicit_in_scope = [a for a in aliases if a in scope]
        for alias in (explicit_in_scope if explicit_in_scope else aliases):
            parts.add(alias)
    # Drop 1-char noise terms produced by aggressive stripping and any
    # generic stop-words that would otherwise match every node with
    # the same suffix ("性质", "概念", ...).
    return [p for p in parts if len(p) >= 2 and p not in _STOP_TERMS]


def _score_pair(label: str, node_name: str) -> int:
    """Score how well a free-text label matches a node's stripped name.

    Higher is better. 0 means "no signal".
    """
    if not label or not node_name or len(label) < 2 or len(node_name) < 2:
        return 0
    if label == node_name:
        return 100
    if label in node_name:
        return 85 + min(len(label), 10)
    if node_name in label:
        return 75 + min(len(node_name), 10)
    # Compare with common connective particles removed so
    # "三角形中位线" and "三角形的中位线" match; also so
    # "椭圆及其方程" and "椭圆的方程" match.
    label_c = _compact(label)
    node_c = _compact(node_name)
    if label_c and node_c:
        if label_c == node_c:
            return 95
        if label_c in node_c:
            return 82 + min(len(label_c), 10)
        if node_c in label_c:
            return 72 + min(len(node_c), 10)
    return 0


_PARTICLES = ("的", "之", "与", "和", "或", "及其", "及", "对")


def _compact(text: str) -> str:
    for p in _PARTICLES:
        text = text.replace(p, "")
    return text


def suggest_nodes(
    knowledge_points: Iterable[str],
    nodes: list[dict],
    limit: int = 5,
    min_score: int = 55,
) -> list[str]:
    """Suggest up to ``limit`` node IDs for the given free-text labels.

    Returns node IDs ordered by descending match score, deduplicated,
    only including matches whose score meets ``min_score`` so we do
    not surface random low-signal suggestions.
    """
    labels = [str(kp).strip() for kp in (knowledge_points or []) if str(kp).strip()]
    if not labels or not nodes:
        return []

    # Only leaf-like nodes are useful bindings; skip the top-level
    # textbook rows (level 1) since binding to "必修一" is meaningless.
    candidate_nodes = [n for n in nodes if int(n.get("level", 0)) >= 2]

    # (score, level) per node so we can prefer more specific matches
    # (level 3 leaves) over broad chapters when both fire.
    best: dict[str, tuple[int, int]] = {}
    # 显式头名词: 若整份 kp 列表里已明确出现某个 alias 目标 (如 "椭圆"),
    # 则 alias 展开只保留该目标, 不把兄弟节点拉进来.
    joined_all = "\u3000".join(labels)
    for label in labels:
        terms = _core_terms(label, joined_all=joined_all)
        for node in candidate_nodes:
            node_name = _strip_chapter_prefix(node.get("name", ""))
            if not node_name:
                continue
            score = 0
            for term in terms:
                score = max(score, _score_pair(term, node_name))
            if score >= min_score:
                nid = node["id"]
                lvl = int(node.get("level", 0))
                prev = best.get(nid)
                if prev is None or score > prev[0]:
                    best[nid] = (score, lvl)

    # Rank by score desc, then prefer deeper (more specific) nodes,
    # then node id for stability.
    ranked = sorted(
        best.items(),
        key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]),
    )
    return [nid for nid, _score in ranked[:limit]]