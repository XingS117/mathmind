"""Match free-text knowledge point labels to fixed knowmap nodes.

The upload flow returns a list of ``knowledge_points`` from the LLM
(e.g. ``["等腰三角形的性质", "三角形中位线定理"]``). Users then have to
bind the question to one or more nodes in the 133-node knowmap tree
(e.g. ``"5.1 等腰三角形"``).

Doing the mapping manually is painful because:

- Node names are prefixed with ``"1.1 "`` style chapter numbers.
- LLM labels use verbose Chinese phrases; nodes use short textbook titles.
- One LLM label ("三角形中位线定理") often maps to a single node
  ("5.3 三角形的中位线") whose name is missing the trailing "定理".

``suggest_nodes`` returns the best matching node IDs so the frontend
can show them as clickable AI suggestions. Matching is deterministic,
in-process, and dependency-free (no extra LLM call).
"""

import re
from typing import Iterable

_CHAPTER_PREFIX = re.compile(r"^\s*(?:第[\d一二三四五六七八九十百]+[章节部分]\s*)?\d*(?:\.\d+){0,2}\s*")
_SUFFIX_NOISE = (
    "的定义", "的概念", "的性质", "的判定", "的判定与性质",
    "的应用", "的运算", "的表示", "的图像与性质", "的图像",
    "定理", "问题", "方法", "模型", "综合", "综合问题",
)
_LABEL_NOISE = ("求参数", "求值", "综合探究", "综合应用", "初步认识")

# Terms that are technically 2+ Chinese chars but carry no topical
# signal on their own; they mostly appear as suffixes of many nodes
# ("...性质", "函数的概念") so matching them alone produces junk.
_STOP_TERMS = frozenset({
    "性质", "概念", "判定", "定义", "定理", "运算", "计算",
    "图像", "表示", "应用", "问题", "关系", "方法", "变换",
    "综合",
})


def _strip_chapter_prefix(name: str) -> str:
    name = (name or "").strip()
    # Some node names look like ``"第1章 集合"`` or ``"1.1 集合的概念"`` or
    # ``"第一章 三角函数"``. Strip both formats so the head noun lines up
    # with LLM free-text labels.
    m = _CHAPTER_PREFIX.match(name)
    if m and m.end() > 0:
        name = name[m.end():].strip()
    return name


def _core_terms(text: str) -> list[str]:
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
    # "三角形中位线" and "三角形的中位线" match.
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


_PARTICLES = ("的", "之", "与", "和", "或")


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
    for label in labels:
        terms = _core_terms(label)
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
