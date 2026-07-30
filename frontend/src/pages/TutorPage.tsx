import { useState, useEffect, useRef, useCallback } from "react";
import { createTutorSession, sendTutorMessage, type TutorDiagnosticSummary } from "../services/api";
import DiagramView from "../components/DiagramView";

interface Props { questionId: string; onSelectQuestion?: (qid: string) => void; }

export default function TutorPage({ questionId, onSelectQuestion }: Props) {
  const [session, setSession] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState({ current: 0, total: 0, hints: 3 });
  const [completed, setCompleted] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [lastReply, setLastReply] = useState<any>(null);
  const [diagnostic, setDiagnostic] = useState<TutorDiagnosticSummary | null>(null);
  const chatEnd = useRef<HTMLDivElement>(null);
  const scroll = () => chatEnd.current?.scrollIntoView({ behavior: "smooth" });

  useEffect(() => {
    setCompleted(false);
    setDiagnostic(null);
    setLastReply(null);
    if (!questionId || questionId.startsWith("kg_")) {
      setMessages([{ role: "system", content: "请先上传一道题目开始学习。" }]);
      setLoading(false); return;
    }
    createTutorSession(questionId).then((d) => {
      setSession(d);
      const msgs: any[] = [
        { role: "system", content: d.question_text, isQuestion: true },
      ];
      if (
        d.solution_confidence === "low" ||
        (Array.isArray(d.uncertain_points) && d.uncertain_points.length > 0)
      ) {
        const detail = (d.uncertain_points || []).slice(0, 3).join("；");
        msgs.push({
          role: "system",
          type: "warning",
          content:
            "⚠️ AI 自检提示：本题的解析置信度较低，请对照原答案核对后再学习。" +
            (detail ? `\n关注点：${detail}` : ""),
        });
      }
      msgs.push({ role: "system", content: d.opening });
      setMessages(msgs);
      setStep({ current: 1, total: d.total_steps, hints: d.hints_available });
      setLoading(false);
      setTimeout(scroll, 100);
    });
  }, [questionId]);

  useEffect(() => { scroll(); }, [messages]);

  const send = useCallback(async (msg: string, intent = "answer") => {
    if (!session) return;
    const text = msg.trim() || `[${intent}]`;
    setMessages((p) => [...p, { role: "user", content: text }]);
    setWaiting(true);
    setInput("");

    try {
      const r = await sendTutorMessage(session.session_id, text, intent);
      setLastReply(r);
      if (r.type === "complete") {
        setCompleted(true);
        setDiagnostic(r.diagnostic_summary || null);
      }
      setMessages((p) => [...p, { role: "system", content: r.reply, type: r.type }]);
      setStep({ current: r.step_index, total: r.total_steps, hints: r.hints_remaining });
      setTimeout(scroll, 100);
    } catch {
      setMessages((p) => [...p, { role: "system", content: "网络开小差了，请稍后再试。" }]);
    } finally {
      setWaiting(false);
    }
  }, [session]);

  if (loading) return <div style={{ textAlign: "center", padding: 60, color: "var(--text-muted)" }}>准备学习中...</div>;

  const pct = step.total > 0 ? Math.min((step.current / step.total) * 100, 100) : 0;

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "72vh",
      border: "1px solid var(--border)", borderRadius: "var(--radius)",
      overflow: "hidden", background: "var(--card)", boxShadow: "var(--shadow)",
    }}>
      {/* Header */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", background: "var(--bg)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            {Math.min(step.current, step.total)} / {step.total} 步
          </span>
          <span style={{ fontSize: 12, color: step.hints > 0 ? "var(--warning)" : "var(--text-muted)" }}>
            提示 {step.hints} 次
          </span>
        </div>
        <div style={{ height: 3, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${pct}%`, background: "var(--brand)", borderRadius: 2, transition: "width 0.3s" }} />
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            maxWidth: m.isQuestion ? "100%" : "82%",
            padding: m.isQuestion ? "12px 16px" : "10px 14px",
            borderRadius: m.isQuestion ? "var(--radius)" : 12,
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            background: m.isQuestion ? "var(--brand-bg)" : m.role === "user" ? "var(--brand)" : "var(--bg)",
            color: m.isQuestion ? "var(--text)" : m.role === "user" ? "#fff" : "var(--text)",
            border: m.isQuestion ? "1px solid rgba(30,64,175,0.1)" : undefined,
            borderBottomRightRadius: m.role === "user" ? 4 : 12,
            borderBottomLeftRadius: m.role === "user" ? 12 : 4,
            fontSize: m.isQuestion ? 13 : 14, lineHeight: 1.6, whiteSpace: "pre-wrap",
          }}>
            {m.isQuestion && <div style={{ fontSize: 11, fontWeight: 600, color: "var(--brand)", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>题目</div>}
            {m.isQuestion && session?.has_diagram && session?.diagram_json && <DiagramView diagram={session.diagram_json} />}
            {m.content}
          </div>
        ))}
        {waiting && (
          <div style={{ alignSelf: "flex-start", padding: "10px 14px", background: "#f0f0f0", borderRadius: 12, fontSize: 14, animation: "pulse 1.5s ease-in-out infinite" }}>
            <span style={{ color: "#94a3b8" }}>老师正在思考</span>
            <span style={{ animation: "blink 1.5s step-end infinite", marginLeft: 2 }}>。</span>
            <span style={{ animation: "blink 1.5s step-end infinite 0.3s" }}>。</span>
            <span style={{ animation: "blink 1.5s step-end infinite 0.6s" }}>。</span>
          </div>
        )}
        <div ref={chatEnd} />
      </div>

      {/* Input */}
      {!completed ? (
        <div style={{ borderTop: "1px solid var(--border)", padding: 12, background: "var(--card)" }}>
          <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
            {[
              { label: `提示 (${step.hints})`, intent: "hint", color: "var(--warning)", disabled: step.hints <= 0 },
              { label: "详细讲解", intent: "detail", color: "var(--success)" },
              { label: "跳过此步", intent: "skip", color: "var(--text-muted)" },
            ].map((b) => (
              <button key={b.intent} onClick={() => send("", b.intent)} disabled={b.disabled}
                style={{
                  padding: "5px 12px", borderRadius: 6, border: "1px solid var(--border)",
                  cursor: "pointer", fontSize: 12,
                  background: b.disabled ? "var(--bg)" : "var(--card)", color: b.disabled ? "var(--text-muted)" : b.color,
                }}>
                {b.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="输入你的答案..."
              style={{
                flex: 1, padding: "10px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
                fontSize: 14, outline: "none", transition: "border-color 0.15s",
              }}
              onFocus={(e) => e.target.style.borderColor = "var(--brand-light)"}
              onBlur={(e) => e.target.style.borderColor = "var(--border)"} />
            <button onClick={() => send(input)}
              style={{
                padding: "10px 22px", background: "var(--brand)", color: "#fff",
                border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer",
                fontSize: 14, fontWeight: 500,
              }}>
              发送
            </button>
          </div>
        </div>
      ) : (
        (() => {
          const mu = typeof lastReply?.mastery_update === "number" ? lastReply.mastery_update : 0;
          const done = diagnostic?.completed_steps ?? 0;
          const total = diagnostic?.total_steps ?? step.total ?? 0;
          const isMastered = mu >= 0.3 && total > 0 && done === total;
          const isPartial = !isMastered && mu > 0;
          const bg = isMastered
            ? "rgba(16,185,129,0.05)"
            : isPartial
              ? "rgba(245,158,11,0.06)"
              : "rgba(239,68,68,0.05)";
          const titleColor = isMastered
            ? "var(--success)"
            : isPartial
              ? "#b45309"
              : "#991b1b";
          const title = isMastered
            ? "学习完成！"
            : isPartial
              ? "本轮走完，还没完全掌握"
              : "本轮走完，未掌握";
          const subtitle = isMastered
            ? `掌握度 +${mu.toFixed(1)}`
            : isPartial
              ? `答对 ${done}/${total} 步，掌握度 +${mu.toFixed(1)}`
              : `答对 ${done}/${total} 步，先回看讲解再练一次`;
          return (
        <div style={{ borderTop: "1px solid var(--border)", padding: 20, textAlign: "center", background: bg }}>
          <p style={{ fontSize: 16, fontWeight: 700, color: titleColor, marginBottom: 4 }}>{title}</p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>{subtitle}</p>
          {diagnostic && (
            <div style={{ textAlign: "left", background: "var(--card)", border: "1px solid rgba(16,185,129,0.18)", borderRadius: "var(--radius-sm)", padding: 12, marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>学习诊断</span>
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {diagnostic.completed_steps}/{diagnostic.total_steps} 步 · 提示 {diagnostic.hints_used} 次
                </span>
              </div>
              {diagnostic.weak_spots?.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                  {diagnostic.weak_spots.map((spot) => (
                    <span key={spot} style={{ fontSize: 11, color: "var(--brand)", background: "var(--brand-bg)", border: "1px solid rgba(30,64,175,0.12)", borderRadius: 999, padding: "2px 8px" }}>
                      {spot}
                    </span>
                  ))}
                </div>
              )}
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                下一步：{diagnostic.next_action}
              </p>
            </div>
          )}
          {isMastered && lastReply?.variants?.length > 0 && (
            <>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>试试变式题巩固</p>
              <button onClick={() => onSelectQuestion?.(lastReply.variants[0])}
                style={{ padding: "10px 28px", background: "var(--success)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 14, fontWeight: 500 }}>
                做下一道变式题
              </button>
            </>
          )}
        </div>
          );
        })()
      )}
    </div>
  );
}
