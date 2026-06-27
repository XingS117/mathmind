import { useState, useEffect, useCallback } from "react";
import ImageUpload from "./components/ImageUpload";
import KnowMapPage from "./pages/KnowMapPage";
import TutorPage from "./pages/TutorPage";
import DashboardPage from "./pages/DashboardPage"
import SettingsPage from "./pages/SettingsPage"
import WenXingLogo from "./components/WenXingLogo"
import LoginPage from "./pages/LoginPage";
import { getActiveSession, uploadQuestion } from "./services/api";

type Page = "dashboard" | "upload" | "knowmap" | "tutor" | "settings" | "login";
type Grade = "初中" | "高中";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [activeSid, setActiveSid] = useState<string | null>(null);
  const [selectedQid, setSelectedQid] = useState<string | null>(null);
  const [focusedWeakPoint, setFocusedWeakPoint] = useState<string>("");
  const [grade, setGrade] = useState<Grade>("高中");

  useEffect(() => {
    getActiveSession().then((d) => {
      if (d.session_id) setActiveSid(d.session_id);
    }).catch(() => {});
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    const res = await uploadQuestion(file);
    setSelectedQid(res.question_id);
    setPage("tutor");
  }, []);

  const handleSelect = useCallback((qid: string) => {
    setSelectedQid(qid);
    setPage("tutor");
  }, []);

  const handleWeakPointSelect = useCallback((weakPoint: string) => {
    setFocusedWeakPoint(weakPoint);
    setPage("knowmap");
  }, []);

  const handleLogin = (token: string) => {
    localStorage.setItem('token', token);
    fetch('/api/v1/auth/me', { headers: {'Authorization': 'Bearer ' + token} })
      .then(r => r.json()).then(d => setUser(d));
    setPage('dashboard');
  };
  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null); setPage('dashboard');
  };
  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) fetch('/api/v1/auth/me', {headers:{'Authorization':'Bearer '+t}}).then(r=>r.json()).then(d=>setUser(d)).catch(()=>{});
  }, []);
  const [user, setUser] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const handleConfirm = useCallback((qid: string) => {
    setSelectedQid(qid);
    setPage("tutor");
  }, []);
  const nav = [
    { id: "dashboard" as Page, label: "首页" },
    { id: "upload" as Page, label: "入库" },
    { id: "knowmap" as Page, label: "图谱" },{ id: "settings" as Page, label: "设置" },{ id: "login" as Page, label: typeof user !== "undefined" && user ? user.name : "登录" },
  ];

  return (
    <div className="app-shell" style={{ maxWidth: 960, margin: "0 auto", padding: "20px 24px", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header className="app-header" style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", alignItems: "center", marginBottom: 20, gap: 16 }}>
        {/* 文星 badge */}
        <WenXingLogo />

        {/* Center title */}
        <div className="app-title" style={{ textAlign: "center" }}>
          <div className="app-title-line" style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 10 }}>
            <span className="app-title-cn" style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", letterSpacing: 1 }}>数智学堂</span>
            <span className="app-title-en" style={{ fontSize: 22, fontWeight: 400, color: "var(--text-muted)", letterSpacing: 1.5 }}>MathMind</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--brand)", fontWeight: 500, marginTop: 4, letterSpacing: 0.8, opacity: 0.85 }}>
            把错题变成可追踪的学习资产
          </div>
        </div>

        {/* Nav + grade switcher */}
        <div className="app-actions" style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          <nav className="app-nav" style={{ display: "flex", gap: 6 }}>
            {nav.map((n) => (
              <button key={n.id} onClick={() => { setPage(n.id); }}
                style={{ padding: "8px 18px", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13, fontWeight: page === n.id ? 600 : 400, background: page === n.id ? "var(--brand)" : "transparent", color: page === n.id ? "#fff" : "var(--text-secondary)", transition: "all 0.15s" }}>
                {n.label}
              </button>
            ))}
          </nav>
          {/* Grade toggle */}
          <div className="grade-toggle" style={{ display: "flex", borderRadius: 6, overflow: "hidden", border: "1px solid var(--border)" }}>
            {(["初中", "高中"] as Grade[]).map((g) => (
              <button key={g} onClick={() => setGrade(g)}
                style={{ padding: "3px 14px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: grade === g ? 600 : 400, background: grade === g ? "var(--brand)" : "var(--card)", color: grade === g ? "#fff" : "var(--text-secondary)", transition: "all 0.15s" }}>
                {g}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div style={{ height: 1, background: "linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent)", marginBottom: 24 }} />

      {activeSid && page !== "tutor" && (
        <div onClick={() => setPage("tutor")} style={{ padding: "10px 16px", background: "var(--brand-bg)", borderRadius: "var(--radius)", marginBottom: 16, fontSize: 13, cursor: "pointer", color: "var(--brand)", display: "flex", alignItems: "center", gap: 8, border: "1px solid rgba(30,64,175,0.1)" }}>
          <span style={{ fontSize: 16 }}>▶</span> 有未完成的学习，点击继续
        </div>
      )}

      <main style={{ flex: 1, animation: "fadeIn 0.2s ease" }}>
        {page === "dashboard" && <DashboardPage onSelectQuestion={handleSelect} onNavigate={setPage} onSelectWeakPoint={handleWeakPointSelect} />}
        {page === "upload" && <ImageUpload grade={grade} onImage={handleUpload} loading={uploading} onConfirm={handleConfirm} />}
        {page === "knowmap" && <KnowMapPage grade={grade} focusWeakPoint={focusedWeakPoint} onSelectQuestion={handleSelect} />}{page === "login" && <LoginPage onLogin={handleLogin} />}{page === "settings" && <SettingsPage />}
        {page === "tutor" && selectedQid && <TutorPage questionId={selectedQid} onSelectQuestion={handleSelect} />}
      </main>

      <footer style={{ marginTop: 48, padding: "24px 0", textAlign: "center", fontSize: 14, fontWeight: 500, color: "var(--text-secondary)", letterSpacing: 0.5, borderTop: "1px solid var(--border)" }}>
        文星 <span style={{ color: "var(--text-muted)", margin: "0 4px" }}>·</span> 上课认真听，下课用文星
      </footer>
    </div>
  );
}
