import { useState, useEffect } from "react";

const BASE = "/api/v1";
function authHeaders(): Record<string, string> {
  const t = localStorage.getItem("token");
  return t ? { Authorization: "Bearer " + t } : {};
}

export default function SettingsPage() {
  const [tab, setTab] = useState("model");
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    fetch(BASE + "/auth/me", { headers: authHeaders() }).then(r => r.json()).then(d => {
      if (d.id && d.id !== "u_default") setUser(d);
    }).catch(() => {});
  }, []);

  const tabs = [
    { id: "model", label: "模型配置" },
    { id: "password", label: "修改密码" },
  ];
  if (user?.role === "admin") tabs.push({ id: "users", label: "用户管理" });

  return (
    <div>
      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ padding: "6px 16px", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13,
              fontWeight: tab === t.id ? 600 : 400,
              background: tab === t.id ? "var(--brand)" : "transparent",
              color: tab === t.id ? "#fff" : "var(--text-secondary)" }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "model" && <ModelConfig />}
      {tab === "password" && <ChangePassword />}
      {tab === "users" && <UserManagement />}
    </div>
  );
}

function ModelConfig() {
  const [providers, setProviders] = useState<any[]>([]);
  const [config, setConfig] = useState<any>({ model_provider: "mock", model_name: "mock", api_key: "", base_url: "" });
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetch(BASE + "/settings/providers").then(r => r.json()).then(d => setProviders(d.providers || []));
    fetch(BASE + "/settings/models", { headers: authHeaders() }).then(r => r.json()).then(d => setConfig(d)).catch(() => {});
  }, []);

  const cp = providers.find(p => p.id === config.model_provider);

  const save = async () => {
    await fetch(BASE + "/settings/models", { method: "PUT", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(config) });
    setSaved(true); setTimeout(() => setSaved(false), 2000);
  };
  const testConn = async () => {
    setTesting(true); setTestResult(null);
    try {
      const r = await fetch(BASE + "/settings/models/test", { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(config) });
      setTestResult(await r.json());
    } catch (e: any) { setTestResult({ status: "error", message: e.message }); }
    setTesting(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 500 }}>
      <div>
        <label style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4, display: "block" }}>模型提供商</label>
        <select value={config.model_provider} onChange={e => { const p = providers.find(x => x.id === e.target.value); setConfig({ ...config, model_provider: e.target.value, model_name: p?.models?.[0] || "mock", base_url: p?.default_base_url || "" }); }}
          style={{ width: "100%", padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13, background: "var(--card)", color: "var(--text)" }}>
          {providers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      {cp && cp.models.length > 0 && (
        <div>
          <label style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4, display: "block" }}>模型名称</label>
          <select value={config.model_name} onChange={e => setConfig({ ...config, model_name: e.target.value })}
            style={{ width: "100%", padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13, background: "var(--card)", color: "var(--text)" }}>
            {cp.models.map((m: string) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      )}
      <div>
        <label style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4, display: "block" }}>API Key</label>
        <input type="password" value={config.api_key} onChange={e => setConfig({ ...config, api_key: e.target.value })}
          disabled={config.model_provider === "mock"}
          style={{ width: "100%", padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13, background: "var(--card)", color: "var(--text)" }} />
      </div>
      <div>
        <label style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4, display: "block" }}>API 地址</label>
        <input value={config.base_url} onChange={e => setConfig({ ...config, base_url: e.target.value })}
          disabled={config.model_provider === "mock"}
          style={{ width: "100%", padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13, background: "var(--card)", color: "var(--text)" }} />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={save} style={{ padding: "9px 24px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13, fontWeight: 500 }}>
          {saved ? "已保存" : "保存配置"}
        </button>
        <button onClick={testConn} disabled={testing || config.model_provider === "mock"}
          style={{ padding: "9px 24px", background: "var(--card)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13 }}>
          {testing ? "测试中..." : "测试连接"}
        </button>
      </div>
      {testResult && (
        <div style={{ padding: "10px 14px", borderRadius: "var(--radius-sm)", fontSize: 12,
          background: testResult.status === "ok" ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
          color: testResult.status === "ok" ? "var(--success)" : "var(--error)" }}>
          {testResult.message}
        </div>
      )}
    </div>
  );
}

export function ChangePassword() {
  const [oldPwd, setOldPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [msg, setMsg] = useState<{ status: string; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (newPwd.length < 6) { setMsg({ status: "error", text: "新密码至少6位" }); return; }
    if (newPwd !== confirmPwd) { setMsg({ status: "error", text: "两次密码不一致" }); return; }
    setLoading(true); setMsg(null);
    try {
      const r = await fetch(BASE + "/auth/password", {
        method: "PUT", headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
      });
      const d = await r.json();
      if (r.ok) { setMsg({ status: "ok", text: "密码已修改" }); setOldPwd(""); setNewPwd(""); setConfirmPwd(""); }
      else { setMsg({ status: "error", text: d.detail || "修改失败" }); }
    } catch (e: any) { setMsg({ status: "error", text: "网络错误" }); }
    setLoading(false);
  };

  const token = localStorage.getItem("token");
  if (!token) return <p style={{ fontSize: 13, color: "var(--text-muted)" }}>请先登录</p>;

  return (
    <div style={{ maxWidth: 400, display: "flex", flexDirection: "column", gap: 12 }}>
      <input type="password" placeholder="旧密码" value={oldPwd} onChange={e => setOldPwd(e.target.value)}
        style={{ padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13 }} />
      <input type="password" placeholder="新密码（至少6位）" value={newPwd} onChange={e => setNewPwd(e.target.value)}
        style={{ padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13 }} />
      <input type="password" placeholder="确认新密码" value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)}
        style={{ padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 13 }} />
      <button onClick={submit} disabled={loading}
        style={{ padding: "9px 24px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13, fontWeight: 500 }}>
        {loading ? "修改中..." : "修改密码"}
      </button>
      {msg && (
        <div style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", fontSize: 12,
          background: msg.status === "ok" ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
          color: msg.status === "ok" ? "var(--success)" : "var(--error)" }}>
          {msg.text}
        </div>
      )}
    </div>
  );
}

function UserManagement() {
  const [users, setUsers] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", name: "", school_level: "高中" });
  const [msg, setMsg] = useState<{ status: string; text: string } | null>(null);

  const load = async () => {
    try { const r = await fetch(BASE + "/admin/users", { headers: authHeaders() }); setUsers((await r.json()).users || []); } catch {}
  };
  useEffect(() => { load(); }, []);

  const createUser = async () => {
    if (form.username.length < 2) { setMsg({ status: "error", text: "用户名至少2位" }); return; }
    if (form.password.length < 6) { setMsg({ status: "error", text: "密码至少6位" }); return; }
    try {
      const r = await fetch(BASE + "/admin/users", {
        method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(form)
      });
      const d = await r.json();
      if (r.ok) { setMsg({ status: "ok", text: "用户 " + d.username + " 创建成功" }); setShowForm(false); setForm({ username: "", password: "", name: "", school_level: "高中" }); load(); }
      else { setMsg({ status: "error", text: d.detail || "创建失败" }); }
    } catch { setMsg({ status: "error", text: "网络错误" }); }
  };

  const deleteUser = async (id: string) => {
    if (!confirm("确定删除此用户？")) return;
    try { await fetch(BASE + "/admin/users/" + id, { method: "DELETE", headers: authHeaders() }); load(); } catch {}
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>共 {users.length} 个用户</span>
        <button onClick={() => setShowForm(!showForm)}
          style={{ padding: "6px 16px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 12 }}>
          {showForm ? "取消" : "创建用户"}
        </button>
      </div>

      {showForm && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16, padding: 12, background: "var(--bg)", borderRadius: "var(--radius-sm)" }}>
          <input placeholder="用户名" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })}
            style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 12 }} />
          <input placeholder="姓名" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
            style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 12 }} />
          <input type="password" placeholder="初始密码" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
            style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 12 }} />
          <select value={form.school_level} onChange={e => setForm({ ...form, school_level: e.target.value })}
            style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 12, background: "var(--card)" }}>
            <option value="初中">初中</option>
            <option value="高中">高中</option>
          </select>
          <button onClick={createUser}
            style={{ padding: "8px 16px", background: "var(--success)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 12, fontWeight: 500 }}>
            创建
          </button>
        </div>
      )}

      {msg && (
        <div style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", fontSize: 12, marginBottom: 12,
          background: msg.status === "ok" ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
          color: msg.status === "ok" ? "var(--success)" : "var(--error)" }}>
          {msg.text}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {users.filter(u => u.role !== "admin").map(u => (
          <div key={u.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)", fontSize: 12 }}>
            <div>
              <span style={{ fontWeight: 500 }}>{u.name}</span>
              <span style={{ color: "var(--text-muted)", marginLeft: 8 }}>{u.username}</span>
              <span style={{ color: "var(--text-muted)", marginLeft: 8 }}>{u.school_level}</span>
            </div>
            <button onClick={() => deleteUser(u.id)}
              style={{ padding: "3px 10px", background: "rgba(239,68,68,0.1)", color: "var(--error)", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 11 }}>
              删除
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
