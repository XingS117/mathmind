import assert from "node:assert/strict";
import test from "node:test";
import { captureVisitOnce } from "./referralCapture.js";

function storage() {
  const values = new Map();
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
}

test("shares one pending referral visit between landing and registration", async () => {
  const session = storage();
  let calls = 0;
  let resolveVisit;
  const request = () => {
    calls += 1;
    return new Promise((resolve) => { resolveVisit = resolve; });
  };

  const landingCapture = captureVisitOnce("invite-code", session, request);
  const registrationCapture = captureVisitOnce("invite-code", session, request);
  await Promise.resolve();
  assert.equal(calls, 1);
  resolveVisit("rv_once");
  assert.equal(await landingCapture, "rv_once");
  assert.equal(await registrationCapture, "rv_once");
  assert.equal(session.getItem("referral_visit:invite-code"), "rv_once");
});
