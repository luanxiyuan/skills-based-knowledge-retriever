# Skills-Based Knowledge Retriever

> 基于 Agent Skills 的无向量渐进式知识库检索引擎，通过 LLM 驱动的智能导航实现高效的多格式文件问答系统。

## 项目简介

本项目是一个完整的本地知识库检索解决方案，采用前后端分离架构：

- **后端**：FastAPI + WebSocket，提供实时流式响应
- **前端**：React + TypeScript + Tailwind CSS，现代化 UI 界面
- **LLM**：支持 Ollama 等本地大模型

### 核心特性

- **多格式支持** - Markdown、PDF、Excel 等多种文件格式
- **分层索引** - 通过 `data_structure.md` 实现智能目录导航
- **渐进式检索** - 避免全文加载，按需局部读取，节省 token
- **LLM 驱动导航** - 智能选择最相关的文件路径
- **实时流式输出** - WebSocket 实时推送思考过程和回答
- **可中断处理** - 支持随时停止正在进行的查询

---

## 项目结构

```
skills-based-knowledge-retriever/
├── backend/                       # 后端服务
│   ├── agent/                     # Agent 核心模块
│   │   ├── agent.py               # Agent 主逻辑
│   │   └── llm_manager.py         # LLM 管理器
│   ├── knowledge/                 # 知识库目录
│   │   ├── data_structure.md      # 根目录索引
│   │   ├── AI Knowledge/          # AI 行业报告（PDF）
│   │   ├── Financial Report Data/ # 金融财报数据
│   │   ├── E-commerce Data/       # 电商业务数据（Excel）
│   │   └── Safety Knowledge/      # 安全知识文档（Markdown）
│   ├── rag-skill/                 # RAG Skill 定义
│   │   ├── SKILL.md               # Skill 主文件
│   │   └── references/            # 参考文档
│   ├── skill_engine/              # Skill 执行引擎
│   ├── tools/                     # 工具实现
│   │   ├── grep_tool.py           # 文本搜索
│   │   ├── read_tool.py           # 文件读取
│   │   ├── pdf_tool.py            # PDF 处理
│   │   └── excel_tool.py          # Excel 处理
│   ├── config.yaml                # 配置文件
│   ├── main.py                    # FastAPI 主应用
│   ├── websocket_server.py        # WebSocket 服务
│   └── requirements.txt           # Python 依赖
│
├── frontend/                      # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx  # 聊天界面组件
│   │   │   └── ui/                # UI 组件
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                          # 文档
│   ├── 01-业务需求文档.md
│   └── 02-架构设计文档.md
│
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Ollama（或其他兼容的 LLM 服务）

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 配置 LLM

编辑 `backend/config.yaml`：

```yaml
llm:
  default_model: "qwen2.5:14b"
  models:
    qwen2.5:14b:
      base_url: "http://localhost:11434"
```

---

## 使用示例

### 示例 1：查询 AI 行业趋势

```
问：2026年AI Agent技术有哪些关键发展趋势？
```

**执行流程**：
1. 读取 `knowledge/data_structure.md` 识别 AI Knowledge 目录
2. LLM 智能导航到 `AI Knowledge/` 目录
3. 定位到 `2026年AI Agent智能体技术发展报告.pdf`
4. 使用 PDF 工具提取内容
5. LLM 生成最终答案

### 示例 2：分析电商数据

```
问：帮我分析一下库存数据，哪些商品库存不足？
```

**执行流程**：
1. 导航到 `E-commerce Data/` 目录
2. 定位到 `inventory.xlsx`
3. 使用 Excel 工具分析数据
4. 返回库存不足的商品列表

### 示例 3：查询安全知识

```
问：XSS是什么？
```

**执行流程**：
1. 导航到 `Safety Knowledge/` 目录
2. 使用 Grep 工具搜索关键词
3. 读取匹配内容并生成答案

---

## 核心设计

### 1. LLM 驱动的智能导航

通过 `data_structure.md` 文件描述目录结构，LLM 根据用户问题智能选择最相关的路径：

```
用户问题 → LLM 分析 → 读取索引 → 选择目录/文件 → 递归导航
```

### 2. Skill 执行引擎

基于 Skill 定义文件（SKILL.md）驱动工具调用：

- **工具注册**：自动发现和注册可用工具
- **参数解析**：从 Skill 定义中提取工具参数
- **执行调度**：按顺序执行工具方法

### 3. 渐进式检索

- 使用 `grep` 定位关键词
- 只读取匹配行附近的上下文
- 避免一次性加载整个文件

### 4. 实时流式输出

WebSocket 实时推送：
- 思考步骤（thinking）
- 工具调用（tool_call）
- 流式回答（answer_stream）

---

## 知识库数据

### AI Knowledge（AI 行业报告）
- **格式**：PDF
- **内容**：AI Agent 技术、大模型应用、AI 治理等

### Financial Report Data（金融财报）
- **格式**：PDF
- **内容**：上市公司季度财报

### E-commerce Data（电商数据）
- **格式**：Excel
- **数据表**：customers、employees、inventory、sales_orders

### Safety Knowledge（安全知识）
- **格式**：Markdown
- **内容**：XSS、CSRF、CORS 等 Web 安全知识

---

## 技术栈

### 后端
- **FastAPI** - 高性能异步 Web 框架
- **WebSocket** - 实时双向通信
- **httpx** - 异步 HTTP 客户端（LLM 调用）
- **pandas** - Excel 数据处理
- **pdfplumber** - PDF 文本提取

### 前端
- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **React Markdown** - Markdown 渲染

---

## 配置说明

### config.yaml

```yaml
llm:
  default_model: "qwen2.5:14b"
  timeout: 300
  models:
    qwen2.5:14b:
      base_url: "http://localhost:11434"

knowledge:
  root_path: "knowledge"

skill:
  skill_path: "rag-skill"
```

---

## 扩展知识库

### 添加新的知识领域

1. 在 `backend/knowledge/` 下创建新目录
2. 添加 `data_structure.md` 说明用途
3. 放入相关文件
4. 更新根目录的 `data_structure.md`

### data_structure.md 模板

```markdown
# [目录名称]

## 用途
简要说明本目录的用途

## 文件说明
- file1.pdf - 文件描述
- file2.xlsx - 文件描述

## 数据范围
时间范围、版本信息等
```

---

## 许可证

本项目仅用于演示和学习目的。
