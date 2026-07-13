import { useEffect, useState } from "react";
import { AccountOverview, getAccountsOverview, resetAccountPassword, setAccountActive } from "../services/api";

function formatTime(value: string | null) {
  return value ? value.replace("T", " ").slice(0, 16) : "—";
}

export default function AdminAccountsPage() {
  const [accounts, setAccounts] = useState<AccountOverview[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

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

  const resetPassword = async (account: AccountOverview) => {
    const password = window.prompt(`为「${account.username}」设置新密码（8-128位）`);
    if (!password) return;
    if (!window.confirm(`确定重置「${account.username}」的密码？`)) return;
    try {
      await resetAccountPassword(account.id, password);
      setMessage("密码已重置");
    } catch (e: unknown) { setMessage(e instanceof Error ? e.message : "重置失败"); }
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
              <td><div style={{ display: "flex", gap: 6 }}><button onClick={() => void toggle(account)} style={{ padding: "4px 8px", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer", background: "var(--card)", color: account.is_active ? "var(--error)" : "var(--success)" }}>{account.is_active ? "停用" : "启用"}</button><button onClick={() => void resetPassword(account)} style={{ padding: "4px 8px", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer", background: "var(--card)" }}>重置密码</button></div></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
