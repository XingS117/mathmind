export const SHARE_TITLE = "把错题变成可追踪的学习资产";

export interface SharePosterContent {
  title: string;
  studentLine: string;
  parentLine: string;
  shareUrl: string;
}

export function buildPromotionText(shareUrl: string): string {
  return `${SHARE_TITLE}。学生上传一题，人工确认后开始分步陪练；家长可看见学习轨迹和后续复习。在线体验 MathMind：${shareUrl}`;
}

export function buildSharePosterContent(shareUrl: string): SharePosterContent {
  return {
    title: SHARE_TITLE,
    studentLine: "上传错题，分步弄懂关键方法",
    parentLine: "看见学习轨迹，安排后续复习",
    shareUrl,
  };
}
