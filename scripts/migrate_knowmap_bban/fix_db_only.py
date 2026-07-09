"""生产环境专用: 单纯基于 OLD_TO_NEW 映射表, 修正 db.questions.knowmap_nodes 里残留的 A 版 id."""
import json, sqlite3, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build_bban_knowmap import OLD_TO_NEW

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "mathmind.db")
KM = os.path.join(os.path.dirname(DB), "knowmap.json")

valid = {n["id"] for n in json.load(open(KM))["nodes"]}
conn = sqlite3.connect(DB); cur = conn.cursor()
cur.execute("SELECT id, knowmap_nodes FROM questions")
rows = cur.fetchall()
changed = 0
for qid, raw in rows:
    if not raw:
        continue
    try:
        v = json.loads(raw)
        if isinstance(v, str):
            v = json.loads(v)
        if not isinstance(v, list):
            continue
        new = []
        for x in v:
            if x in valid:
                new.append(x)
            elif x in OLD_TO_NEW and OLD_TO_NEW[x] in valid:
                new.append(OLD_TO_NEW[x])
            else:
                new.append(x)  # keep, will show as unknown
        # 去重保序
        seen=set(); out=[]
        for x in new:
            if x not in seen: seen.add(x); out.append(x)
        if out != v:
            cur.execute("UPDATE questions SET knowmap_nodes=? WHERE id=?",
                        (json.dumps(out, ensure_ascii=False), qid))
            changed += 1
            print(f"{qid}: {v} -> {out}")
    except Exception as e:
        print(f"parse err {qid}: {e} raw={raw!r}")
conn.commit()
conn.close()
print(f"changed: {changed}")