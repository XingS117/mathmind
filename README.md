# 数智学堂 MathMind

数智学堂是一个面向中学生的个性化数学学习平台：把日常错题和好题拍照入库，通过 AI 解析、知识图谱归类和分步引导，把题目沉淀成可复习、可追踪、可迁移的学习资产。

> 当前开发暂缓。方案版本为 v1.1，恢复开发前请先阅读
> [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

## 当前能力

- 拍照或上传题目图片，进行 OCR / AI 分析并确认入库。
- 入库前校对题干、题型、难度、知识点、题眼、答案和解析，避免错误数据污染题库。
- 按初中、高中知识图谱浏览题目分布。
- 进入导学会话，按步骤回答、提示、跳过或查看详细讲解。
- 记录学习历史、掌握度和复习计划。
- 在设置页配置模型服务商和 API Key。

## 入库流程

1. 在「入库」页上传一张或多张题目图片。
2. 系统尝试 OCR / 视觉模型识别题目。
3. 如果识别失败，仍可手动输入题目内容。
4. 在入库前校对题干、知识点、题眼、答案和解析。
5. 点击「确认入库」后，题目进入个人题库并跳转到导学页。

## 本地开发

### 后端

```bash
cd D:\Sven\maths
pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

OCR 是可选增强能力。需要本地 PaddleOCR 时再安装：

```bash
pip install -r backend\requirements-ocr.txt
```

如果没有安装 OCR，系统会进入 OCR mock 模式，仍可通过手动输入或视觉模型能力继续调试上传流程。

### 前端

```bash
cd D:\Sven\maths\frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，并通过 Vite proxy 转发 `/api` 到后端 `http://localhost:8000`。

### 一键启动

```bat
_run.bat
```

该脚本会分别打开后端 API 和前端 Web 两个窗口。

## 关键文件

- 产品方案：`SPEC.md`
- 项目进度与接续记录：`docs/PROJECT_STATUS.md`
- 后端入口：`backend/main.py`
- 前端入口：`frontend/src/App.tsx`
- 数据库：`data/mathmind.db`
- 知识图谱：`data/knowmap.json`
- 种子题库：`data/seed_questions.json`

## 当前数据说明

截至 2026-06-27，本地数据库中的 14 道题全部是开发测试数据，不是真实错题，也不能代表复杂题目已经通过验收。

后续真实验收需要使用包含几何图、函数图、多步骤推理或多张图片的复杂题目。复习计划按 10 / 30 / 90 / 180 天生成。

## 开发检查

```bash
cd D:\Sven\maths\frontend
npx tsc --noEmit
npx vite build --configLoader native

cd D:\Sven\maths
python -m compileall backend
```
