import { useEffect, useState } from "react";
import { Copy, ImageDown, Share2, Sparkles } from "lucide-react";
import { getReferralSummary, ReferralSummary } from "../services/api";
import { buildPromotionText, SHARE_TITLE } from "../utils/sharePromotion";
import { createSharePoster, downloadSharePoster, sharePoster } from "../utils/sharePoster";

export default function SharePage() {
  const [summary, setSummary] = useState<ReferralSummary | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [savingPoster, setSavingPoster] = useState(false);

  const load = async () => {
    setError("");
    try { setSummary(await getReferralSummary()); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "分享信息加载失败"); }
  };
  useEffect(() => { void load(); }, []);

  const copyPromotion = async () => {
    if (!summary) return;
    const text = buildPromotionText(summary.share_url);
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

  const savePoster = async () => {
    if (!summary || savingPoster) return;
    setSavingPoster(true);
    setNotice("");
    try {
      const poster = await createSharePoster(summary.share_url);
      if (await sharePoster(poster)) setNotice("已打开系统分享，请在微信中选择好友或朋友圈");
      else {
        downloadSharePoster(poster);
        setNotice("海报已保存，请在微信中发送给好友或朋友圈");
      }
    } catch (e: unknown) {
      setNotice(e instanceof Error ? e.message : "海报生成失败，请重试");
    } finally {
      setSavingPoster(false);
    }
  };

  const shareLink = async () => {
    if (!summary) return;
    const text = buildPromotionText(summary.share_url);
    try {
      if (navigator.share) {
        await navigator.share({ title: "MathMind", text, url: summary.share_url });
        setNotice("已打开系统分享面板");
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
  const buttonStyle = { minHeight: 46, padding: "10px 14px", borderRadius: "var(--radius-sm)", cursor: "pointer", display: "inline-flex", justifyContent: "center", alignItems: "center", gap: 7, fontSize: 13, fontWeight: 600 };

  return <section style={{ maxWidth: 760, margin: "0 auto" }}>
    <div style={{ padding: "clamp(22px, 5vw, 38px)", borderRadius: "var(--radius)", color: "#fff", overflow: "hidden", position: "relative", background: "linear-gradient(135deg, #173fba 0%, #285ed5 58%, #65baf0 100%)", boxShadow: "0 16px 36px rgba(26, 66, 174, 0.2)" }}>
      <div style={{ position: "absolute", width: 260, height: 260, borderRadius: "50%", right: -100, top: -120, background: "rgba(255,255,255,0.13)" }} />
      <div style={{ position: "relative" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "6px 10px", borderRadius: 999, background: "rgba(255,255,255,0.16)", fontSize: 12, fontWeight: 600 }}><Sparkles size={15} /> MathMind · 错题学习工具</div>
        <h2 style={{ maxWidth: 460, margin: "18px 0 10px", fontSize: "clamp(25px, 5vw, 37px)", lineHeight: 1.22, letterSpacing: "-0.03em" }}>{SHARE_TITLE}</h2>
        <p style={{ maxWidth: 520, margin: 0, color: "rgba(255,255,255,0.86)", lineHeight: 1.7, fontSize: 14 }}>上传错题，人工确认后开始分步陪练；学习记录会形成后续复习任务。</p>
      </div>
    </div>

    {!summary && !error && <p style={{ color: "var(--text-muted)", marginTop: 18 }}>加载中...</p>}
    {error && <div style={{ marginTop: 18 }}><p style={{ color: "var(--error)", marginBottom: 10 }}>{error}</p><button onClick={() => void load()}>重试</button></div>}
    {summary && <>
      <section style={{ marginTop: 18, padding: 18, borderRadius: "var(--radius)", border: "1px solid var(--border)", background: "var(--card)" }}>
        <h3 style={{ margin: "0 0 6px", fontSize: 16 }}>一张海报，轻松分享到微信</h3>
        <p style={{ margin: "0 0 16px", color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.65 }}>保存后可在微信发送给好友或朋友圈。网页无法直接指定微信收件人，但海报和文案都已为你准备好。</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(0, 1fr))", gap: 10 }}>
          <button onClick={() => void savePoster()} disabled={savingPoster} style={{ ...buttonStyle, border: "none", background: "var(--brand)", color: "#fff" }}><ImageDown size={17} />{savingPoster ? "生成海报中..." : "保存微信海报"}</button>
          <button onClick={() => void copyPromotion()} style={{ ...buttonStyle, border: "1px solid var(--border)", background: "var(--card)", color: "var(--text)" }}><Copy size={16} />复制推广文案</button>
          <button onClick={() => void shareLink()} style={{ ...buttonStyle, border: "1px solid var(--border)", background: "var(--card)", color: "var(--text)" }}><Share2 size={16} />更多分享方式</button>
        </div>
        {notice && <p style={{ margin: "14px 0 0", padding: "9px 12px", borderRadius: "var(--radius-sm)", background: "var(--brand-bg)", color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.55, overflowWrap: "anywhere" }}>{notice}</p>}
      </section>

      <section style={{ marginTop: 18 }}>
        <h3 style={{ margin: "0 0 10px", fontSize: 16 }}>我的邀请数据</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, margin: "0 0 12px" }}>仅展示汇总数据，不展示任何同学身份信息。</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12 }}>
          {cards.map(([label, value]) => <div key={String(label)} style={{ padding: 16, border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--card)" }}><div style={{ color: "var(--text-muted)", fontSize: 13 }}>{label}</div><strong style={{ fontSize: 24 }}>{value}</strong></div>)}
        </div>
      </section>
    </>}
  </section>;
}
