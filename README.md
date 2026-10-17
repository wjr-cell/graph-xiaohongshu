# AI 内容运营助手

## 📸 项目截图

<p align="center">
  <img src="./屏幕截图%202026-10-17%20175431.png" width="80%" />
</p>

<p align="center">
  <img src="./屏幕截图%202026-10-17%20123628.png" width="80%" />
</p>

<p align="center">
  <img src="./屏幕截图%202026-10-17%20175102.png" width="80%" />
</p>

<p align="center">
  <img src="./屏幕截图%202026-10-17%20175154.png" width="80%" />
</p>

<p align="center">
  <img src="./屏幕截图%202026-10-17%20175209.png" width="80%" />
</p>

## 项目介绍

基于 LangGraph 1.0+ 和 FastAPI 的自动化内容生成工作流（含 Vue 前端）。

## 功能特性

- **AI 选题生成**: 根据主题方向自动生成候选选题
- **AI 文章撰写**: 根据选定选题生成技术文章
- **Human-in-the-loop**: 支持人工介入的选题和审稿机制
- **配图生成**: 自动提取视觉要点并生成配图
- **状态持久化**: 使用 PostgreSQL 持久化工作流状态
- **用户认证**: JWT 登录 / 注册

## 技术栈

- **Python 3.12**（conda 环境 `xiaohongshu`）
- **FastAPI** / **LangGraph 1.0+** / **PostgreSQL** / **SQLAlchemy**
- **Vue 3** + **Vite**（前端）

## 快速开始

### 1. 环境准备

确保本地已安装并运行 PostgreSQL：

```bash
# 创建数据库（名称需与 .env 中一致）
psql -U postgres -c "CREATE DATABASE langgraph_db;"

# 可选：初始化用户表等
psql -U postgres -d langgraph_db -f scripts/init_db.sql
```

### 2. 安装后端依赖

```bash
# 创建环境（Python 3.12）
conda create -n xiaohongshu python=3.12 -y

# 激活环境
conda activate xiaohongshu

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

按需修改 `.env` 中的数据库连接、LLM / 图片 API Key 等：

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/langgraph_db
POSTGRES_URI=postgresql://postgres:your_password@localhost:5432/langgraph_db
```

### 4. 启动后端

```bash
conda activate xiaohongshu

# 方式 1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式 2
python -m app.main
```

API 文档: http://localhost:8000/docs

### 5. 启动前端（推荐）

InkFlow 前端提供清晰的五步流程界面：登录 → 输入主题 → 选题 → 审稿 → 配图完成。

```bash
cd frontend
npm install
npm run dev
```

浏览器访问: http://localhost:3000（已代理 `/api` 与 `/static` 到后端 `8000` 端口）

## API 接口

### 启动工作流

```bash
POST /api/v1/workflow/start
Content-Type: application/json

{
    "topic_direction": "AI技术"
}
```

**响应示例:**

```json
{
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "topics_generated",
    "generated_topics": [
        "LangGraph入门：构建你的第一个AI工作流 - AI技术方向",
        "AI Agent实战：从零搭建智能助手 - AI技术方向",
        "Python高并发编程：asyncio深度解析 - AI技术方向"
    ],
    "message": "工作流已启动，请选择一个选题继续"
}
```

### 获取工作流状态

```bash
GET /api/v1/workflow/state/{thread_id}
```

### 恢复工作流 - 选择选题

```bash
POST /api/v1/workflow/resume/{thread_id}
Content-Type: application/json

{
    "action": "select_topic",
    "data": {
        "selected_topic": "LangGraph入门：构建你的第一个AI工作流"
    }
}
```

### 恢复工作流 - 审核通过

```bash
POST /api/v1/workflow/resume/{thread_id}
Content-Type: application/json

{
    "action": "approve"
}
```

### 恢复工作流 - 审核驳回

```bash
POST /api/v1/workflow/resume/{thread_id}
Content-Type: application/json

{
    "action": "reject",
    "data": {
        "feedback": "请增加更多实际代码示例"
    }
}
```

## 工作流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                         START                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     plan_topics                                  │
│                  (AI 生成 3-5 个选题)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ⏸️ INTERRUPT: human_select_topic                    │
│                    (等待人工选题)                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      write_draft                                 │
│                  (AI 根据选题写长文)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ⏸️ INTERRUPT: human_review                          │
│                    (等待人工审稿)                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         [approved]                      [rejected]
              │                               │
              ▼                               │
┌─────────────────────────┐                   │
│    extract_visuals      │                   │
│    (提炼图片要点)        │                   │
└─────────────────────────┘                   │
              │                               │
              ▼                               │
┌─────────────────────────┐                   │
│    generate_images      │                   │
│    (生成配图)           │                   │
└─────────────────────────┘                   │
              │                               │
              ▼                               │
┌─────────────────────────┐                   │
│          END            │◀──────────────────┘
│       (工作流完成)       │    (回到 write_draft 重写)
└─────────────────────────┘
```

## 项目结构

```
.
├── app/
│   ├── api/v1/              # auth / workflow / image API
│   ├── core/                # 配置、数据库、日志、安全、中间件
│   ├── dependencies/        # FastAPI 依赖（认证等）
│   ├── graph/               # LangGraph 工作流
│   │   ├── nodes/           # planner / writer / visualizer
│   │   ├── subgraphs/       # 选题子图
│   │   ├── state.py
│   │   ├── workflow.py
│   │   └── utils.py
│   ├── models/              # SQLAlchemy 模型
│   ├── services/            # LLM / 图片生成服务
│   └── main.py              # 应用入口
├── frontend/                # Vue 3 + Vite 前端
├── scripts/
│   └── init_db.sql          # 数据库初始化（可选）
├── static/images/generated/ # 运行时生成的配图（不入库）
├── requirements.txt
├── .env.example
└── README.md
```

## 注意事项

1. **数据库连接**: 确保 PostgreSQL 服务运行，库名与 `.env` 一致（默认 `langgraph_db`）
2. **LLM / 配图配置**: 在 `.env` 中配置火山引擎 Doubao / Seedream API Key
3. **状态持久化**: LangGraph Checkpointer 会自动创建所需表结构
4. **生成图片**: 保存在 `static/images/generated/`，已加入 `.gitignore`

