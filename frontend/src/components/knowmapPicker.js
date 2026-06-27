export function formatNodePath(node, nodes) {
  const byId = new Map(nodes.map(n => [n.id, n]));
  const path = [node.name];
  let parent = node.parent_id ? byId.get(node.parent_id) : null;

  while (parent) {
    path.unshift(parent.name);
    parent = parent.parent_id ? byId.get(parent.parent_id) : null;
  }

  return path.join(" / ");
}

export function buildNodeSearchText(node, nodes) {
  return `${node.id} ${formatNodePath(node, nodes)}`.toLowerCase();
}

export function filterKnowMapNodes(nodes, query, selectedIds = [], limit = 5) {
  const selected = new Set(selectedIds);
  const keyword = query.trim().toLowerCase();

  return nodes
    .filter(node => node.level >= 2 && !selected.has(node.id))
    .filter(node => !keyword || buildNodeSearchText(node, nodes).includes(keyword))
    .slice(0, limit);
}

export function findBestWeakPointNode(nodes, weakPoint) {
  const keyword = weakPoint.trim().toLowerCase();
  if (!keyword) return undefined;

  return nodes
    .filter(node => node.level >= 2)
    .filter(node => buildNodeSearchText(node, nodes).includes(keyword))
    .sort((a, b) => b.level - a.level || a.id.localeCompare(b.id))[0];
}
