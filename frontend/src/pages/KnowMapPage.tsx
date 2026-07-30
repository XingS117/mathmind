import { useState, useEffect, useMemo } from "react";
import { getKnowMapTree, getNodeQuestions } from "../services/api";
import { findBestWeakPointNode } from "../components/knowmapPicker.js";

interface N { id: string; name: string; level: number; parent_id: string|null; children: string[]; grade_level: string; grade?: string; }
interface Props { grade: string; focusWeakPoint?: string; onSelectQuestion: (qid: string) => void; }

const C: Record<string, string> = {
  "必修第一册":"#dc2626","必修第二册":"#ea580c",
  "选择性必修第一册":"#2563eb","选择性必修第二册":"#16a34a","选择性必修第三册":"#9333ea",
  "七年级上册":"#0891b2","七年级下册":"#0d9488",
  "八年级上册":"#7c3aed","八年级下册":"#6366f1",
  "九年级上册":"#db2777","九年级下册":"#c026d3",
};

export default function KnowMapPage({ grade, focusWeakPoint = "", onSelectQuestion }: Props) {
  const [tree, setTree] = useState<N[]>([]);
  const [counts, setCounts] = useState<Record<string,number>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string | null>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focusMessage, setFocusMessage] = useState("");

  // Load tree
  useEffect(() => {
    getKnowMapTree(grade).then(d => {
      const nodes = d.nodes || [];
      setTree(nodes);
      setCounts(d.question_counts || {});
      setExpanded(new Set(nodes.filter((n:N) => n.level === 1).map((n:N) => n.id)));
      setSelected(null); setQuestions([]); setError(null);
    }).catch(() => setError("加载图谱失败"));
  }, [grade]);

  // Load questions when selected changes
  useEffect(() => {
    if (!selected) { setQuestions([]); return; }
    setLoading(true); setError(null);
    getNodeQuestions(selected, grade).then(d => {
      const qs = d.questions || [];
      setQuestions(qs);
      setLoading(false);
    }).catch(() => {
      setLoading(false); setError("加载题目失败");
    });
  }, [selected, grade]);

  useEffect(() => {
    if (!focusWeakPoint || tree.length === 0) return;
    const node = findBestWeakPointNode(tree, focusWeakPoint);
    if (!node) {
      setFocusMessage(`正在查看薄弱点：${focusWeakPoint}`);
      return;
    }
    setSelected(node.id);
    setFocusMessage(`已定位：${focusWeakPoint}`);
    setExpanded(prev => {
      const next = new Set(prev);
      let parentId = node.parent_id;
      while (parentId) {
        next.add(parentId);
        parentId = tree.find(n => n.id === parentId)?.parent_id || null;
      }
      return next;
    });
  }, [focusWeakPoint, tree]);

  const selectedNode = tree.find(n => n.id === selected);
  const qc = (id: string) => counts[id] || 0;
  const perBook = useMemo(() => {
    const books = tree.filter(n => n.level === 1);
    const r: Record<string,number> = {};
    for (const b of books) {
      const ids = new Set<string>();
      const collect = (nid: string) => { ids.add(nid); const n = tree.find(x => x.id === nid); if (n) for (const c of n.children) collect(c); };
      collect(b.id);
      let t = 0; for (const id of ids) t += counts[id] || 0;
      if (t > 0) r[b.name] = t;
    }
    return r;
  }, [tree, counts]);
  const totalQ = useMemo(() => Object.values(counts).reduce((a,b)=>a+b,0), [counts]);

  const toggle = (id: string) => setExpanded(p => { const n = new Set(p); n.has(id)?n.delete(id):n.add(id); return n; });
  const descend = (pid: string) => tree.filter(n => n.parent_id === pid).sort((a,b) => a.id.localeCompare(b.id));

  const rn = (node: N, depth: number) => {
    const open = expanded.has(node.id);
    const hk = node.children?.length > 0;
    const cnt = qc(node.id);
    const color = node.level === 1 ? (C[node.name] || "#2563eb") : undefined;
    return (
      <div key={node.id}>
        <div onClick={() => { if (hk) toggle(node.id); setSelected(node.id); }}
          style={{ padding: "5px 8px", marginLeft: depth * 14, cursor: "pointer", borderRadius: 4,
            fontSize: node.level === 1 ? 13 : node.level === 2 ? 12 : 11,
            fontWeight: node.level <= 2 ? 600 : 400,
            background: selected === node.id ? (color ? color + "18" : "#eff6ff") : "transparent",
            color: color || (selected === node.id ? "#2563eb" : "#0f172a"),
            borderLeft: node.level === 1 ? `3px solid ${color || "#2563eb"}` : "3px solid transparent",
            display: "flex", alignItems: "center", gap: 3, transition: "background 0.1s" }}>
          <span style={{ fontSize: 9, color: "#94a3b8", width: 10, textAlign: "center" }}>{hk ? (open ? "▾" : "▸") : "·"}</span>
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
          {cnt > 0 && <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 999, background: color || "#2563eb", color: "#fff", fontWeight: 600, minWidth: 16, textAlign: "center" }}>{cnt}</span>}
        </div>
        {open && hk && descend(node.id).map(c => rn(c, depth + 1))}
      </div>
    );
  };

  if (tree.length === 0) return <div style={{ textAlign:"center", padding:60, color:"#94a3b8" }}>该学段暂无数据</div>;

  return (
    <div>
      {/* Summary */}
      {totalQ > 0 && (
        <div style={{ marginBottom: 10, padding: "8px 12px", background: "#fff", borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12, display: "flex", flexWrap: "wrap", gap: "2px 14px" }}>
          <span style={{ fontWeight: 600, color: "#0f172a" }}>共 {totalQ} 题</span>
          {Object.entries(perBook).map(([k, v]) => (
            <span key={k} style={{ color: C[k] || "#475569" }}>{k.replace("选择性必修","选必").replace("册","")} {v}题</span>
          ))}
        </div>
      )}

      {focusMessage && (
        <div style={{ marginBottom: 10, padding: "8px 12px", background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.14)", borderRadius: 10, fontSize: 12, color: "#991b1b", display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
          <span>{focusMessage}</span>
          <span style={{ color: "#64748b" }}>{selected ? "右侧已显示相关题目" : "未匹配到图谱节点，可从左侧选择相关章节"}</span>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, minHeight: "60vh" }}>
        {/* Tree */}
        <div style={{ flex: 1, border: "1px solid #e2e8f0", borderRadius: 10, padding: 4, overflowY: "auto", maxHeight: "68vh", background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          {tree.filter(n => n.level === 1).map(b => rn(b, 0))}
        </div>
        {/* Detail */}
        <div style={{ flex: 1, border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, overflowY: "auto", maxHeight: "68vh", background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          {selectedNode ? (
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, color: C[selectedNode.name] || "#0f172a" }}>{selectedNode.name}</h3>
              <p style={{ fontSize: 11, color: "#94a3b8", marginBottom: 12 }}>
                {tree.find(n => n.id === selectedNode.parent_id)?.name || ""}{selectedNode.grade_level ? ` · ${selectedNode.grade_level}` : ""}{qc(selectedNode.id) > 0 ? ` · ${qc(selectedNode.id)} 题` : ""}
              </p>
              {error && <p style={{ fontSize: 12, color: "#ef4444" }}>{error}</p>}
              {loading ? <p style={{ fontSize: 12, color: "#94a3b8" }}>加载中...</p> : (
                questions.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {questions.map((q: any) => (
                      <div key={q.id} onClick={() => onSelectQuestion(q.id)}
                        style={{ padding: "10px 12px", background: "#f8fafc", borderRadius: 8, cursor: "pointer", border: "1px solid #e2e8f0" }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.borderColor = "#3b82f6"}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.borderColor = "#e2e8f0"}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 4, background: "#eff6ff", color: "#2563eb", fontWeight: 500 }}>{q.question_type || "题目"}</span>
                          <span style={{ fontSize: 11, color: "#94a3b8" }}>{q.difficulty ? `${q.difficulty}/5` : ""}</span>
                        </div>
                        <p style={{ fontSize: 12, color: "#0f172a", margin: 0 }}>{q.text || q.id}</p>
                        <div style={{ marginTop: 4, display: "flex", gap: 4 }}>
                          {(q.knowledge_points || []).slice(0, 3).map((kp: string, i: number) => (
                            <span key={i} style={{ fontSize: 10, color: "#64748b" }}>#{kp}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <p style={{ fontSize: 12, color: "#94a3b8", textAlign: "center", padding: 16 }}>该节点下暂无题目</p>
              )}
            </div>
          ) : (
            <div style={{ textAlign: "center", paddingTop: 60, color: "#94a3b8", fontSize: 13 }}><p>选择一个知识点查看题目</p></div>
          )}
        </div>
      </div>
    </div>
  );
}
