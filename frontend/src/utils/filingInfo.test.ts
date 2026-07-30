import { expect, it } from "vitest";
import { ICP_FILING, POLICE_FILING } from "./filingInfo";

it("does not publish a fallback filing identity", () => {
  expect(ICP_FILING).toBeNull();
  expect(POLICE_FILING).toBeNull();
});
