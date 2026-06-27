export interface KnowMapPickerNode {
  id: string;
  name: string;
  level: number;
  parent_id: string | null;
  children?: string[];
}

export function formatNodePath(node: KnowMapPickerNode, nodes: KnowMapPickerNode[]): string;

export function buildNodeSearchText(node: KnowMapPickerNode, nodes: KnowMapPickerNode[]): string;

export function filterKnowMapNodes(
  nodes: KnowMapPickerNode[],
  query: string,
  selectedIds?: string[],
  limit?: number,
): KnowMapPickerNode[];

export function findBestWeakPointNode(
  nodes: KnowMapPickerNode[],
  weakPoint: string,
): KnowMapPickerNode | undefined;
