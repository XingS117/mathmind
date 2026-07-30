import { useState } from "react";
import { AuthUser, updateProfile } from "../services/api";
import { ChangePassword } from "./SettingsPage";

interface Props {
  user: AuthUser;
  onUserUpdated: (user: AuthUser) => void;
  onOpenAdmin: () => void;
}

export default function AccountPage({ user, onUserUpdated, onOpenAdmin }: Props) {
  const [name, setName] = useState(user.name);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const saveName = async () => {
    setSaving(true);
    setMessage("");
    try {
      const updated = await updateProfile(name.trim());
      onUserUpdated(updated);
      setName(updated.name);
      setMessage("姓名已保存");
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <h2 style={{ fontSize: 18, margin: "0 0 20px", color: "var(--text)" }}>账户</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: 16, border: "1px solid var(--border)", borderRadius: "var(--radius)" }}>
        <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>用户名
          <input value={user.username || localStorage.getItem("username") || "—"} readOnly style={{ width: "100%", boxSizing: "border-box", marginTop: 5, padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg)", color: "var(--text-muted)" }} />
        </label>
        <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>显示姓名
          <input value={name} onChange={e => setName(e.target.value)} maxLength={32} style={{ width: "100%", boxSizing: "border-box", marginTop: 5, padding: "9px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", fontSize: 14 }} />
        </label>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={saveName} disabled={saving} style={{ padding: "9px 18px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13 }}>
            {saving ? "保存中..." : "保存姓名"}
          </button>
          {message && <span style={{ fontSize: 12, color: message === "姓名已保存" ? "var(--success)" : "var(--error)" }}>{message}</span>}
        </div>
      </div>

      {user.role === "admin" && <button onClick={onOpenAdmin} style={{ marginTop: 16, padding: "9px 18px", color: "var(--brand)", background: "var(--brand-bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", cursor: "pointer", fontSize: 13 }}>管理账户</button>}

      <section style={{ marginTop: 28 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12, color: "var(--text)" }}>修改密码</h3>
        <ChangePassword />
      </section>
    </div>
  );
}
