import json, logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.question import Question
from backend.services.auth_service import get_user_id
from backend.services.knowmap_service import get_tree, get_node, get_subtree

logger = logging.getLogger(__name__)
router = APIRouter(tags=["knowmap"])

def _parse_json(val):
    """Parse a JSON string to Python object, handling SQLAlchemy JSON column quirks."""
    if val is None: return []
    if isinstance(val, (list, dict)): return val
    if isinstance(val, str):
        try: return json.loads(val)
        except: return []
    return []


def _visible_questions(request: Request, db: DBSession):
    """Return questions the current user is allowed to see: their own + seed
    (u_default owned questions with source_label starting with 'seed').

    For logged-in users this hides other users' uploads; guests only see
    u_default's own questions (which include seed data).
    """
    uid = get_user_id(request, db=db)
    q = db.query(Question).filter(Question.status == "complete")
    if uid == "u_default":
        q = q.filter(Question.user_id == "u_default")
    else:
        q = q.filter(Question.user_id.in_([uid, "u_default"]))
    return q


@router.get("/knowmap/tree")
def knowmap_tree(request: Request, grade: str = Query(""), db: DBSession = Depends(get_db)):
    nodes = get_tree(grade)
    node_map = {n["id"]: n for n in nodes}
    raw_counts = {}
    for q in _visible_questions(request, db).all():
        for nid in _parse_json(q.knowmap_nodes):
            if nid in node_map:
                raw_counts[nid] = raw_counts.get(nid, 0) + 1
    final = dict(raw_counts)
    for nid, cnt in raw_counts.items():
        pid = node_map[nid].get("parent_id")
        seen = {nid}
        while pid and pid in node_map and pid not in seen:
            seen.add(pid)
            final[pid] = final.get(pid, 0) + cnt
            pid = node_map[pid].get("parent_id")
    return {"nodes": [dict(n) for n in nodes], "question_counts": final}

@router.get("/knowmap/summary")
def knowmap_summary(request: Request, grade: str = Query(""), db: DBSession = Depends(get_db)):
    tree = get_tree(grade)
    l1 = [n for n in tree if n["level"] == 1]
    total = 0
    per_book = {}
    visible = list(_visible_questions(request, db).all())
    for book in l1:
        desc = set()
        def collect(nid):
            desc.add(nid)
            n = get_node(nid)
            if n:
                for c in n.get("children", []): collect(c)
        collect(book["id"])
        cnt = 0
        for q in visible:
            if any(n in desc for n in _parse_json(q.knowmap_nodes)):
                cnt += 1
        total += cnt
        per_book[book["name"]] = {"count": cnt, "children": len(book.get("children", []))}
    return {"grade": grade or "全部", "total_questions": total, "total_nodes": len(tree), "per_book": per_book}

@router.get("/knowmap/nodes/{node_id}/questions")
def node_questions(node_id: str, request: Request, grade: str = Query(""), db: DBSession = Depends(get_db)):
    subtree = get_subtree(node_id)
    desc_ids = set(n["id"] for n in subtree)
    result = []
    for q in _visible_questions(request, db).order_by(Question.created_at.desc()).all():
        if any(n in desc_ids for n in _parse_json(q.knowmap_nodes)):
            result.append({
                "id": q.id,
                "text": (q.text or "")[:80],
                "question_type": q.question_type or "题目",
                "difficulty": q.difficulty or 1,
                "source_label": q.source_label or "好题",
                "knowledge_points": _parse_json(q.knowledge_points),
            })
    return {"questions": result}

@router.get("/knowmap/nodes/{node_id}")
def knowmap_node(node_id: str):
    node = get_node(node_id)
    if not node: raise HTTPException(404, "Node not found")
    return node

@router.get("/knowmap/nodes/{node_id}/subtree")
def knowmap_subtree(node_id: str):
    return {"nodes": get_subtree(node_id)}
