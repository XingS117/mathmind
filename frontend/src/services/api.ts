const BASE = "/api/v1";

function authHeader(): Record<string, string> {
  const t = typeof localStorage !== "undefined" ? localStorage.getItem("token") : null;
  return t ? { Authorization: "Bearer " + t } : {};
}

type Init = RequestInit & { json?: unknown };

async function apiFetch(path: string, init: Init = {}): Promise<Response> {
  const { json, headers, ...rest } = init;
  const h: Record<string, string> = { ...(headers as Record<string, string> | undefined), ...authHeader() };
  const body = json !== undefined ? JSON.stringify(json) : rest.body;
  if (json !== undefined && !h["Content-Type"]) h["Content-Type"] = "application/json";
  const r = await fetch(`${BASE}${path}`, { ...rest, body, headers: h });
  if (r.status === 401 && typeof localStorage !== "undefined") {
    // Token expired or invalid: drop it so caller reverts to guest mode.
    localStorage.removeItem("token");
  }
  return r;
}

async function apiJson<T>(path: string, init: Init = {}): Promise<T> {
  const r = await apiFetch(path, init);
  return r.json() as Promise<T>;
}

async function apiJsonOrThrow<T>(path: string, init: Init = {}): Promise<T> {
  const r = await apiFetch(path, init);
  const data = await r.json().catch(() => ({})) as { detail?: unknown } & T;
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "请求失败");
  return data;
}

export interface AnalysisResult {
  success: boolean;
  source?: string;
  text?: string;
  question_type?: string;
  knowledge_points?: string[];
  suggested_nodes?: string[];
  difficulty?: number;
  has_diagram?: boolean;
  key_insight?: string;
  raw_ocr_text?: string;
  confidence?: number;
  needs_human_review?: boolean;
  error?: string;
  suggestion?: string;
}

export interface ConfirmPayload {
  text: string;
  question_type: string;
  difficulty: number;
  knowledge_points: string[];
  has_diagram: boolean;
  raw_ocr_text: string;
  final_answer: string;
  solution_text: string;
  key_insight: string;
  knowmap_nodes: string[];
  analysis_source: string;
  analysis_confidence: number;
  needs_human_review: boolean;
}

export interface AuthUser {
  id: string;
  username?: string;
  name: string;
  role: string;
  school_level: string;
}

export interface AccountOverview {
  id: string;
  username: string;
  name: string;
  is_active: boolean;
  created_at: string | null;
  login_count: number;
  last_login_at: string | null;
  last_ip_masked: string | null;
  user_agent_family: string | null;
}

export async function login(username: string, password: string): Promise<{ token: string; user: AuthUser }> {
  const session = await apiJsonOrThrow<{ token: string; user: AuthUser }>("/auth/login", { method: "POST", json: { username, password } });
  return { ...session, user: { ...session.user, username } };
}

export async function register(username: string, password: string, name: string): Promise<{ user: AuthUser }> {
  return apiJsonOrThrow<{ user: AuthUser }>("/auth/register", { method: "POST", json: { username, password, name } });
}

export async function fetchMe(): Promise<AuthUser> {
  return apiJson<AuthUser>("/auth/me");
}

export async function updateProfile(name: string): Promise<AuthUser> {
  return apiJsonOrThrow<AuthUser>("/auth/profile", { method: "PUT", json: { name } });
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<{ message: string }> {
  return apiJsonOrThrow<{ message: string }>("/auth/password", {
    method: "PUT", json: { old_password: oldPassword, new_password: newPassword },
  });
}

export async function getAccountsOverview(): Promise<{ accounts: AccountOverview[] }> {
  return apiJsonOrThrow<{ accounts: AccountOverview[] }>("/admin/accounts-overview");
}

export async function setAccountActive(userId: string, isActive: boolean): Promise<{ id: string; is_active: boolean }> {
  return apiJsonOrThrow<{ id: string; is_active: boolean }>(`/admin/users/${userId}/status`, {
    method: "PATCH", json: { is_active: isActive },
  });
}

export async function resetAccountPassword(userId: string, newPassword: string): Promise<{ message: string }> {
  return apiJsonOrThrow<{ message: string }>(`/admin/users/${userId}/reset-password`, {
    method: "POST", json: { new_password: newPassword },
  });
}

export function isLoggedIn(): boolean {
  return typeof localStorage !== "undefined" && !!localStorage.getItem("token");
}

export function logout() {
  if (typeof localStorage !== "undefined") localStorage.removeItem("token");
}

export async function getKnowMapSummary(grade?: string) {
  const params = grade ? `?grade=${encodeURIComponent(grade)}` : "";
  return apiJson<any>(`/knowmap/summary${params}`);
}

export async function getKnowMapTree(grade?: string) {
  const params = grade ? `?grade=${encodeURIComponent(grade)}` : "";
  return apiJson<any>(`/knowmap/tree${params}`);
}

export async function getNodeQuestions(nodeId: string, grade?: string) {
  const params = grade ? `?grade=${encodeURIComponent(grade)}` : "";
  return apiJson<any>(`/knowmap/nodes/${nodeId}/questions${params}`);
}

export async function analyzeQuestion(files: File[], signal?: AbortSignal) {
  const fd = new FormData();
  files.forEach(f => fd.append("image", f));
  const r = await apiFetch(`/questions/analyze`, { method: "POST", body: fd, signal });
  if (!r.ok) {
    throw new Error(`analyze HTTP ${r.status}`);
  }
  return r.json() as Promise<AnalysisResult>;
}

export async function getOcrHealth(signal?: AbortSignal): Promise<{ status: string; message: string }> {
  const r = await apiFetch(`/health/ocr`, { signal });
  if (!r.ok) throw new Error(`ocr health ${r.status}`);
  return r.json();
}

export async function confirmQuestion(payload: ConfirmPayload) {
  return apiJson<any>("/questions/confirm", { method: "POST", json: payload });
}

function payloadFromAnalysis(analyzed: AnalysisResult): ConfirmPayload {
  return {
    text: analyzed.text || "",
    question_type: analyzed.question_type || "计算题",
    difficulty: analyzed.difficulty || 2,
    knowledge_points: analyzed.knowledge_points || [],
    has_diagram: analyzed.has_diagram || false,
    raw_ocr_text: analyzed.raw_ocr_text || "",
    final_answer: "",
    solution_text: "",
    key_insight: analyzed.key_insight || "",
    knowmap_nodes: [],
    analysis_source: analyzed.source || "manual",
    analysis_confidence: analyzed.confidence || 0,
    needs_human_review: false,
  };
}

export async function uploadQuestion(file: File) {
  const analyzed = await analyzeQuestion([file]);
  if (!analyzed.success) return analyzed;
  return confirmQuestion(payloadFromAnalysis(analyzed));
}

export async function uploadMultiple(files: File[]) {
  const analyzed = await analyzeQuestion(files);
  if (!analyzed.success) return analyzed;
  return confirmQuestion(payloadFromAnalysis(analyzed));
}

export async function createTutorSession(questionId: string) {
  return apiJson<any>("/tutor/session", { method: "POST", json: { question_id: questionId } });
}

export interface TutorDiagnosticSummary {
  completed_steps: number;
  total_steps: number;
  hints_used: number;
  stuck_steps: number[];
  weak_spots: string[];
  next_action: string;
}

export interface TutorMessageResult {
  type: string;
  reply: string;
  step_index: number;
  total_steps: number;
  hints_remaining: number;
  mastery_update?: number | null;
  variant_suggested?: string | null;
  variants?: string[];
  diagnostic_summary?: TutorDiagnosticSummary | null;
}

export async function sendTutorMessage(sessionId: string, message: string, intent = "answer") {
  return apiJson<TutorMessageResult>("/tutor/message", {
    method: "POST",
    json: { session_id: sessionId, message, intent },
  });
}

export async function getActiveSession() {
  return apiJson<any>("/tutor/sessions/active");
}

export async function getDashboard() {
  return apiJson<any>("/learn/dashboard");
}

export async function getHistory() {
  return apiJson<any>("/learn/history");
}

export async function getModelConfig() {
  return apiJson<any>("/settings/models");
}

export async function saveModelConfig(config: any) {
  return apiJson<any>("/settings/models", { method: "PUT", json: config });
}

export async function testConnection(config: any) {
  return apiJson<any>("/settings/models/test", { method: "POST", json: config });
}
