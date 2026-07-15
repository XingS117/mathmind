# MathMind 阶段归档 · 公开测试期（Public Beta）

> 归档日期：2026-07-11
> Git HEAD（归档时刻）：`44d369a`（分支 `feat/real-question-baseline`）
> 生产 URL：<https://mathmind.xingshuwen.com/>
> 上一里程碑：`docs/quality/ua-2026-07-09.md`（正式上线 UA 全通）
> 本文档定位：把 2026-07-09 正式上线 → 2026-07-11 面向真实用户可用之间的四件事一次性沉淀，方便后续 Agent / 用户回溯

---

## 1. 阶段定义

| 里程碑 | 日期 | 状态标志 |
|--------|------|---------|
| Alpha：5 题基线闭环 + 修复包 A | 2026-07-09（首次跑通） | `docs/quality/real-question-baseline-2026-06-27.md` |
| Beta 上线：正式部署 + UA 全通 | 2026-07-09（`647ac0b`） | `docs/quality/ua-2026-07-09.md` |
| **Public Beta：面向真实用户可用（本次归档）** | **2026-07-11（`44d369a`）** | **本文档** |
| GA：多真实用户回归 + P2 收敛 | 未开始 | 待用户下一步授权 |

「Public Beta」的判定标准：**任何一个真实用户打开生产 URL，都能把自己的错题从上传到入库到诊断跑一遍完整闭环，且不会撞进 demo 数据、不会遇到"知识点没有匹配的图谱节点"这类系统性阻塞。**

---

## 2. 本阶段实际交付（Beta 上线 → Public Beta）

Git 范围：`647ac0b..44d369a`，共 9 个提交。核心 4 件事：

### 2.1 高中知识图谱切换到人教 B 版

- **背景**：Beta 上线时高中图谱是自造的通用目录，用户明确要求"要使用人教 B 版的目录"，并指向 <https://www.pep.com.cn/gzsxb/>。
- **改动**：
  - 章级依据 pep.com.cn 官网抓取（7 册 17 章：必修四册 + 选择性必修三册）
  - 节级采用人教 B 版通行目录填充（89 节点）
  - 初中三册保持不变（38 节点）
  - 总节点数 `133 → 127`（高中 95 → 89，其余不变）
- **迁移**：`scripts/migrate_knowmap_bban/build_bban_knowmap.py`（含 `OLD_TO_NEW` 映射表）+ `scripts/migrate_knowmap_bban/fix_db_only.py`（生产 db 单修）
- **备份**：`data/knowmap.json.pre_bban.bak`、`data/seed_questions.json.pre_bban.bak`、生产端 `mathmind.db.pre_bban.bak`
- **提交**：`d9507df`、`7fe2dab`

### 2.2 清空 demo 数据 · 让新用户从零开始

- **背景**：上线后仍在默认灌 7 条 seed 题 + demo sessions/mastery，第一个真实用户看到的是别人的错题。
- **改动**：
  - `backend/services/seed_service.py`：默认不再灌 seed；只有 `MATHMIND_ENABLE_SEED=1` 才灌
  - `scripts/reset_prod_data/wipe_demo_data.py`：一次性清空 `questions / sessions / mastery / review_schedule`，保留 `users / user_settings / knowmap`
- **生产执行**：备份 `mathmind.db.pre_wipe_20260709-221959.bak`，已一次性清库
- **提交**：`ddad385`

### 2.3 知识点自动挂图谱节点 · 校对更省事

- **背景**：真实用户上传后卡在校对页——AI 识别出的知识点（如"椭圆的标准方程"）跟 B 版节名（"椭圆及其方程"）字面不等，"没有匹配的图谱节点"。
- **改动**：
  - `backend/services/knowmap_matcher.py`：
    - 扩 `_SUFFIX_NOISE`（"的标准方程 / 及其方程 / 求和公式 / 通项" 等）
    - 扩 `_PARTICLES`（`及其 / 及 / 对`）
    - 新增 `_ALIAS_MAP`：教学术语 ↔ B 版节名核心词，覆盖常用逻辑、立体几何、圆锥曲线、直线与圆、随机变量、数列、三角、导数
    - alias 展开在整份 kp 联合体上判显式头名词（避免"椭圆的标准方程 + 焦点弦长"顺带把双曲线/抛物线拉进来）
  - `backend/routers/upload.py::confirm_question`：兜底 matcher，用户没勾节点但 kp 非空时自动挂 3 个
  - `frontend/src/components/ImageUpload.tsx`：analyze 返回后默认勾上前 3 个 AI 建议
- **测试**：`backend/tests/test_knowmap_matcher.py` 13/13 通过（原 7 + B 版新增 6）
- **提交**：`1836884`

### 2.4 模型清单按各家官网更新（+ MiniMax base_url 修正）

- **背景**：用户推的 MiniMax 文档指出模型系列已迁到 M3/M2.7/M2.5/M2.1/M2，`base_url` 应为 `api.minimaxi.com/v1`；用户同步要求其他厂按官网各取主流 3 款。
- **改动**（`backend/routers/settings.py::PROVIDER_MODELS` + `backend/services/llm_service.py::defaults`）：

  | 厂 | 主流 3 款 | base_url |
  |---|---|---|
  | DeepSeek | `deepseek-v4-pro / deepseek-v4-flash / deepseek-chat` | `api.deepseek.com/v1` |
  | OpenAI | `gpt-5.6-sol / gpt-5.6-terra / gpt-5.6-luna` | `api.openai.com/v1` |
  | Gemini | `gemini-3.5 / gemini-3.5-flash / gemini-2.5-pro` | `generativelanguage.googleapis.com/v1beta` |
  | Qwen | `qwen3.7-max / qwen3.6-plus / qwen3.6-flash` | `dashscope.aliyuncs.com/compatible-mode/v1` |
  | Moonshot | `kimi-latest / kimi-k2.7-code / moonshot-v1-128k` | `api.moonshot.cn/v1` |
  | MiniMax | `MiniMax-M3 / M2.7 / M2.7-highspeed` 等 8 款 | `api.minimaxi.com/v1` ✅修正 |
  | 腾讯混元 | **未动** | 官网 JS 渲染无法取证，按 AGENTS.md 不猜 |

- **提交**：`1acd50a`、`44d369a`
- **生产验证**：`curl /api/v1/settings/providers` 返回新数据

### 2.5 其它已上线但更早的能力（引用）

- 登录 + 数据隔离（`8f97021` + `ed73987`）：见 `docs/quality/ua-2026-07-09.md` UA-06
- 正式部署 Ubuntu + nginx + Let's Encrypt + systemd（`647ac0b`）：见 `docs/DEPLOYMENT-live.md`
- Windows 单机单端口方案（`76231bb` + `0ae1c18`）：见 `docs/DEPLOYMENT.md`

---

## 3. 当前生产状态（归档时刻实测）

| 项 | 值 |
|----|----|
| URL | <https://mathmind.xingshuwen.com/> |
| HTTPS 证书 | Let's Encrypt，2026-10-06 到期，certbot systemd timer 自动续签 |
| 后端 | `mathmind.service`（systemd），`uvicorn 127.0.0.1:8100` |
| 前端 | `frontend/dist` 由 backend 单端口托管 |
| LLM | DeepSeek `deepseek-chat`，key 走 `.env` 注入 |
| OCR | PaddleOCR 3.7.0 + PaddlePaddle 3.3.1，冷启单张 <25s |
| DB | SQLite，demo 数据已清空，第一位真实用户可从零建库 |
| 知识图谱 | 127 节点（初中 3 册 38 + 高中人教 B 版 7 册 89） |
| 模型清单 | 7 家（DeepSeek / OpenAI / Gemini / Qwen / Moonshot / MiniMax / 腾讯混元） |
| 数据备份 | `mathmind.db.pre_wipe_20260709-221959.bak`、`mathmind.db.pre_bban.bak` |

**回归测试基线**（本地工作树，最近一次绿）：
- backend `unittest`：70+ pass（含 auth 隔离 3 + knowmap matcher 13）
- frontend：`npx tsc --noEmit` 0 error / `npm run build` 39 modules 通过

---

## 4. Phase 完成度（对齐 SPEC v1.1）

| 阶段 | 状态 | 备注 |
|------|------|------|
| Phase A：底座与口径 | ✅ 完成 | 前后端可构建，MVP 闭环明确 |
| Phase B：高质量入库 | ✅ 完成 | 5 题基线全部 ≥80，OCR / LLM / 校对 / 图谱绑定跑通 |
| Phase C：导学诊断 | ✅ 主闭环完成 | mastery 三档、hint 不泄题、stuck 不重复、weak_spots 定位到图谱节点 |
| Phase D：复习与掌握度 | ✅ 主闭环完成 | 10/30/90/180 天复习自动写入；默认用户可见 |
| Phase E：三层变式 | ⚪ 未开始 | 完成页仅入口，未实现同型/条件变化/综合迁移 |
| Phase F：家庭可用版 | ✅ 部署 + 登录 + 数据隔离已上线 | 家长仪表盘、备份导出未做 |
| Phase G：搜索与班级 | ⚪ 暂缓 | 主闭环稳定后再评估 |

---

## 5. 已知遗留与风险

按后续 Agent 或用户可能追问的方向排序：

### 5.1 P2 增强项（计划外，不阻塞使用）
- `CONTENT-02`：LLM 中间步骤未强制化简到与解构稿等价形式（由 SOLVE_PROMPT 的 verification + self-confidence 缓解）
- `DIAGRAM-01`：`diagram_json=null`，未生成结构化几何/函数图数据
- `VERIFY-01`：SOLVE_PROMPT 未强制"识别原标答矛盾时标 uncertain_points"

### 5.2 模型协议未适配
- **MiniMax**：官方文档标 M 系列走 Anthropic 兼容协议，项目 `llm_service.py::call_llm_with_config` 只走 OpenAI 兼容 `POST /chat/completions`。用户若配 MiniMax 点"测试连接"预计失败，需要写 Anthropic 兼容适配器
- **腾讯混元**：模型清单未按官网更新（官网 JS 渲染抓不到静态证据），如要更新需用户给静态可访问的官方文档 URL

### 5.3 运维待办
- 生产 `u_admin` 密码仍是默认 `admin123`（`.env` 里 `ADMIN_PASS` 未设置），建议改
- 定期 db 备份未做成脚本 / cron，只在关键变更前手动备份
- Chrome DevTools 桌面 1440×900 + 移动 390×844 布局最终核对未做

### 5.4 图谱扩展空间
- B 版当前节到"5.2 等差数列"这级，如要更细（"5.2.1 等差数列的通项公式"）需 LLM 生成 + 用户确认
- `_ALIAS_MAP` 覆盖度：若真实用户上传发现某 kp 没匹配，往 `backend/services/knowmap_matcher.py::_ALIAS_MAP` 补一行即可

---

## 6. 后续 Agent 恢复入口

**必读顺序**：
1. `AGENTS.md`（根，行为准则）
2. `docs/AGENT_HANDOFF.md`（当前允许任务 + 单任务执行协议）
3. 本文档（阶段归档）
4. `docs/PROJECT_STATUS.md`（进度快照）
5. `docs/DEPLOYMENT-live.md`（生产运维）
6. `SPEC.md`（产品口径 v1.1）

**关键文件速查**：

| 场景 | 文件 |
|------|------|
| 后端图谱 | `backend/services/knowmap_service.py`（读 `data/knowmap.json`）+ `backend/routers/knowmap.py` |
| 知识点匹配 | `backend/services/knowmap_matcher.py`（`_ALIAS_MAP` 最常改） |
| 上传流程 | `backend/routers/upload.py::analyze_question` / `confirm_question` |
| 模型配置 | `backend/routers/settings.py::PROVIDER_MODELS` |
| LLM 调用 | `backend/services/llm_service.py::call_llm_with_config` |
| 认证/隔离 | `backend/services/auth_service.py::get_user_id`（默认 `u_default` 游客；`Authorization: Bearer` 走 uid） |
| 前端上传页 | `frontend/src/components/ImageUpload.tsx` |
| 前端设置页 | `frontend/src/pages/SettingsPage.tsx`（自动拉 providers，不用改） |

**生产更新流程**：见 `docs/DEPLOYMENT-live.md` 第 "更新流程" 节。核心：本地 build → 打 `deploy.tar.gz` → scp 到 `/data/mathmind/` → `sudo tar -xzf ... -C app && sudo systemctl restart mathmind`。

---

## 7. 归档确认

- [x] Git HEAD 已锁定：`44d369a`
- [x] 本轮四件事对应提交全部已入库
- [x] 生产 URL 可访问 · demo 数据已清空 · 第一位真实用户可从零建库
- [x] `PROJECT_STATUS.md` + `AGENT_HANDOFF.md` 同步至 Public Beta 快照
- [ ] 用户开始测试后新增问题 → 由下一次交接单独记录，不回填本文档