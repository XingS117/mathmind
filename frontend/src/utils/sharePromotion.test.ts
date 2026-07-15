import { describe, expect, it } from "vitest";
import { buildPromotionText, buildSharePosterContent } from "./sharePromotion";

describe("buildPromotionText", () => {
  it("keeps the referral URL and both audiences", () => {
    const url = "https://example.com/?ref=mine";
    const text = buildPromotionText(url);

    expect(text).toContain(url);
    expect(text).toContain("学生");
    expect(text).toContain("家长");
  });

  it("builds poster content from the caller referral URL", () => {
    expect(buildSharePosterContent("https://example.com/?ref=mine")).toEqual({
      title: "把每一道错题，变成下一次进步",
      studentLine: "整理错题，获得分步讲解",
      parentLine: "看见学习积累和进步",
      shareUrl: "https://example.com/?ref=mine",
    });
  });
});
