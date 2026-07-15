export const SHARE_TITLE = "把每一道错题，变成下一次进步";

export function buildPromotionText(shareUrl: string): string {
  return `${SHARE_TITLE}。学生可整理错题、获得分步讲解；家长可看见学习积累和进步。一起试试数智学堂：${shareUrl}`;
}
