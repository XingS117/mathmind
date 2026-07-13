import { useState, useEffect, useCallback } from "react";
import { completeReview, DueReview, getDashboard, getHistory } from "../services/api";

type Page = "dashboard" | "upload" | "knowmap" | "tutor";

interface Props {
  onSelectQuestion: (qid: string) => void;
  onNavigate: (page: Page) => void;
  onSelectWeakPoint?: (weakPoint: string) => void;
}

const pillStyle = (color: string) => ({
  padding: "3px 10px", borderRadius: 999, fontSize: 11, cursor: "pointer",
  background: color,
});

export default function DashboardPage({ onSelectQuestion, onNavigate, onSelectWeakPoint }: Props) {
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [showWeak, setShowWeak] = useState(false);
  const [showDist, setShowDist] = useState(false);
  const [completingReviewId, setCompletingReviewId] = useState<string | null>(null);

  const refreshDashboard = useCallback(() => {
    getDashboard().then(setData).catch(() => {});
    getHistory().then((d) => setHistory(d.sessions || [])).catch(() => {});
  }, []);

  useEffect(() => { refreshDashboard(); }, [refreshDashboard]);

  const handleCompleteReview = async (review: DueReview) => {
    if (!window.confirm("确认已完成这次复习？")) return;
    setCompletingReviewId(review.id);
    try {
      await completeReview(review.id);
      refreshDashboard();
    } finally {
      setCompletingReviewId(null);
    }
  };

  const stats = [
    { label: "已入库题目", value: data?.total_questions || 0, color: "var(--brand)", hint: "查看分布", onClick: () => onNavigate("knowmap") },
    { label: "学习次数", value: data?.total_sessions || 0, color: "var(--success)", hint: (data?.top_studied?.length || 0) > 0 ? "查看分布" : "", onClick: (data?.top_studied?.length || 0) > 0 ? () => setShowDist(!showDist) : () => setShowDist(!showDist) },
    { label: "平均掌握度", value: `${Math.round((data?.avg_mastery || 0) * 100)}%`, color: "var(--accent)", hint: data?.weak_points?.length ? "查看薄弱点" : "", onClick: () => setShowWeak(!showWeak) },
  ];

  const weakBg = "rgba(239,68,68,0.08)";
  const weakColor = "var(--error)";

  return (
    <div>
      <div style={{ marginBottom: 16, padding: 16, background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", boxShadow: "var(--shadow)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, marginBottom: 10 }}>
          <h2 style={{ margin: 0, fontSize: 16, color: "var(--text)" }}>今日复习</h2>
          <span style={{ fontSize: 12, color: "var(--success)", fontWeight: 600 }}>本周掌握度变化 +{Math.round((data?.mastery_change || 0) * 100)}%</span>
        </div>
        {data?.due_reviews?.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.due_reviews.map((review: DueReview) => (
              <div key={review.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "10px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)" }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>第 {review.round} 轮复习</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>{review.type} · {review.scheduled_date}</div>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  <button type="button" onClick={() => onSelectQuestion(review.question_id)}
                    style={{ padding: "5px 9px", border: "none", borderRadius: "var(--radius-sm)", background: "var(--brand)", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                    开始复习
                  </button>
                  <button type="button" onClick={() => handleCompleteReview(review)} disabled={completingReviewId === review.id}
                    style={{ padding: "5px 9px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--card)", color: "var(--text-secondary)", cursor: completingReviewId === review.id ? "wait" : "pointer", fontSize: 12 }}>
                    {completingReviewId === review.id ? "提交中" : "完成复习"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, fontSize: 13, color: "var(--text-muted)" }}>
            <span>今日没有待复习，去入库一道题</span>
            <button type="button" onClick={() => onNavigate("upload")}
              style={{ padding: "5px 9px", border: "1px solid var(--brand)", borderRadius: "var(--radius-sm)", background: "var(--card)", color: "var(--brand)", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
              去入库
            </button>
          </div>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}>
        {stats.map((s, i) => (
          <div key={i} onClick={s.onClick}
            style={{ background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)",
              padding: 20, boxShadow: "var(--shadow)", cursor: "pointer" }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: s.color, lineHeight: 1.2 }}>{s.value}</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {showDist && (
        <div style={{ marginBottom: 16, padding: 12, background: "var(--card)", borderRadius: "var(--radius)",
          border: "1px solid var(--border)", boxShadow: "var(--shadow)" }}>
          <h3 style={{ fontSize: 12, fontWeight: 600, color: "var(--success)", marginBottom: 8 }}>学习分布</h3>
          {data?.top_studied?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {data.top_studied.map((item: any, i: number) => {
                const maxC = Math.max(...data.top_studied.map((t: any) => t.count));
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                    <span style={{ color: "var(--success)", fontWeight: 600, minWidth: 24, textAlign: "right" }}>{item.count}次</span>
                    <div style={{ flex: 1, height: 20, background: "var(--bg)", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${(item.count / maxC) * 100}%`,
                        background: "var(--success)", borderRadius: 4, opacity: 0.5 }} />
                    </div>
                    <span style={{ color: "var(--text)", flex: 1 }}>{item.node}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ fontSize: 12, color: "var(--text-muted)", padding: 8 }}>暂无学习记录</p>
          )}
        </div>
      )}

      {showWeak && (
        <div style={{ marginBottom: 16, padding: 12, background: "var(--card)", borderRadius: "var(--radius)",
          border: "1px solid var(--border)", boxShadow: "var(--shadow)" }}>
          <h3 style={{ fontSize: 12, fontWeight: 600, color: weakColor, marginBottom: 8 }}>薄弱知识点</h3>
          {data?.weak_points?.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {data.weak_points.slice(0, 8).map((w: string, i: number) => (
                <span key={i} onClick={() => onSelectWeakPoint ? onSelectWeakPoint(w) : onNavigate("knowmap")}
                  style={pillStyle(weakBg)}>
                  {w}
                </span>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 12, color: "var(--text-muted)", padding: 8 }}>暂无薄弱知识点，继续加油</p>
          )}
        </div>
      )}

      {data?.weak_points?.length > 0 && (
        <div style={{ marginBottom: 16, padding: 14, background: "linear-gradient(135deg, rgba(239,68,68,0.08), rgba(245,158,11,0.08))", borderRadius: "var(--radius)",
          border: "1px solid rgba(239,68,68,0.14)", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", margin: 0 }}>最近暴露的薄弱点</h3>
            <button onClick={() => onSelectWeakPoint ? onSelectWeakPoint(data.weak_points[0]) : onNavigate("knowmap")}
              style={{ padding: "4px 10px", border: "1px solid rgba(239,68,68,0.18)", borderRadius: "var(--radius-sm)", background: "var(--card)", color: "var(--error)", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
              去图谱看
            </button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {data.weak_points.slice(0, 6).map((w: string, i: number) => (
              <button key={i} type="button" onClick={() => onSelectWeakPoint ? onSelectWeakPoint(w) : onNavigate("knowmap")}
                style={{ padding: "3px 10px", borderRadius: 999, fontSize: 11, color: "var(--error)", background: "rgba(255,255,255,0.72)", border: "1px solid rgba(239,68,68,0.12)", cursor: "pointer" }}>
                {w}
              </button>
            ))}
          </div>
        </div>
      )}

      {history.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 16 }}>
          <div style={{ background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: 20, boxShadow: "var(--shadow)" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: "var(--text)" }}>最近学习</h3>
            {history.slice(0, 6).map((s: any, i: number) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "8px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)", fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: "var(--text)", fontWeight: 500 }}>{s.question_id?.slice(0, 14) || "题目"}</span>
                <span style={{ fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 999,
                  color: s.status === "completed" ? "var(--success)" : "var(--warning)",
                  background: s.status === "completed" ? "rgba(16,185,129,0.08)" : "rgba(245,158,11,0.08)" }}>
                  {s.status === "completed" ? "已完成" : "进行中"}
                </span>
              </div>
            ))}
          </div>
          <div onClick={() => onNavigate("upload")}
            style={{ background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: 20, boxShadow: "var(--shadow)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>入库新题目</p>
              <p style={{ fontSize: 11, color: "var(--text-muted)" }}>拍照或上传一道数学题</p>
            </div>
          </div>
        </div>
      ) : (
        <div onClick={() => onNavigate("upload")}
          style={{ background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)", padding: "60px 24px", boxShadow: "var(--shadow)", cursor: "pointer", textAlign: "center" }}>
          <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", marginBottom: 12 }}>开始你的学习之旅</p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 24 }}>点击下方按钮入库你的第一道题目</p>
          <div style={{ display: "inline-flex", padding: "10px 32px", background: "var(--brand)", color: "#fff", borderRadius: "var(--radius-sm)", fontSize: 14, fontWeight: 500 }}>入库第一题</div>
        </div>
      )}
    </div>
  );
}
