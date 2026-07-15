import { useState } from "react";
import { login, register } from "../services/api";
import { isPasswordLengthValid, PASSWORD_LENGTH_MESSAGE } from "../utils/passwordPolicy";
import { isRegistrationUsernameValid, USERNAME_FORMAT_MESSAGE } from "../utils/usernamePolicy";

interface Props {
  onLogin: (token: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem("token");
  const usernameError = mode === "register" && username && !isRegistrationUsernameValid(username) ? USERNAME_FORMAT_MESSAGE : "";
  const passwordError = mode === "register" && password && !isPasswordLengthValid(password) ? PASSWORD_LENGTH_MESSAGE : "";
  const registrationReady = Boolean(username && name.trim() && password) && !usernameError && !passwordError;

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
    if (!username || !password || (mode === "register" && !name.trim())) {
      setError(mode === "register" ? "请输入用户名、显示姓名和密码" : "请输入用户名和密码");
      return;
    }
    if (mode === "register" && !isRegistrationUsernameValid(username)) {
      setError(USERNAME_FORMAT_MESSAGE);
      return;
    }
    if (mode === "register" && !isPasswordLengthValid(password)) {
      setError(PASSWORD_LENGTH_MESSAGE);
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (mode === "register") await register(username, password, name.trim());
      const session = await login(username, password);
      localStorage.setItem("username", username);
      onLogin(session.token);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "网络错误");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = { padding: "10px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 14 };
  return (
    <div style={{ maxWidth: 360, margin: "60px auto" }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20, textAlign: "center", color: "var(--text)" }}>
        {mode === "login" ? "登录" : "注册"}
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input placeholder={mode === "register" ? "用户名（3–32 位字母或数字）" : "用户名"} value={username} onChange={e => setUsername(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSubmit()} style={{ ...inputStyle, borderColor: usernameError ? "var(--error)" : "var(--border)" }} />
        {mode === "register" && <p style={{ fontSize: 12, color: usernameError ? "var(--error)" : "#64748b", margin: -8 }}>{usernameError || "用户名仅支持 3–32 位英文字母或数字"}</p>}
        {mode === "register" && <input placeholder="显示姓名" value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSubmit()} style={inputStyle} />}
        <input type="password" placeholder={mode === "register" ? "密码（8–128 位）" : "密码"} value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSubmit()} style={{ ...inputStyle, borderColor: passwordError ? "var(--error)" : "var(--border)" }} />
        {mode === "register" && password && <p style={{ fontSize: 12, color: passwordError ? "var(--error)" : "var(--success)", margin: -8 }}>{passwordError || "密码长度符合要求"}</p>}
        {error && <p style={{ fontSize: 12, color: "var(--error)", margin: 0 }}>{error}</p>}
        <button onClick={handleSubmit} disabled={loading || (mode === "register" && !registrationReady)}
          style={{ padding: "10px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: loading || (mode === "register" && !registrationReady) ? "not-allowed" : "pointer", fontSize: 14, fontWeight: 500, opacity: loading || (mode === "register" && !registrationReady) ? 0.55 : 1 }}>
          {loading ? (mode === "login" ? "登录中..." : "注册中...") : (mode === "login" ? "登录" : "注册并登录")}
        </button>
        <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
          style={{ padding: "8px", background: "transparent", color: "var(--brand)", border: "none", cursor: "pointer", fontSize: 13 }}>
          {mode === "login" ? "没有账户？注册" : "已有账户？登录"}
        </button>
      </div>
    </div>
  );
}
