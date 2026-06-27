import StepExplorer from "./StepExplorer";
import DiagramView from "./DiagramView";

interface SolutionData {
  question_id: string;
  ocr_result: {
    text: string;
    latex: string;
    question_type: string;
    has_diagram: boolean;
    knowledge_points: string[];
  };
  solution: {
    steps: { step_number: number; description: string; latex: string; result: string }[];
    final_answer: string;
    method: string;
    difficulty: number;
    knowledge_points: string[];
    common_mistakes: string[];
  };
  diagram: {
    type: string;
    points: Record<string, { x: number; y: number; label: string }>;
    lines: { from: string; to: string; style: string; label?: string }[];
  } | null;
}

function Tag({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 999,
      fontSize: 12, fontWeight: 600, color: "#fff", background: color, marginRight: 6, marginBottom: 4
    }}>
      {label}
    </span>
  );
}

export default function SolutionView({ data }: { data: SolutionData }) {
  const { ocr_result: ocr, solution: sol, diagram } = data;
  const diffColor = sol.difficulty <= 2 ? "#2ecc71" : sol.difficulty <= 4 ? "#f39c12" : "#e74c3c";

  return (
    <div style={{ marginTop: 24 }}>
      {/* Question type & difficulty */}
      <div style={{ marginBottom: 16 }}>
        <Tag label={ocr.question_type || "未知题型"} color="#3498db" />
        <Tag label={`难度 ${sol.difficulty}/5`} color={diffColor} />
      </div>

      {/* Knowledge points */}
      <div style={{ marginBottom: 16 }}>
        {sol.knowledge_points.map((kp, i) => (
          <Tag key={i} label={kp} color="#9b59b6" />
        ))}
      </div>

      {/* OCR text */}
      <div style={{ background: "#f8f9fa", padding: 16, borderRadius: 8, marginBottom: 16 }}>
        <p style={{ margin: "0 0 4px", fontSize: 12, color: "#999", fontWeight: 600 }}>题目</p>
        <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6 }}>{ocr.text}</p>
      </div>

      {/* Method */}
      <p style={{ fontSize: 13, color: "#666", marginBottom: 12 }}>
        解法：<strong>{sol.method}</strong>
      </p>

      {/* Steps */}
      <h3 style={{ fontSize: 16, margin: "16px 0 8px" }}>解题步骤</h3>
      <StepExplorer steps={sol.steps} />

      {/* Final answer */}
      <div style={{
        marginTop: 16, padding: 16, background: "#eafaf1", borderRadius: 8,
        border: "1px solid #d5f5e3"
      }}>
        <p style={{ margin: "0 0 4px", fontSize: 12, color: "#27ae60", fontWeight: 600 }}>答案</p>
        <p style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#1e8449" }}>{sol.final_answer}</p>
      </div>

      {/* Common mistakes */}
      {sol.common_mistakes.length > 0 && (
        <div style={{ marginTop: 16, padding: 16, background: "#fdedec", borderRadius: 8, border: "1px solid #fadbd8" }}>
          <p style={{ margin: "0 0 8px", fontSize: 12, color: "#c0392b", fontWeight: 600 }}>常见易错点</p>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {sol.common_mistakes.map((m, i) => (
              <li key={i} style={{ fontSize: 13, color: "#e74c3c", marginBottom: 4 }}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Diagram */}
      {diagram && <DiagramView diagram={diagram} />}
    </div>
  );
}