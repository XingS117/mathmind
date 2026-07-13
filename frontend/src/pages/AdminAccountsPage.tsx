import { useEffect, useState } from "react";
import { AccountOverview, getAccountsOverview, resetAccountPassword, setAccountActive } from "../services/api";

function formatTime(value: string | null) {
  return value ? value.replace("T", " ").slice(0, 16) : "—";
}

export default function AdminAccountsPage() {
  const [accounts, setAccounts] = useState<AccountOverview[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [resetTarget, setResetTarget] = useState<AccountOverview | null>(null);
  const [newPassword, setNewPassword] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setAccounts((await getAccountsOverview()).accounts);
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "账户列表加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  const toggle = async (account: AccountOverview) => {
    const action = account.is_active ? "停用" : "启用";
    if (!window.confirm(`确定${action}账户「${account.username}」？`)) return;
    try {
      await setAccountActive(account.id, !account.is_active);
      setMessage(`账户已${action}`);
      await load();
    } catch (e: unknown) { setMessage(e instanceof Error ? e.message : `${action}失败`); }
  };

  const submitResetPassword = async () => {
    if (!resetTarget) return;
    if (newPassword.length < 8) {
      setMessage("新密码至少 8 位");
      return;
    }
    if (!window.confirm(`确定重置「${resetTarget.username}」的密码？`)) return;
    try {
      await resetAccountPassword(resetTarget.id, newPassword);
      setMessage("密码已重置");
      setResetTarget(null);
      setNewPassword("");
    } catch (e: unknown) { setMessage(e instanceof Error ? e.message : "重置失败"); }
  };

  const cancelResetPassword = () => {
    setResetTarget(null);
    setNewPassword("");
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div><h2 style={{ fontSize: 18, margin: 0, color: "var(--text)" }}>账户管理</h2><span style={{ fontSize: 12, color: "var(--text-muted)" }}>登录次数与最近一次成功登录信息</span></div>
        <button onClick={() => void load()} style={{ padding: "7px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--card)", cursor: "pointer" }}>刷新</button>
      </div>
      {message && <p style={{ fontSize: 13, color: "var(--error)" }}>{message}</p>}
      {loading ? <p style={{ fontSize: 13, color: "var(--text-muted)" }}>加载中...</p> : (
        <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: "var(--radius)" }}>
          <table style={{ width: "100%", minWidth: 840, borderCollapse: "collapse", fontSize: 12 }}>
            <thead><tr style={{ textAlign: "left", background: "var(--bg)", color: "var(--text-secondary)" }}><th style={{ padding: 10 }}>账户</th><th>状态</th><th>登录次数</th><th>最近登录</th><th>IP</th><th>设备</th><th>操作</th></tr></thead>
            <tbody>{accounts.map(account => <tr key={account.id} style={{ borderTop: "1px solid var(--border)" }}>
              <td style={{ padding: 10 }}><strong>{account.name}</strong><div style={{ color: "var(--text-muted)", marginTop: 3 }}>{account.username}</div></td>
              <td><span style={{ color: account.is_active ? "var(--success)" : "var(--error)" }}>{account.is_active ? "正常" : "已停用"}</span></td>
              <td>{account.login_count}</td><td>{formatTime(account.last_login_at)}</td><td>{account.last_ip_masked || "—"}</td><td>{account.user_agent_family || "—"}</td>
              <td><div style={{ display: "flex", gap: 6 }}><button onClick={() => void toggle(account)} style={{ padding: "4px 8px", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer", background: "var(--card)", color: account.is_active ? "var(--error)" : "var(--success)" }}>{account.is_active ? "停用" : "启用"}</button><button onClick={() => { setResetTarget(account); setNewPassword(""); }} style={{ padding: "4px 8px", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer", background: "var(--card)" }}>重置密码</button></div></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
      {resetTarget && <div role="dialog" aria-modal="true" aria-label="重置密码" style={{ position: "fixed", inset: 0, zIndex: 10, display: "grid", placeItems: "center", padding: 20, background: "rgba(0,0,0,0.35)" }}>
        <div style={{ width: "min(100%, 360px)", padding: 20, background: "var(--card)", borderRadius: "var(--radius)", boxShadow: "0 12px 36px rgba(0,0,0,0.2)" }}>
          <h3 style={{ margin: "0 0 8px", fontSize: 16 }}>重置密码</h3>
          <p style={{ margin: "0 0 14px", fontSize: 13, color: "var(--text-secondary)" }}>为「{resetTarget.username}」设置新的登录密码。</p>
          <input type="password" autoComplete="new-password" autoFocus placeholder="新密码（至少 8 位）" value={newPassword} onChange={e => setNewPassword(e.target.value)} style={{ width: "100%", boxSizing: "border-box", padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }} />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
            <button onClick={cancelResetPassword} style={{ padding: "8px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--card)", cursor: "pointer" }}>取消</button>
            <button onClick={() => void submitResetPassword()} style={{ padding: "8px 14px", border: "none", borderRadius: "var(--radius-sm)", background: "var(--brand)", color: "#fff", cursor: "pointer" }}>确认重置</button>
          </div>
        </div>
      </div>}
    </div>
  );
}
