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

export declare function browseTopLevelBooks<T extends { id: string; level: number }>(
  nodes: T[],
  selectedIds?: string[]
): T[];

export declare function browseChildren<T extends { id: string; parent_id?: string | null }>(
  nodes: T[],
  parentId: string,
  selectedIds?: string[]
): T[];