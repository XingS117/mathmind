import assert from "node:assert/strict";
import test from "node:test";

import { jsonOrThrow } from "./apiResponse.js";

test("503 响应会携带接口错误进入失败分支", async () => {
  await assert.rejects(
    () => jsonOrThrow(new Response(JSON.stringify({ detail: "服务暂不可用" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    })),
    { message: "服务暂不可用" },
  );
});

test("成功响应返回 JSON 数据", async () => {
  const data = await jsonOrThrow(new Response(JSON.stringify({ status: "ok" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  }));

  assert.deepEqual(data, { status: "ok" });
});

test("422 验证列表会返回具体字段错误", async () => {
  await assert.rejects(
    () => jsonOrThrow(new Response(JSON.stringify({ detail: [{ msg: "Value error, 用户名仅支持 3–32 位英文字母或数字" }] }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    })),
    { message: "用户名仅支持 3–32 位英文字母或数字" },
  );
});
