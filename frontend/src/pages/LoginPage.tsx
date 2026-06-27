import { useState } from "react";

interface Props {
  onLogin: (token: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem("token");

  if (token) {
    return (
      <div style={{ maxWidth: 400, margin: "60px auto", textAlign: "center" }}>
        <p style={{ fontSize: 14, marginBottom: 16, color: "var(--text)" }}>您已登录</p>
        <button onClick={() => { localStorage.removeItem("token"); window.location.reload(); }}
          style={{ padding: "10px 28px", background: "var(--error)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 14 }}>
          退出登录
        </button>
      </div>
    );
  }

  const handleSubmit = async () => {
    if (!username || !password) { setError("请输入用户名和密码"); return; }
    setLoading(true); setError("");
    try {
      const r = await fetch("/api/v1/auth/login", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username, password })
      });
      const d = await r.json();
      if (!r.ok) { setError(d.detail || "登录失败"); setLoading(false); return; }
      onLogin(d.token);
    } catch (e: any) { setError("网络错误"); setLoading(false); }
  };

  return (
    <div style={{ maxWidth: 360, margin: "60px auto" }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20, textAlign: "center", color: "var(--text)" }}>登录</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSubmit()}
          style={{ padding: "10px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 14 }} />
        <input type="password" placeholder="密码" value={password} onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSubmit()}
          style={{ padding: "10px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 14 }} />
        {error && <p style={{ fontSize: 12, color: "var(--error)", margin: 0 }}>{error}</p>}
        <button onClick={handleSubmit} disabled={loading}
          style={{ padding: "10px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 14, fontWeight: 500 }}>
          {loading ? "登录中..." : "登录"}
        </button>
      </div>
    </div>
  );
}