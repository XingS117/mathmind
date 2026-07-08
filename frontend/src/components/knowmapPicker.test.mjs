import assert from "node:assert/strict";
import test from "node:test";
import { buildNodeSearchText, filterKnowMapNodes, findBestWeakPointNode, formatNodePath } from "./knowmapPicker.js";

const nodes = [
  { id: "bx1", name: "第1章 集合与常用逻辑用语", level: 2, parent_id: null },
  { id: "bx1_c1", name: "1.1 集合的概念", level: 3, parent_id: "bx1" },
  { id: "bx1_c2", name: "1.2 集合间的基本关系", level: 3, parent_id: "bx1" },
  { id: "bx1_c3", name: "1.3 集合的基本运算", level: 3, parent_id: "bx1" },
  { id: "bx2", name: "第2章 一元二次函数、方程和不等式", level: 2, parent_id: null },
  { id: "bx2_c3", name: "2.3 二次函数与一元二次方程、不等式", level: 3, parent_id: "bx2" },
];

test("formats a node with its parent chapter path", () => {
  assert.equal(
    formatNodePath(nodes[3], nodes),
    "第1章 集合与常用逻辑用语 / 1.3 集合的基本运算",
  );
});

test("builds search text from name, id, and parent path", () => {
  const text = buildNodeSearchText(nodes[5], nodes);
  assert.match(text, /bx2_c3/);
  assert.match(text, /第2章 一元二次函数/);
  assert.match(text, /2.3 二次函数/);
});

test("filters nodes by keyword and excludes selected ids", () => {
  const result = filterKnowMapNodes(nodes, "集合", ["bx1_c1"]);
  assert.deepEqual(result.map(n => n.id), ["bx1", "bx1_c2", "bx1_c3"]);
});

test("limits empty search to a small scannable set", () => {
  const result = filterKnowMapNodes(nodes, "", []);
  assert.equal(result.length, 5);
});

test("finds the best graph node for a weak point keyword", () => {
  assert.equal(findBestWeakPointNode(nodes, "二次函数")?.id, "bx2_c3");
  assert.equal(findBestWeakPointNode(nodes, "不存在")?.id, undefined);
});

test("findBestWeakPointNode falls back to token match for long weak points", () => {
  const longLabel = "利用二次函数的图像与坐标轴的交点关系";
  const hit = findBestWeakPointNode(nodes, longLabel);
  assert.ok(hit, "expected some node for long weak point");
  assert.match(hit.name, /二次函数|函数/);
});

test("findBestWeakPointNode returns undefined for unrelated long labels", () => {
  // Long label that shares no 2+ char token with any node text.
  const label = "物理力学中的斜面加速度问题";
  const hit = findBestWeakPointNode(nodes, label);
  assert.equal(hit, undefined);
});

import { browseChildren, browseTopLevelBooks } from "./knowmapPicker.js";

const bookNodes = [
  { id: "bx1", name: "必修一", level: 1, parent_id: null },
  { id: "bx2", name: "必修二", level: 1, parent_id: null },
  { id: "cz_bs1", name: "八年级上册", level: 1, parent_id: null },
  { id: "bx1_c1", name: "第1章", level: 2, parent_id: "bx1" },
  { id: "bx1_c1_s1", name: "1.1", level: 3, parent_id: "bx1_c1" },
];

test("browseTopLevelBooks returns level 1 books excluding selected", () => {
  const result = browseTopLevelBooks(bookNodes, ["bx2"]);
  assert.deepEqual(result.map(n => n.id), ["bx1", "cz_bs1"]);
});

test("browseTopLevelBooks with empty selection returns all books", () => {
  const result = browseTopLevelBooks(bookNodes);
  assert.equal(result.length, 3);
});

test("browseChildren returns direct children by parent id", () => {
  const result = browseChildren(bookNodes, "bx1");
  assert.deepEqual(result.map(n => n.id), ["bx1_c1"]);
});

test("browseChildren excludes already-selected ids", () => {
  const result = browseChildren(bookNodes, "bx1_c1", ["bx1_c1_s1"]);
  assert.deepEqual(result, []);
});
