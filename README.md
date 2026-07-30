# MathMind

> 把错题变成可追踪的学习资产。

[在线体验](https://mathmind.xingshuwen.com/)

MathMind 面向中学生，把一道错题从图片、人工校对、分步陪练到后续复习串成可回看的学习记录。它不是一次性给出答案的工具，而是帮助学生整理错题、理解关键方法并持续复习的学习空间。

## 适合谁

- 学生：整理错题，弄懂关键方法，按节奏复习。
- 家长：看见学习积累和需要关注的薄弱点。

## 使用指南

1. 注册并登录后，打开「入库」上传一张或多张题目图片。
2. 校对题干、题型、知识点、答案和解析，再确认入库。
3. 进入导学页逐步作答；需要时使用提示或详细讲解。
4. 在首页和知识图谱查看学习记录、掌握度和待复习任务。

AI 识别结果仍需人工确认，尤其是含图、多页或复杂公式的题目。

## 当前能力

- 上传单图或多图题目，进行 OCR / AI 分析并人工确认入库。
- 将题目关联到知识图谱，沉淀题干、题眼、答案和解析。
- 通过分步导学记录尝试、提示和卡点。
- 在仪表盘查看学习历史、掌握度和复习任务。

## 本地运行

环境要求：Python 3.10+、Node.js 20+ 和 npm。

启动后端：

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

另开终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 输出的本地地址，默认是 `http://127.0.0.1:5173/`。前端会将 `/api` 请求转发到 `http://127.0.0.1:8000`。

生产环境变量和反向代理原则请参考 [公共部署说明](docs/PUBLIC_DEPLOYMENT.md)。

## 验证

```bash
cd frontend
npm test
npx tsc --noEmit
npm run build

cd ..
python -m compileall backend
```

## 数据与安全

- `.env`、数据库、备份和上传内容均为本地文件，不应提交到 Git。
- API Key 等敏感配置使用环境变量管理，配置方法见 `.env.example`。
- 请只上传有权处理的题目图片和学习资料。
