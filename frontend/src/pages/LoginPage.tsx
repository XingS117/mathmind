import { useEffect, useState } from "react";
import { checkUsernameAvailability, login, register } from "../services/api";
import { isPasswordLengthValid, PASSWORD_LENGTH_MESSAGE } from "../utils/passwordPolicy";
import { isRegistrationUsernameValid, USERNAME_FORMAT_MESSAGE } from "../utils/usernamePolicy";
import { canSubmitRegistration, usernameAvailabilityMessage, UsernameAvailabilityStatus } from "../utils/registrationAvailability";

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
  const [usernameStatus, setUsernameStatus] = useState<UsernameAvailabilityStatus>("idle");
  const token = localStorage.getItem("token");
  const usernameError = mode === "register" && username && !isRegistrationUsernameValid(username) ? USERNAME_FORMAT_MESSAGE : "";
  const nameError = mode === "register" && name && name.trim().length > 32 ? "显示姓名长度需为 1-32 位" : "";
  const passwordError = mode === "register" && password && !isPasswordLengthValid(password) ? PASSWORD_LENGTH_MESSAGE : "";
  const usernameValid = mode === "register" && Boolean(username) && !usernameError;
  const nameValid = mode === "register" && Boolean(name.trim()) && !nameError;
  const passwordValid = mode === "register" && Boolean(password) && !passwordError;
  const registrationReady = canSubmitRegistration({ usernameValid, usernameStatus, nameValid, passwordValid });
  const usernameHint = usernameError || usernameAvailabilityMessage(usernameStatus) || "用户名仅支持 3–32 位英文字母或数字";
  const usernameHintColor = usernameError || usernameStatus === "taken" || usernameStatus === "error"
    ? "var(--error)"
    : usernameStatus === "available" ? "var(--success)" : "#64748b";

  useEffect(() => {
    if (mode !== "register" || !username || !isRegistrationUsernameValid(username)) {
      setUsernameStatus("idle");
      return;
    }
    const controller = new AbortController();
    setUsernameStatus("checking");
    const timer = window.setTimeout(async () => {
      try {
        const available = await checkUsernameAvailability(username, controller.signal);
        if (!controller.signal.aborted) setUsernameStatus(available ? "available" : "taken");
      } catch (e: unknown) {
        if (!controller.signal.aborted && !(e instanceof DOMException && e.name === "AbortError")) {
          setUsernameStatus("error");
        }
      }
    }, 400);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [mode, username]);

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
    if (mode === "register" && !name.trim()) {
      setError("请输入显示姓名");
      return;
    }
    if (mode === "register" && name.trim().length > 32) {
      setError("显示姓名长度需为 1-32 位");
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
      const message = e instanceof Error ? e.message : "网络错误";
      if (mode === "register" && message === "用户名已存在") {
        setUsernameStatus("taken");
        setError("");
      } else {
        setError(message);
      }
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
        <input placeholder={mode === "register" ? "用户名（3–32 位字母或数字）" : "用户名"} value={username} onChange={e => { setUsername(e.target.value); setUsernameStatus("idle"); }} onKeyDown={e => e.key === "Enter" && handleSubmit()} style={{ ...inputStyle, borderColor: usernameError || usernameStatus === "taken" || usernameStatus === "error" ? "var(--error)" : "var(--border)" }} />
        {mode === "register" && <p style={{ fontSize: 12, color: usernameHintColor, margin: -8 }}>{usernameHint}</p>}
        {mode === "register" && <input placeholder="显示姓名（1–32 位）" value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSubmit()} style={{ ...inputStyle, borderColor: nameError ? "var(--error)" : "var(--border)" }} />}
        {mode === "register" && nameError && <p style={{ fontSize: 12, color: "var(--error)", margin: -8 }}>{nameError}</p>}
        <input type="password" placeholder={mode === "register" ? "密码（8–128 位）" : "密码"} value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSubmit()} style={{ ...inputStyle, borderColor: passwordError ? "var(--error)" : "var(--border)" }} />
        {mode === "register" && password && <p style={{ fontSize: 12, color: passwordError ? "var(--error)" : "var(--success)", margin: -8 }}>{passwordError || "密码长度符合要求"}</p>}
        {error && <p style={{ fontSize: 12, color: "var(--error)", margin: 0 }}>{error}</p>}
        <button onClick={handleSubmit} disabled={loading || (mode === "register" && !registrationReady)}
          style={{ padding: "10px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: loading || (mode === "register" && !registrationReady) ? "not-allowed" : "pointer", fontSize: 14, fontWeight: 500, opacity: loading || (mode === "register" && !registrationReady) ? 0.55 : 1 }}>
          {loading ? (mode === "login" ? "登录中..." : "注册中...") : (mode === "login" ? "登录" : "注册并登录")}
        </button>
        <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); setUsernameStatus("idle"); }}
          style={{ padding: "8px", background: "transparent", color: "var(--brand)", border: "none", cursor: "pointer", fontSize: 13 }}>
          {mode === "login" ? "没有账户？注册" : "已有账户？登录"}
        </button>
      </div>
    </div>
  );
}
