interface DiagramData {
  type: string;
  points: Record<string, { x: number; y: number; label: string }>;
  lines: { from: string; to: string; style: string; label?: string }[];
}

interface Props {
  diagram: DiagramData | null;
}

export default function DiagramView({ diagram }: Props) {
  if (!diagram || Object.keys(diagram.points).length === 0) return null;

  const scale = 50;
  const pts = diagram.points;
  const allX = Object.values(pts).map((p) => p.x);
  const allY = Object.values(pts).map((p) => p.y);
  const padding = 1;
  const minX = Math.min(...allX) - padding;
  const maxX = Math.max(...allX) + padding;
  const minY = Math.min(...allY) - padding;
  const maxY = Math.max(...allY) + padding;
  const w = (maxX - minX) * scale;
  const h = (maxY - minY) * scale;

  return (
    <div style={{ textAlign: "center", margin: "16px 0" }}>
      <svg viewBox={`${minX * scale} ${minY * scale} ${w || 200} ${h || 200}`}
        style={{ maxWidth: "100%", background: "#fff", border: "1px solid #eee", borderRadius: 8 }}>
        {diagram.lines.map((line, i) => {
          const a = pts[line.from];
          const b = pts[line.to];
          if (!a || !b) return null;
          return (
            <g key={i}>
              <line x1={a.x * scale} y1={a.y * scale}
                x2={b.x * scale} y2={b.y * scale}
                stroke="#333" strokeWidth={2}
                strokeDasharray={line.style === "dashed" ? "5,5" : undefined} />
              {line.label && (
                <text x={(a.x + b.x) / 2 * scale} y={(a.y + b.y) / 2 * scale - 5}
                  textAnchor="middle" fill="#e74c3c" fontSize={14}>{line.label}</text>
              )}
            </g>
          );
        })}
        {Object.entries(pts).map(([id, pt]) => (
          <g key={id}>
            <circle cx={pt.x * scale} cy={pt.y * scale} r={4} fill="#333" />
            <text x={pt.x * scale + 8} y={pt.y * scale - 8} fontSize={14} fill="#333">
              {pt.label || id}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}