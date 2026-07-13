import { useEffect, useState } from "react";
import { getOperationsOverview, OperationsOverview } from "../services/api";

export default function AdminOperationsPage() {
  const [overview, setOverview] = useState<OperationsOverview | null>(null);
  const [error, setError] = useState("");
  const load = async () => {
    setError("");
    try { setOverview(await getOperationsOverview()); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "运营数据加载失败"); }
  };
  useEffect(() => { void load(); }, []);
  const funnel = overview ? [["访问", overview.funnel.visits], ["注册", overview.funnel.registrations], ["完成首题", overview.funnel.first_questions], ["完成导学", overview.funnel.first_tutors]] : [];

  return <section style={{ maxWidth: 860, margin: "0 auto" }}>
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 16 }}><div><h2 style={{ fontSize: 20 }}>运营看板</h2><p style={{ fontSize: 13, color: "var(--text-muted)" }}>仅显示汇总数据，不包含学生身份、题目或原始访问记录。</p></div><button onClick={() => void load()}>刷新</button></div>
    {!overview && !error && <p style={{ color: "var(--text-muted)" }}>加载中...</p>}
    {error && <div><p style={{ color: "var(--error)", marginBottom: 10 }}>{error}</p><button onClick={() => void load()}>重试</button></div>}
    {overview && <>
      <h3 style={{ marginBottom: 10 }}>推广漏斗</h3><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 26 }}>{funnel.map(([label, value]) => <div key={String(label)} style={{ padding: 16, border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--card)" }}><span style={{ color: "var(--text-muted)", fontSize: 13 }}>{label}</span><strong style={{ display: "block", fontSize: 24 }}>{value}</strong></div>)}</div>
      <h3 style={{ marginBottom: 10 }}>运行健康</h3>
      {overview.runtime_health.length === 0 ? <p style={{ color: "var(--text-muted)" }}>暂无运行数据</p> : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>{overview.runtime_health.map(row => <div key={`${row.engine_kind}-${row.provider}-${row.model_name}`} style={{ padding: 16, border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--card)", overflowWrap: "anywhere" }}><strong>{row.engine_kind} · {row.provider}</strong><div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{row.model_name || "未标注模型"}</div><div style={{ fontSize: 13, marginTop: 10 }}>调用 {row.count} 次 · 成功率 {Math.round(row.success_rate * 100)}%</div><div style={{ fontSize: 13, color: "var(--text-secondary)" }}>平均耗时 {row.avg_duration_ms === null ? "—" : `${row.avg_duration_ms} ms`}</div></div>)}</div>}
    </>}
  </section>;
}
