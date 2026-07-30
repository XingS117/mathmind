"""SVG generation from structured geometry data."""
def generate_svg(diagram: dict) -> str:
    """Generate SVG markup from geometry structure."""
    points = diagram.get("points", {})
    lines = diagram.get("lines", [])
    svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" style="background:#fff">']
    for line in lines:
        a = points.get(line["from"])
        b = points.get(line["to"])
        if not a or not b:
            continue
        dash = "" if line.get("style") == "solid" else 'stroke-dasharray="5,5"'
        x1, y1 = a["x"] * 50, a["y"] * 50
        x2, y2 = b["x"] * 50, b["y"] * 50
        svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="2" {dash}/>')
        label = line.get("label", "")
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            svg_parts.append(f'<text x="{mx}" y="{my - 5}" text-anchor="middle" fill="#e74c3c" font-size="14">{label}</text>')
    for pid, pt in points.items():
        x, y = pt["x"] * 50, pt["y"] * 50
        label = pt.get("label", pid)
        svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#333"/>')
        svg_parts.append(f'<text x="{x + 8}" y="{y - 8}" font-size="14" fill="#333">{label}</text>')
    annotations = diagram.get("annotations", [])
    for ann in annotations:
        at = ann.get("at", [])
        text = ann.get("text", "")
        if at and text:
            pt = points.get(at[0])
            if pt:
                svg_parts.append(f'<text x="{pt["x"] * 50 + 10}" y="{pt["y"] * 50 + 20}" font-size="12" fill="#2980b9">{text}</text>')
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)
