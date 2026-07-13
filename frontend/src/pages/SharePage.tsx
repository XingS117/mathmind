import { useEffect, useState } from "react";
import { getReferralSummary, ReferralSummary } from "../services/api";

const PROMOTION_PREFIX = "我在数智学堂整理错题、分步练习，欢迎一起试试：";

export default function SharePage() {
  const [summary, setSummary] = useState<ReferralSummary | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = async () => {
    setError("");
    try { setSummary(await getReferralSummary()); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "分享信息加载失败"); }
  };
  useEffect(() => { void load(); }, []);

  const share = async () => {
    if (!summary) return;
    const text = `${PROMOTION_PREFIX}${summary.share_url}`;
    const copyPromotion = async () => {
      if (!navigator.clipboard) {
        setNotice(`请手动复制：${text}`);
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        setNotice("推广文案已复制，可粘贴发送给好友或朋友圈");
      } catch {
        setNotice(`复制失败，请手动复制：${text}`);
      }
    };
    try {
      if (navigator.share) {
        await navigator.share({ title: "数智学堂", text, url: summary.share_url });
        setNotice("已打开分享面板");
      } else {
        await copyPromotion();
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      await copyPromotion();
    }
  };

  const cards = summary ? [
    ["访问", summary.visits], ["注册", summary.registrations], ["完成首题", summary.first_questions], ["完成导学", summary.first_tutors],
  ] : [];
  return <section style={{ maxWidth: 720, margin: "0 auto" }}>
    <h2 style={{ fontSize: 20, marginBottom: 6 }}>邀请同学一起学习</h2>
    <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 18 }}>分享专属链接，数据只展示汇总，不展示任何同学身份信息。</p>
    {!summary && !error && <p style={{ color: "var(--text-muted)" }}>加载中...</p>}
    {error && <div><p style={{ color: "var(--error)", marginBottom: 10 }}>{error}</p><button onClick={() => void load()}>重试</button></div>}
    {summary && <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, marginBottom: 20 }}>
        {cards.map(([label, value]) => <div key={String(label)} style={{ padding: 16, border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--card)" }}><div style={{ color: "var(--text-muted)", fontSize: 13 }}>{label}</div><strong style={{ fontSize: 24 }}>{value}</strong></div>)}
      </div>
      <div style={{ padding: 16, borderRadius: "var(--radius)", background: "var(--brand-bg)", overflowWrap: "anywhere" }}>{PROMOTION_PREFIX}{summary.share_url}</div>
      <button onClick={() => void share()} style={{ marginTop: 14, padding: "10px 18px", border: "none", borderRadius: "var(--radius-sm)", background: "var(--brand)", color: "#fff", cursor: "pointer" }}>转发给好友或朋友圈</button>
      {notice && <p style={{ marginTop: 12, fontSize: 13, color: "var(--text-secondary)", overflowWrap: "anywhere" }}>{notice}</p>}
    </>}
  </section>;
}
