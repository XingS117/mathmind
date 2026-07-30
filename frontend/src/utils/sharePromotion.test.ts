import { describe, expect, it } from "vitest";
import { buildPromotionText, buildSharePosterContent } from "./sharePromotion";

describe("buildPromotionText", () => {
  it("keeps the referral URL and both audiences", () => {
    const url = "https://example.com/?ref=mine";
    const text = buildPromotionText(url);

    expect(text).toContain(url);
    expect(text).toContain("学生");
    expect(text).toContain("家长");
    expect(text).toContain("人工确认");
    expect(text).toContain("复习");
  });

  it("builds poster content from the caller referral URL", () => {
    expect(buildSharePosterContent("https://example.com/?ref=mine")).toEqual({
      title: "把错题变成可追踪的学习资产",
      studentLine: "上传错题，分步弄懂关键方法",
      parentLine: "看见学习轨迹，安排后续复习",
      shareUrl: "https://example.com/?ref=mine",
    });
  });
});
