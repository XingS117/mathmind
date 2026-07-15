import assert from "node:assert/strict";
import test from "node:test";
import { dashboardViewState } from "./dashboardViewState.js";

test("shows an error state instead of an empty dashboard when the first load fails", () => {
  assert.equal(dashboardViewState({ loading: false, data: null, dashboardError: "加载失败" }), "initial_error");
});

test("keeps the loaded dashboard visible when only history fails", () => {
  assert.equal(dashboardViewState({ loading: false, data: { due_reviews: [] }, dashboardError: "" }), "ready");
});
