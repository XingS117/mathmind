const BASE = "/api/v1";

export interface AnalysisResult {
  success: boolean;
  source?: string;
  text?: string;
  question_type?: string;
  knowledge_points?: string[];
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

export async function getKnowMapSummary(grade?: string) {
  const params = grade ? `?grade=${encodeURIComponent(grade)}` : "";
  const r = await fetch(`${BASE}/knowmap/summary${params}`);
  return r.json();
}

export async function getKnowMapTree(grade?: string) {
  const params = grade ? `?grade=${encodeURIComponent(grade)}` : "";
  const r = await fetch(`${BASE}/knowmap/tree${params}`);
  return r.json();
}

export async function getNodeQuestions(nodeId: string, grade?: string) {
  const params = grade ? `?grade=${encodeURIComponent(grade)}` : "";
  const r = await fetch(`${BASE}/knowmap/nodes/${nodeId}/questions${params}`);
  return r.json();
}

export async function analyzeQuestion(files: File[]) {
  const fd = new FormData();
  files.forEach(f => fd.append("image", f));
  const r = await fetch(`${BASE}/questions/analyze`, { method: "POST", body: fd });
  return r.json() as Promise<AnalysisResult>;
}

export async function confirmQuestion(payload: ConfirmPayload) {
  const r = await fetch(`${BASE}/questions/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
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
  const r = await fetch(`${BASE}/tutor/session`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId }),
  });
  return r.json();
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
  const r = await fetch(`${BASE}/tutor/message`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, intent }),
  });
  return r.json() as Promise<TutorMessageResult>;
}

export async function getActiveSession() {
  const r = await fetch(`${BASE}/tutor/sessions/active`);
  return r.json();
}

export async function getDashboard() {
  const r = await fetch(`${BASE}/learn/dashboard`);
  return r.json();
}

export async function getHistory() {
  const r = await fetch(`${BASE}/learn/history`);
  return r.json();
}

export async function getModelConfig() {
  const r = await fetch(`${BASE}/settings/models`);
  return r.json();
}

export async function saveModelConfig(config: any) {
  const r = await fetch(`${BASE}/settings/models`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return r.json();
}

export async function testConnection(config: any) {
  const r = await fetch(`${BASE}/settings/models/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return r.json();
}
