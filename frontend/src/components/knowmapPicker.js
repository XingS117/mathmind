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

  const candidates = nodes.filter(node => node.level >= 2);
  const withText = candidates.map(node => ({
    node,
    text: buildNodeSearchText(node, nodes),
  }));

  // 1) Exact substring match on the full weak point label, prefer the
  //    deepest (most specific) matching node.
  const directHits = withText
    .filter(({ text }) => text.includes(keyword))
    .sort((a, b) => b.node.level - a.node.level || a.node.id.localeCompare(b.node.id));
  if (directHits.length > 0) return directHits[0].node;

  // 2) Fall back to tokenised matching so long dashboard weak points
  //    ("利用矩形性质得到垂直关系，通过三角函数设参数表示边长...") can
  //    still light up a node when any 2+ char noun-like token matches
  //    (P1-DASHBOARD-01).
  const rough = keyword
    .split(/[\s，。,、；;：:（）()？?！!的与和或]+/)
    .map(t => t.trim())
    .filter(t => t.length >= 2);
  if (rough.length === 0) return undefined;

  // Expand each rough chunk into its 2-4 char sliding windows so a
  // chunk like "利用二次函数" (6 chars) can still match a node whose
  // text contains "二次函数".
  const tokenSet = new Set();
  for (const chunk of rough) {
    for (let n = 2; n <= 4; n += 1) {
      for (let i = 0; i + n <= chunk.length; i += 1) {
        tokenSet.add(chunk.slice(i, i + n));
      }
    }
  }
  const tokens = [...tokenSet];
  if (tokens.length === 0) return undefined;

  let best = undefined;
  let bestScore = 0;
  for (const { node, text } of withText) {
    let score = 0;
    for (const tok of tokens) {
      if (text.includes(tok)) score += tok.length;
    }
    if (score === 0) continue;
    if (
      score > bestScore ||
      (score === bestScore && best && node.level > best.level)
    ) {
      bestScore = score;
      best = node;
    }
  }
  return best;
}

export function browseTopLevelBooks(nodes, selectedIds = []) {
  const selected = new Set(selectedIds);
  return nodes
    .filter(node => node.level === 1 && !selected.has(node.id));
}

export function browseChildren(nodes, parentId, selectedIds = []) {
  const selected = new Set(selectedIds);
  return nodes
    .filter(node => node.parent_id === parentId && !selected.has(node.id));
}
