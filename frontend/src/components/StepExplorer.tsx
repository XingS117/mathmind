interface Step {
  step_number: number;
  description: string;
  latex: string;
  result: string;
}

interface Props {
  steps: Step[];
}

export default function StepExplorer({ steps }: Props) {
  return (
    <div>
      {steps.map((step) => (
        <details key={step.step_number} style={{ marginBottom: 8, border: "1px solid #e0e0e0", borderRadius: 8, overflow: "hidden" }}>
          <summary style={{ padding: "10px 14px", background: "#f8f9fa", cursor: "pointer", fontWeight: 600, fontSize: 14 }}>
            Step {step.step_number}: {step.description}
          </summary>
          <div style={{ padding: "10px 14px", background: "#fff" }}>
            {step.latex && (
              <p style={{ fontFamily: "monospace", background: "#f4f4f4", padding: 8, borderRadius: 4, fontSize: 13 }}>
                {step.latex}
              </p>
            )}
            {step.result && (
              <p style={{ color: "#2ecc71", fontWeight: 600, fontSize: 14, margin: 0 }}>
                = {step.result}
              </p>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}