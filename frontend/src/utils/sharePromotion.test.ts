import { describe, expect, it } from "vitest";
import { buildPromotionText } from "./sharePromotion";

describe("buildPromotionText", () => {
  it("keeps the referral URL and both audiences", () => {
    const url = "https://example.com/?ref=mine";
    const text = buildPromotionText(url);

    expect(text).toContain(url);
    expect(text).toContain("学生");
    expect(text).toContain("家长");
  });
});
