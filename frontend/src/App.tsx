import { useState, useEffect, useCallback } from "react";
import { BrainCircuit } from "lucide-react";
import ImageUpload from "./components/ImageUpload";
import KnowMapPage from "./pages/KnowMapPage";
import TutorPage from "./pages/TutorPage";
import DashboardPage from "./pages/DashboardPage"
import SettingsPage from "./pages/SettingsPage"
import LoginPage from "./pages/LoginPage";
import AccountPage from "./pages/AccountPage";
import AdminAccountsPage from "./pages/AdminAccountsPage";
import { getActiveSession, uploadQuestion, fetchMe, logout, AuthUser, captureReferralVisit } from "./services/api";
import SharePage from "./pages/SharePage";
import AdminOperationsPage from "./pages/AdminOperationsPage";
import { type FilingInfo, ICP_FILING, POLICE_FILING } from "./utils/filingInfo";

type Page = "dashboard" | "upload" | "knowmap" | "tutor" | "settings" | "login" | "account" | "share" | "adminAccounts" | "adminOperations";
type Grade = "初中" | "高中";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [activeSid, setActiveSid] = useState<string | null>(null);
  const [selectedQid, setSelectedQid] = useState<string | null>(null);
  const [focusedWeakPoint, setFocusedWeakPoint] = useState<string>("");
  const [grade, setGrade] = useState<Grade>("高中");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [uploading, setUploading] = useState(false);
  const filingLinks = [ICP_FILING, POLICE_FILING].filter((filing): filing is FilingInfo => filing !== null);

  // Load /auth/me on start; if token exists resolve to user, else stay guest.
  const refreshUser = useCallback(() => {
    if (!localStorage.getItem("token")) { setUser(null); return; }
    fetchMe().then(u => {
      if (u && u.id && u.id !== "u_default") setUser(u);
      else setUser(null);
    }).catch(() => setUser(null));
  }, []);
  useEffect(() => { refreshUser(); }, [refreshUser]);

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("ref");
    if (code) void captureReferralVisit(code).catch(() => {});
  }, []);

  // Re-fetch active session whenever the current user changes so guest sessions
  // do not leak into a logged-in user's dashboard.
  useEffect(() => {
    setActiveSid(null);
    getActiveSession().then((d) => {
      if (d && d.session_id) setActiveSid(d.session_id);
    }).catch(() => {});
  }, [user?.id]);

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
    refreshUser();
    setPage('dashboard');
  };
  const handleLogout = () => {
    logout();
    localStorage.removeItem("username");
    setUser(null);
    setPage('dashboard');
  };

  const handleConfirm = useCallback((qid: string) => {
    setSelectedQid(qid);
    setPage("tutor");
  }, []);
  const nav = [
    { id: "dashboard" as Page, label: "首页" },
    { id: "upload" as Page, label: "入库" },
    { id: "knowmap" as Page, label: "图谱" },
    { id: "settings" as Page, label: "设置" },
    ...(user ? [{ id: "share" as Page, label: "分享" }] : []),
    ...(user?.role === "admin" ? [{ id: "adminAccounts" as Page, label: "账户" }, { id: "adminOperations" as Page, label: "运营" }] : []),
    { id: user ? "account" as Page : "login" as Page, label: user ? user.name : "登录" },
  ];

  return (
    <div className="app-shell" style={{ maxWidth: 960, margin: "0 auto", padding: "20px 24px", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header className="app-header" style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", alignItems: "center", marginBottom: 20, gap: 16 }}>
        <div aria-hidden="true" style={{ width: 52, height: 52, flexShrink: 0, borderRadius: 10, display: "grid", placeItems: "center", background: "var(--brand-bg)", color: "var(--brand)" }}>
          <BrainCircuit size={28} strokeWidth={1.8} />
        </div>

        <div className="app-title" style={{ textAlign: "center" }}>
          <div className="app-title-line" style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 10 }}>
            <span className="app-title-cn" style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", letterSpacing: 1 }}>MathMind</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--brand)", fontWeight: 500, marginTop: 4, letterSpacing: 0.8, opacity: 0.85 }}>
            把错题变成可追踪的学习资产
          </div>
        </div>

        <div className="app-actions" style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          <nav className="app-nav" style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {nav.map((n) => (
              <button key={n.id} onClick={() => { setPage(n.id); }}
                style={{ padding: "8px 18px", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13, fontWeight: page === n.id ? 600 : 400, background: page === n.id ? "var(--brand)" : "transparent", color: page === n.id ? "#fff" : "var(--text-secondary)", transition: "all 0.15s" }}>
                {n.label}
              </button>
            ))}
            {user && (
              <button onClick={handleLogout} title="退出登录"
                style={{ padding: "6px 10px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 12, background: "transparent", color: "var(--text-secondary)" }}>
                退出
              </button>
            )}
          </nav>
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

      {!user && (
        <div onClick={() => setPage("login")} style={{ padding: "10px 16px", background: "rgba(234, 179, 8, 0.08)", borderRadius: "var(--radius)", marginBottom: 16, fontSize: 13, cursor: "pointer", color: "#a16207", display: "flex", alignItems: "center", gap: 8, border: "1px solid rgba(234, 179, 8, 0.2)" }}>
          <span style={{ fontSize: 16 }}>ⓘ</span>
          当前为<strong style={{ margin: "0 4px" }}>游客模式</strong>，数据不区分身份。<u style={{ marginLeft: 4 }}>点击登录</u>以把错题、导学与复习绑到自己的账号。
        </div>
      )}

      {activeSid && page !== "tutor" && (
        <div onClick={() => setPage("tutor")} style={{ padding: "10px 16px", background: "var(--brand-bg)", borderRadius: "var(--radius)", marginBottom: 16, fontSize: 13, cursor: "pointer", color: "var(--brand)", display: "flex", alignItems: "center", gap: 8, border: "1px solid rgba(30,64,175,0.1)" }}>
          <span style={{ fontSize: 16 }}>▶</span> 有未完成的学习，点击继续
        </div>
      )}

      <main style={{ flex: 1, animation: "fadeIn 0.2s ease" }}>
        {page === "dashboard" && <DashboardPage onSelectQuestion={handleSelect} onNavigate={setPage} onSelectWeakPoint={handleWeakPointSelect} />}
        {page === "upload" && <ImageUpload grade={grade} onImage={handleUpload} loading={uploading} onConfirm={handleConfirm} />}
        {page === "knowmap" && <KnowMapPage grade={grade} focusWeakPoint={focusedWeakPoint} onSelectQuestion={handleSelect} />}
        {page === "login" && <LoginPage onLogin={handleLogin} />}
        {page === "account" && user && <AccountPage user={user} onUserUpdated={setUser} onOpenAdmin={() => setPage("adminAccounts")} />}
        {page === "share" && user && <SharePage />}
        {page === "adminAccounts" && user?.role === "admin" && <AdminAccountsPage />}
        {page === "adminOperations" && user?.role === "admin" && <AdminOperationsPage />}
        {page === "settings" && <SettingsPage />}
        {page === "tutor" && selectedQid && <TutorPage questionId={selectedQid} onSelectQuestion={handleSelect} />}
      </main>

      <footer style={{ marginTop: 48, padding: "24px 0", textAlign: "center", fontSize: 14, fontWeight: 500, color: "var(--text-secondary)", letterSpacing: 0.5, borderTop: "1px solid var(--border)" }}>
        <div>MathMind <span style={{ color: "var(--text-muted)", margin: "0 4px" }}>·</span> 把错题变成可追踪的学习资产</div>
        {filingLinks.length > 0 && <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "6px 14px", marginTop: 10, fontSize: 12, fontWeight: 400, letterSpacing: 0 }}>
          {filingLinks.map((filing) => <a key={filing.href} href={filing.href} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }}>{filing.number}</a>)}
        </div>}
      </footer>
    </div>
  );
}
