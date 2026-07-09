import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { analyzeQuestion, confirmQuestion, getKnowMapTree, getOcrHealth, type AnalysisResult } from "../services/api";
import { browseChildren, browseTopLevelBooks, filterKnowMapNodes, formatNodePath } from "./knowmapPicker.js";

interface Props {
  grade?: string;
  onConfirm?: (qid: string) => void;
  onImage: (file: File) => void;
  loading: boolean;
}

interface ReviewDraft extends AnalysisResult {
  final_answer?: string;
  solution_text?: string;
  knowmap_nodes?: string[];
}

interface KnowMapNode {
  id: string;
  name: string;
  level: number;
  parent_id: string | null;
  children?: string[];
}

const questionTypes = ["选择题", "填空题", "计算题", "解答题", "证明题", "几何题"];

export default function ImageUpload({ grade = "高中", onConfirm }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [elapsed, setElapsed] = useState(0); // seconds
  const [ocrHealth, setOcrHealth] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<ReviewDraft | null>(null);
  const [knowmapNodes, setKnowmapNodes] = useState<KnowMapNode[]>([]);
  const [nodeQuery, setNodeQuery] = useState("");
  const [browseParentId, setBrowseParentId] = useState<string | null>(null);

  useEffect(() => {
    getKnowMapTree(grade).then(d => {
      setKnowmapNodes(d.nodes || []);
    }).catch(() => setKnowmapNodes([]));
  }, [grade]);

  const nodeMatches = useMemo(() => {
    return filterKnowMapNodes(knowmapNodes, nodeQuery, result?.knowmap_nodes || [], 6);
  }, [knowmapNodes, nodeQuery, result?.knowmap_nodes]);

  const selectedNodes = useMemo(() => {
    const ids = new Set(result?.knowmap_nodes || []);
    return knowmapNodes.filter(n => ids.has(n.id));
  }, [knowmapNodes, result?.knowmap_nodes]);

  const suggestedNodes = useMemo(() => {
    const suggested = result?.suggested_nodes || [];
    if (suggested.length === 0) return [];
    const bySet = new Set(result?.knowmap_nodes || []);
    const byId = new Map(knowmapNodes.map(n => [n.id, n] as const));
    return suggested
      .map(id => byId.get(id))
      .filter((n): n is KnowMapNode => !!n && !bySet.has(n.id));
  }, [result?.suggested_nodes, result?.knowmap_nodes, knowmapNodes]);

  const addAllSuggested = () => {
    if (!result || suggestedNodes.length === 0) return;
    const merged = Array.from(new Set([...(result.knowmap_nodes || []), ...suggestedNodes.map(n => n.id)]));
    updateResult({ knowmap_nodes: merged });
  };

  const updateResult = (patch: Partial<ReviewDraft>) => {
    setResult(prev => prev ? { ...prev, ...patch } : prev);
  };

  const handleFiles = useCallback((fileList: FileList) => {
    previews.forEach(url => URL.revokeObjectURL(url));
    const arr = Array.from(fileList);
    if (arr.length === 0) return;
    setFiles(arr);
    setPreviews(arr.map(f => URL.createObjectURL(f)));
    setResult(null);
  }, [previews]);

  const reset = () => {
    previews.forEach(url => URL.revokeObjectURL(url));
    setFiles([]);
    setPreviews([]);
    setResult(null);
    setConfirming(false);
  };

  const analyze = async () => {
    if (files.length === 0) return;
    setAnalyzing(true);
    setElapsed(0);
    setOcrHealth("");
    setResult(null);

    const controller = new AbortController();
    abortRef.current = controller;
    // 硬上限 6 分钟 (单张 60-90s * 最多 4 张 + LLM)
    const hardTimeout = window.setTimeout(() => controller.abort(), 360_000);
    const tick = window.setInterval(() => setElapsed(s => s + 1), 1000);
    const healthPoll = window.setInterval(() => {
      getOcrHealth().then(h => setOcrHealth(h.status)).catch(() => {});
    }, 5000);

    try {
      const d = await analyzeQuestion(files, controller.signal);
      // AI 建议的图谱节点默认全部勾选 (P1-UX-KP-01):
      // 大部分情况下 matcher 命中即正确, 让用户看到"已选"更快;
      // 若不满意可以点标签上的 × 撤销.
      const auto = Array.isArray(d.suggested_nodes) ? d.suggested_nodes.slice(0, 3) : [];
      setResult({
        ...d,
        key_insight: d.key_insight || "",
        final_answer: "",
        solution_text: "",
        knowmap_nodes: auto,
      });
    } catch (err: unknown) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      setResult({
        success: false,
        error: aborted ? "识别超时(超过 6 分钟)" : "网络错误",
        suggestion: aborted
          ? "OCR 未能在预期时间内完成,请减少图片数量后重试,或先手动录入题干"
          : "请检查后端是否运行 (http://127.0.0.1:8000),或改为手动录入",
      });
    } finally {
      window.clearTimeout(hardTimeout);
      window.clearInterval(tick);
      window.clearInterval(healthPoll);
      abortRef.current = null;
      setAnalyzing(false);
    }
  };

  const cancelAnalyze = () => {
    abortRef.current?.abort();
  };

  const formatElapsed = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const confirm = async () => {
    if (!result || !result.success || !result.text?.trim()) return;
    setConfirming(true);
    try {
      const d = await confirmQuestion({
        text: result.text.trim(),
        question_type: result.question_type || "计算题",
        difficulty: result.difficulty || 2,
        knowledge_points: result.knowledge_points || [],
        has_diagram: result.has_diagram || false,
        raw_ocr_text: result.raw_ocr_text || "",
        final_answer: result.final_answer || "",
        solution_text: result.solution_text || "",
        key_insight: result.key_insight || "",
        knowmap_nodes: result.knowmap_nodes || [],
        analysis_source: result.source || "manual",
        analysis_confidence: result.confidence || 0,
        needs_human_review: false,
      });
      if (d.question_id && onConfirm) onConfirm(d.question_id);
    } catch {
      updateResult({ error: "入库失败", suggestion: "请稍后重试，或检查后端服务是否运行。" });
    } finally {
      setConfirming(false);
    }
  };

  const confidence = result?.confidence ?? 0;
  const lowConfidence = result?.success && confidence < 70;
  const addNode = (selectedNodeId: string) => {
    if (!selectedNodeId || !result) return;
    const current = result.knowmap_nodes || [];
    if (current.includes(selectedNodeId)) return;
    updateResult({ knowmap_nodes: [...current, selectedNodeId] });
    setNodeQuery("");
    setBrowseParentId(null);
  };
  const removeNode = (id: string) => {
    if (!result) return;
    updateResult({ knowmap_nodes: (result.knowmap_nodes || []).filter(n => n !== id) });
  };

  return (
    <div>
      <input ref={inputRef} type="file" accept="image/*" multiple hidden
        onChange={e => e.target.files && handleFiles(e.target.files)} />

      <div onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); e.dataTransfer.files && handleFiles(e.dataTransfer.files); }}
        onClick={() => !analyzing && !result && inputRef.current?.click()}
        style={{ border: `2px dashed ${dragOver ? "#3b82f6" : "#e2e8f0"}`, borderRadius: 12, padding: 32,
          textAlign: "center", cursor: result ? "default" : "pointer",
          background: dragOver ? "#eff6ff" : "#fafafa", transition: "all 0.2s", opacity: analyzing ? 0.5 : 1 }}>
        {previews.length > 0 ? (
          <p style={{ fontSize: 14, color: "#64748b", margin: 0 }}>
            已选择 {previews.length} 张图片{!result && "，点击「解析入库」开始分析"}
          </p>
        ) : (
          <>
            <p style={{ fontSize: 14, color: "#64748b", margin: "0 0 4px" }}>点击或拖拽题目图片到这里</p>
            <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>支持多张图片（如解析较长分多页截图）</p>
          </>
        )}
      </div>

      {previews.length > 0 && !result && (
        <div style={{ display: "flex", gap: 8, marginTop: 12, overflowX: "auto" }}>
          {previews.map((p, i) => (
            <div key={i} style={{ position: "relative", flexShrink: 0 }}>
              <img src={p} alt={`${i + 1}`} style={{ height: 120, borderRadius: 8, border: "1px solid #e2e8f0" }} />
              <span style={{ position: "absolute", top: 4, left: 4, background: "rgba(0,0,0,0.5)", color: "#fff", fontSize: 11, padding: "1px 6px", borderRadius: 4 }}>{i + 1}</span>
            </div>
          ))}
        </div>
      )}

      {files.length > 0 && !result && !analyzing && (
        <button onClick={analyze}
          style={{ marginTop: 12, padding: "10px 28px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 14, fontWeight: 500, width: "100%" }}>
          解析入库
        </button>
      )}

      {analyzing && (() => {
        const perImage = 75; // seconds per image (empirically 60-90s)
        const budget = files.length * perImage + 10;
        const pct = Math.min(99, Math.floor((elapsed / budget) * 100));
        const remain = Math.max(0, budget - elapsed);
        const ocrLabel =
          ocrHealth === "ready" ? "OCR 就绪"
          : ocrHealth === "initializing" ? "OCR 正在启动"
          : ocrHealth === "failed" ? "OCR 启动失败,将走 Mock"
          : "OCR 状态检测中";
        return (
          <div style={{ marginTop: 12, padding: 14, border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--card)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 8, color: "var(--text)" }}>
              <span>正在识别 {files.length} 张图片...</span>
              <span style={{ fontVariantNumeric: "tabular-nums" }}>{formatElapsed(elapsed)} / 约 {formatElapsed(budget)}</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: "var(--border)", overflow: "hidden", marginBottom: 8 }}>
              <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand)", transition: "width 0.6s linear" }} />
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
              {ocrLabel} · 预计还需 {formatElapsed(remain)} · 请勿关闭页面
            </div>
            <button type="button" onClick={cancelAnalyze}
              style={{ fontSize: 12, padding: "6px 12px", background: "transparent", color: "var(--text-muted)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer" }}>
              取消识别
            </button>
          </div>
        );
      })()}

      {result && !analyzing && (
        <div style={{ marginTop: 12, padding: 16, borderRadius: "var(--radius)", border: "1px solid var(--border)", background: "var(--card)" }}>
          {result.success ? (
            <>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 10 }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", marginBottom: 2 }}>入库前校对</p>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                    来源 {result.source || "manual"} · 置信度 {confidence}%
                  </p>
                </div>
                <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 999,
                  background: lowConfidence ? "rgba(245,158,11,0.12)" : "rgba(16,185,129,0.1)",
                  color: lowConfidence ? "var(--warning)" : "var(--success)", fontWeight: 600 }}>
                  {lowConfidence ? "建议仔细校对" : "仍需人工确认"}
                </span>
              </div>

              {result.suggestion && (
                <p style={{ fontSize: 12, color: "var(--warning)", background: "rgba(245,158,11,0.08)", padding: "8px 10px", borderRadius: 6, marginBottom: 10 }}>
                  {result.suggestion}
                </p>
              )}

              <label style={labelStyle}>题目内容</label>
              <textarea value={result.text || ""} onChange={e => updateResult({ text: e.target.value })} rows={5}
                placeholder="在此输入或校对完整题目内容..."
                style={textareaStyle} />

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
                <div>
                  <label style={labelStyle}>题型</label>
                  <select value={result.question_type || "计算题"} onChange={e => updateResult({ question_type: e.target.value })}
                    style={inputStyle}>
                    {questionTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>难度 1-5</label>
                  <input type="number" min={1} max={5} value={result.difficulty || 2}
                    onChange={e => updateResult({ difficulty: Number(e.target.value) })}
                    style={inputStyle} />
                </div>
              </div>

              <label style={{ ...labelStyle, marginTop: 10 }}>知识点</label>
              <input value={(result.knowledge_points || []).join("、")}
                onChange={e => updateResult({ knowledge_points: e.target.value.split(/[、,，]/).map(s => s.trim()).filter(Boolean) })}
                placeholder="例如：相似三角形、圆的切线"
                style={inputStyle} />

              <label style={{ ...labelStyle, marginTop: 10 }}>图谱节点</label>
              <div>
                {suggestedNodes.length > 0 && (
                  <div style={{ marginBottom: 10, padding: 10, border: "1px solid rgba(30,64,175,0.15)", background: "var(--brand-bg)", borderRadius: "var(--radius-sm)" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)" }}>
                        💡 还没被采用的建议 ({suggestedNodes.length})
                      </span>
                      <button type="button" onClick={addAllSuggested}
                        style={{ fontSize: 11, padding: "4px 10px", border: "1px solid var(--brand)", background: "var(--brand)", color: "#fff", borderRadius: 999, cursor: "pointer", fontWeight: 500 }}>
                        追加全部
                      </button>
                    </div>
                    <div style={{ display: "grid", gap: 4 }}>
                      {suggestedNodes.map(n => (
                        <button key={n.id} type="button" onClick={() => addNode(n.id)}
                          style={{ display: "flex", justifyContent: "space-between", gap: 8, width: "100%", textAlign: "left", padding: "6px 10px", border: "1px solid rgba(30,64,175,0.2)", borderRadius: "var(--radius-sm)", background: "var(--card)", color: "var(--text)", cursor: "pointer", fontSize: 12, lineHeight: 1.4 }}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{formatNodePath(n, knowmapNodes)}</span>
                          <span style={{ color: "var(--brand)", fontWeight: 700, flexShrink: 0 }}>+ 添加</span>
                        </button>
                      ))}
                    </div>
                    <p style={{ fontSize: 10, color: "var(--text-muted)", margin: "6px 0 0" }}>
                      默认已按 AI 匹配自动关联，可点击下方"×"撤销；未采用的候选如需追加，点即可添加。
                    </p>
                  </div>
                )}
                <input value={nodeQuery} onChange={e => setNodeQuery(e.target.value)}
                  placeholder="搜索章节、知识点或节点 ID"
                  aria-label="搜索图谱节点"
                  style={inputStyle} />
                <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
                  {nodeMatches.map(n => (
                    <button key={n.id} type="button" onClick={() => addNode(n.id)}
                      style={{ display: "flex", justifyContent: "space-between", gap: 8, width: "100%", textAlign: "left", padding: "8px 10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--card)", color: "var(--text)", cursor: "pointer", fontSize: 12, lineHeight: 1.4 }}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{formatNodePath(n, knowmapNodes)}</span>
                      <span style={{ color: "var(--brand)", fontWeight: 700, flexShrink: 0 }}>添加</span>
                    </button>
                  ))}
                  {nodeMatches.length === 0 && (
                    <div style={{ display: "grid", gap: 6 }}>
                      <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 4px" }}>
                        {nodeQuery.trim() ? `未匹配到"${nodeQuery.trim()}"，按教材浏览：` : "按教材浏览："}
                      </p>
                      {browseParentId && (
                        <button type="button" onClick={() => {
                          const current = knowmapNodes.find(n => n.id === browseParentId);
                          setBrowseParentId(current?.parent_id ?? null);
                        }} style={{ fontSize: 12, textAlign: "left", padding: "6px 10px", border: "1px dashed var(--border)", borderRadius: "var(--radius-sm)", background: "transparent", color: "var(--text-muted)", cursor: "pointer" }}>
                          ← 返回上一级
                        </button>
                      )}
                      {(browseParentId
                        ? browseChildren(knowmapNodes, browseParentId, result?.knowmap_nodes || [])
                        : browseTopLevelBooks(knowmapNodes, result?.knowmap_nodes || [])
                      ).map(n => {
                        const hasChildren = knowmapNodes.some(c => c.parent_id === n.id);
                        return (
                          <div key={n.id} style={{ display: "flex", gap: 6 }}>
                            <button type="button" onClick={() => addNode(n.id)}
                              style={{ flex: 1, textAlign: "left", padding: "8px 10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--card)", color: "var(--text)", cursor: "pointer", fontSize: 12, lineHeight: 1.4 }}>
                              <span style={{ color: "var(--brand)", fontWeight: 600, marginRight: 6 }}>选此</span>
                              {n.name}
                            </button>
                            {hasChildren && (
                              <button type="button" onClick={() => setBrowseParentId(n.id)}
                                style={{ padding: "8px 10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "transparent", color: "var(--text-muted)", cursor: "pointer", fontSize: 12 }}>
                                展开 →
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
              {selectedNodes.length > 0 ? (
                <div style={{ marginTop: 8 }}>
                  <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 4px" }}>
                    已关联 {selectedNodes.length} 个节点(点标签 × 撤销):
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {selectedNodes.map(n => (
                      <button key={n.id} type="button" onClick={() => removeNode(n.id)}
                        title="点击移除"
                        style={{ border: "1px solid rgba(30,64,175,0.15)", background: "var(--brand-bg)", color: "var(--brand)", borderRadius: 999, padding: "3px 9px", fontSize: 11, cursor: "pointer" }}>
                        {n.name} ×
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "8px 0 0" }}>
                  尚未关联图谱节点。可在上方"还没被采用的建议"里追加,或用下方搜索/教材浏览手动挑选。
                </p>
              )}

              <label style={{ ...labelStyle, marginTop: 10 }}>题眼 / 解题突破口</label>
              <input value={result.key_insight || ""} onChange={e => updateResult({ key_insight: e.target.value })}
                placeholder="例如：连接半径证明垂直，转化为相似三角形"
                style={inputStyle} />

              <label style={{ ...labelStyle, marginTop: 10 }}>最终答案</label>
              <input value={result.final_answer || ""} onChange={e => updateResult({ final_answer: e.target.value })}
                placeholder="可选：填入最终答案，便于后续导学"
                style={inputStyle} />

              <label style={{ ...labelStyle, marginTop: 10 }}>解析 / 已知解法</label>
              <textarea value={result.solution_text || ""} onChange={e => updateResult({ solution_text: e.target.value })} rows={4}
                placeholder="可选：粘贴答案解析，或记录自己的解法"
                style={textareaStyle} />

              <label style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 10, fontSize: 12, color: "var(--text-secondary)" }}>
                <input type="checkbox" checked={!!result.has_diagram} onChange={e => updateResult({ has_diagram: e.target.checked })} />
                含几何图或函数图
              </label>

              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                <button onClick={confirm} disabled={confirming || !result.text?.trim()}
                  style={{ flex: 1, padding: "10px", background: "var(--success)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: confirming ? "default" : "pointer", fontSize: 13, fontWeight: 500, opacity: confirming ? 0.7 : 1 }}>
                  {confirming ? "正在入库..." : "确认入库"}
                </button>
                <button onClick={reset}
                  style={{ flex: 1, padding: "10px", background: "var(--card)", color: "var(--text-secondary)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13 }}>
                  重新选择
                </button>
              </div>
            </>
          ) : (
            <>
              <p style={{ fontSize: 13, color: "var(--error)", marginBottom: 4 }}>分析失败</p>
              <p style={{ fontSize: 13, color: "var(--text)", marginBottom: 4 }}>{result.error || "无法识别题目"}</p>
              {result.suggestion && <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 12 }}>建议：{result.suggestion}</p>}
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => setResult(null)}
                  style={{ flex: 1, padding: "10px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13, fontWeight: 500 }}>
                  重试
                </button>
                <button onClick={reset}
                  style={{ flex: 1, padding: "10px", background: "var(--card)", color: "var(--text-secondary)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13 }}>
                  重新选择
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

const labelStyle = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--text-secondary)",
  marginBottom: 4,
};

const inputStyle = {
  width: "100%",
  padding: "8px 10px",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  fontSize: 13,
  background: "var(--card)",
  color: "var(--text)",
};

const textareaStyle = {
  ...inputStyle,
  resize: "vertical" as const,
  lineHeight: 1.5,
};
