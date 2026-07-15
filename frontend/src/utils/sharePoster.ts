import QRCode from "qrcode";
import { buildSharePosterContent } from "./sharePromotion";

const POSTER_WIDTH = 1080;
const POSTER_HEIGHT = 1520;

function roundedRect(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  context.beginPath();
  context.roundRect(x, y, width, height, radius);
  context.closePath();
}

function drawWrappedText(context: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth: number, lineHeight: number) {
  let line = "";
  let currentY = y;
  for (const character of text) {
    const next = line + character;
    if (line && context.measureText(next).width > maxWidth) {
      context.fillText(line, x, currentY);
      line = character;
      currentY += lineHeight;
    } else {
      line = next;
    }
  }
  if (line) context.fillText(line, x, currentY);
  return currentY;
}

export async function createSharePoster(shareUrl: string): Promise<Blob> {
  const content = buildSharePosterContent(shareUrl);
  const canvas = document.createElement("canvas");
  canvas.width = POSTER_WIDTH;
  canvas.height = POSTER_HEIGHT;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("海报生成失败，请重试");

  const background = context.createLinearGradient(0, 0, POSTER_WIDTH, POSTER_HEIGHT);
  background.addColorStop(0, "#173fba");
  background.addColorStop(0.58, "#285ed5");
  background.addColorStop(1, "#7cc9ff");
  context.fillStyle = background;
  context.fillRect(0, 0, POSTER_WIDTH, POSTER_HEIGHT);

  context.fillStyle = "rgba(255,255,255,0.14)";
  context.beginPath();
  context.arc(930, 170, 235, 0, Math.PI * 2);
  context.fill();
  context.beginPath();
  context.arc(150, 1270, 280, 0, Math.PI * 2);
  context.fill();

  context.fillStyle = "#ffffff";
  context.font = "600 40px 'Microsoft YaHei', sans-serif";
  context.fillText("文星 · 数智学堂", 92, 128);
  context.fillStyle = "rgba(255,255,255,0.76)";
  context.font = "400 26px 'Microsoft YaHei', sans-serif";
  context.fillText("AI 陪伴，把学习走得更扎实", 92, 178);

  context.fillStyle = "#ffffff";
  context.font = "700 88px 'Microsoft YaHei', sans-serif";
  context.fillText("把每一道错题", 92, 390);
  context.fillText("变成下一次进步", 92, 500);
  context.fillStyle = "#d9f1ff";
  context.fillRect(96, 540, 214, 10);

  context.fillStyle = "rgba(255,255,255,0.16)";
  roundedRect(context, 76, 650, 928, 288, 38);
  context.fill();
  context.fillStyle = "#ffffff";
  context.font = "600 33px 'Microsoft YaHei', sans-serif";
  context.fillText("给学生", 124, 730);
  context.font = "400 32px 'Microsoft YaHei', sans-serif";
  context.fillText(content.studentLine, 124, 790);
  context.font = "600 33px 'Microsoft YaHei', sans-serif";
  context.fillText("给家长", 124, 856);
  context.font = "400 32px 'Microsoft YaHei', sans-serif";
  context.fillText(content.parentLine, 124, 916);

  context.fillStyle = "#ffffff";
  roundedRect(context, 76, 1020, 928, 382, 42);
  context.fill();
  const qrCanvas = document.createElement("canvas");
  await QRCode.toCanvas(qrCanvas, content.shareUrl, {
    width: 252,
    margin: 1,
    errorCorrectionLevel: "M",
    color: { dark: "#173fba", light: "#ffffff" },
  });
  context.drawImage(qrCanvas, 126, 1088, 252, 252);
  context.fillStyle = "#173fba";
  context.font = "700 38px 'Microsoft YaHei', sans-serif";
  context.fillText("扫码一起学习", 432, 1146);
  context.fillStyle = "#526379";
  context.font = "400 27px 'Microsoft YaHei', sans-serif";
  context.fillText("错题整理 · 分步讲解 · 巩固复习", 432, 1204);
  context.font = "400 20px 'Microsoft YaHei', sans-serif";
  drawWrappedText(context, content.shareUrl, 432, 1268, 500, 31);

  return new Promise((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) resolve(blob);
      else reject(new Error("海报生成失败，请重试"));
    }, "image/png");
  });
}

export function downloadSharePoster(blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "数智学堂-邀请海报.png";
  link.click();
  URL.revokeObjectURL(url);
}

export async function sharePoster(blob: Blob): Promise<boolean> {
  if (typeof navigator.share !== "function" || typeof navigator.canShare !== "function") return false;
  const file = new File([blob], "数智学堂-邀请海报.png", { type: "image/png" });
  if (!navigator.canShare({ files: [file] })) return false;
  await navigator.share({ title: "数智学堂", files: [file] });
  return true;
}
