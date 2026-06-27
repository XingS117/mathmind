import json, os, logging
from typing import Optional

logger = logging.getLogger(__name__)
_nodes: list[dict] = []
_nodes_by_id: dict[str, dict] = {}

def load_knowmap():
    global _nodes, _nodes_by_id
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "knowmap.json")
    if not os.path.exists(path):
        logger.warning(f"KnowMap not found: {path}")
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _nodes = data["nodes"]
    _nodes_by_id = {n["id"]: n for n in _nodes}
    logger.info(f"KnowMap loaded: {len(_nodes)} nodes")

def get_tree(grade_level: str = "") -> list[dict]:
    if not _nodes:
        load_knowmap()
    if grade_level:
        return [n for n in _nodes if n.get("grade_level") == grade_level]
    return _nodes

def get_node(node_id: str) -> Optional[dict]:
    if not _nodes:
        load_knowmap()
    return _nodes_by_id.get(node_id)

def get_subtree(node_id: str, grade_level: str = "") -> list[dict]:
    node = get_node(node_id)
    if not node:
        return []
    result = [node]
    for child_id in node.get("children", []):
        child = get_node(child_id)
        if child:
            if grade_level and child.get("grade_level") != grade_level:
                continue
            result.extend(get_subtree(child_id, grade_level))
    return result

def get_leaf_nodes(node_id: str) -> list[str]:
    leaves = []
    for n in get_subtree(node_id):
        if n["level"] == 3 or not n.get("children"):
            leaves.append(n["id"])
    return leaves