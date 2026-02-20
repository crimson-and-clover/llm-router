# LLM Router - 大模型 API 路由服务

LLM Router 是一个开源的大模型 API 路由/代理服务，提供统一的 OpenAI 兼容接口，支持多个 LLM 提供商（月之暗面、深度求索、智谱等），并支持 API Key 管理和请求处理管道定制。

## 主要特性

- **统一接口**：对外提供 OpenAI 兼容的 `/chat/completions` API
- **多提供商支持**：支持月之暗面（Moonshot）、深度求索（DeepSeek）、智谱（Zai）等多个 LLM 提供商
- **API Key 管理**：基于 SQLite 的 API Key 存储，支持多租户和权限控制
- **Cursor IDE 优化**：内置 CursorPipeline，可将模型的思考过程转换为 `<think>` 标签格式
- **流式响应**：完整支持 SSE 流式和非流式响应
- **请求处理管道**：可扩展的 Pipeline 架构，支持自定义请求/响应处理

## 技术栈

### 后端服务器 (src/)
- **Web 框架**: FastAPI
- **HTTP 客户端**: httpx (异步)
- **数据库**: SQLite (aiosqlite)
- **配置管理**: Pydantic Settings
- **服务器**: Uvicorn

### 前端界面 (ui/)
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: Pinia
- **路由**: Vue Router

### 边缘计算 (worker/)
- **平台**: Cloudflare Workers
- **运行时**: Node.js / TypeScript
- **部署**: Wrangler CLI

## 项目架构

LLM Router 采用三层架构设计：

```
llm-router/
├── src/                         # Python 后端服务器
│   ├── api/
│   │   ├── routes_chat.py       # API 路由定义
│   │   └── routes_internal.py   # 内部管理路由
│   ├── core/
│   │   ├── dependencies.py      # FastAPI 依赖
│   │   ├── logging.py           # 日志配置
│   │   ├── security.py          # 安全工具
│   │   └── settings.py          # 应用配置
│   ├── models/                  # 数据模型
│   ├── pipeline/
│   │   ├── base.py              # 基础 Pipeline
│   │   └── cursor.py            # Cursor IDE 专用 Pipeline
│   ├── providers/               # LLM 提供商适配器
│   │   ├── base.py              # Provider 基类
│   │   ├── moonshot.py          # 月之暗面（Moonshot）适配
│   │   ├── deepseek.py          # 深度求索（DeepSeek）适配
│   │   ├── zai.py               # 智谱（Zai）适配
│   │   └── test_provider.py     # 测试用 Provider
│   ├── storage/
│   │   ├── apikey_storage.py    # API Key 存储管理
│   │   └── user_storage.py      # 用户存储管理
│   ├── utils/
│   │   └── decoder.py           # 解码工具
│   ├── main.py                  # FastAPI 应用入口
│   ├── manage_keys.py           # API Key 管理工具
│   └── manage_users.py          # 用户管理工具
├── ui/                          # Vue.js 前端界面
│   ├── src/
│   │   ├── api/                 # API 客户端
│   │   ├── components/          # Vue 组件
│   │   ├── router/              # 路由配置
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── views/               # 页面视图
│   │   └── App.vue              # 根组件
│   └── package.json
├── worker/                      # Cloudflare Workers 边缘计算
│   ├── src/
│   │   ├── routes/              # 路由处理
│   │   │   ├── api/             # API 路由
│   │   │   └── worker/          # Worker 内部路由
│   │   ├── core/                # 核心逻辑（结算、日志等）
│   │   ├── middleware/          # 中间件（认证等）
│   │   ├── providers/           # LLM 提供商适配
│   │   ├── storage/             # 边缘存储
│   │   ├── types.ts             # 类型定义
│   │   └── index.ts             # Worker 入口
│   ├── wrangler.jsonc           # Worker 配置
│   └── package.json
├── tests/                       # 单元测试
├── tests_integration/           # 集成测试
├── scripts/                     # 工具脚本
├── logs/                        # 日志目录
└── data/                        # SQLite 数据库目录
```

### 架构说明

| 组件 | 技术 | 职责 |
|------|------|------|
| **Python 服务器** | FastAPI + SQLite | 主服务，处理 API 请求、API Key 管理、用户认证 |
| **前端界面** | Vue 3 + TypeScript | 管理后台，提供 Web UI 管理 API Key 和用户 |
| **边缘 Worker** | Cloudflare Workers | 边缘计算层，提供低延迟 API 访问、请求预处理 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
# ========== 月之暗面（Moonshot）配置 ==========
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_API_KEY=your_moonshot_api_key

# ========== 深度求索（DeepSeek）配置 ==========
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your_deepseek_api_key

# ========== 智谱（Zai）配置 ==========
ZAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZAI_API_KEY=your_zai_api_key

# ========== 内部密钥配置 ==========
# 用于 Worker 与后端服务之间的安全通信
INTERNAL_SECRET=your-internal-secret-key

# ========== 可选配置 ==========
DEBUG=false
```

**注意**：`INTERNAL_SECRET` 用于 Worker 与后端服务之间的安全通信。建议生成强随机字符串：

```bash
openssl rand -base64 32
```

### 3. 创建 API Key

```bash
python src/manage_keys.py create --username admin --purpose default --prefix sk
```

输出示例：
```
==============================
✅ API Key 创建成功！
Owner: admin
Key:   sk-xxxxxxxxxxxxxxxxxxxxxxxx
Purpose: default
==============================
```

### 4. 启动服务

```bash
bash start_server.sh
# 或
python src/main.py
```

服务将在 `http://0.0.0.0:12000` 启动。

## API 使用

### Chat Completions

```bash
curl http://localhost:12000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "moonshot/kimi-k2.5",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### 支持的模型格式

模型名称格式为 `{provider}/{model_name}`：

| Provider | 中文名 | 可用模型 |
|----------|--------|----------|
| moonshot | 月之暗面 | `kimi-k2.5`, `kimi-k2-0905-preview`, `kimi-k2-thinking` |
| deepseek | 深度求索 | `deepseek-chat`, `deepseek-reasoner` |
| zai | 智谱 | `glm-5` |

### 流式响应

```bash
curl http://localhost:12000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "deepseek/deepseek-reasoner",
    "messages": [{"role": "user", "content": "解释量子计算"}],
    "stream": true
  }'
```

## API Key 管理

### 创建 API Key

```bash
# 基础用法
python src/manage_keys.py create --username user001

# 指定用途（cursor 用途会启用特殊处理）
python src/manage_keys.py create --username user001 --purpose cursor

# 自定义前缀
python src/manage_keys.py create --username user001 --prefix pk
```

### 用途说明

| Purpose | 说明 |
|---------|------|
| `default` | 使用默认 Pipeline，透传请求 |
| `cursor` | 使用 CursorPipeline，将 `reasoning_content` 转换为 `<think>` 标签 |

## 配置说明

### 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `MOONSHOT_BASE_URL` | 是* | 月之暗面 API 基础地址 |
| `MOONSHOT_API_KEY` | 是* | 月之暗面 API 密钥 |
| `DEEPSEEK_BASE_URL` | 是* | 深度求索 API 基础地址 |
| `DEEPSEEK_API_KEY` | 是* | 深度求索 API 密钥 |
| `ZAI_BASE_URL` | 是* | 智谱 API 基础地址 |
| `ZAI_API_KEY` | 是* | 智谱 API 密钥 |
| `INTERNAL_SECRET` | 否 | 内部通信密钥，用于 Worker 与后端服务认证 |
| `DEBUG` | 否 | 调试模式，默认 `false` |

*至少配置一个提供商

### 数据库

SQLite 数据库默认存储在 `./data/api_keys.db`，支持 WAL 模式以处理并发访问。

## 边缘 Worker 部署

LLM Router 支持部署到 Cloudflare Workers 边缘节点，提供低延迟的全球访问。

详细的部署说明请参考：[worker/DEPLOYMENT.md](worker/DEPLOYMENT.md)

### 部署架构

Worker 提供以下访问路径：

| 路径 | 用途 | 说明 |
|------|------|------|
| `/api/*` | LLM API 接口 | 对外提供 OpenAI 兼容的聊天接口 |
| `/worker/*` | Worker 内部接口 | 用于 Worker 内部路由（如 ping、结算触发等） |

源服务器（后端 Python 服务）提供：

| 路径 | 用途 | 说明 |
|------|------|------|
| `/internal/*` | 内部管理接口 | 用于用量结算、密钥验证等内部通信 |

### 快速部署

```bash
cd worker
npm install
npx wrangler login
npx wrangler deploy --env production
```

### 本地开发（反向代理模式）

开发时使用 Cloudflare Tunnel 将请求反向代理到本地：

1. **启动源服务器（后端）：**
   ```bash
   python src/main.py
   ```

2. **启动本地 Worker：**
   ```bash
   cd worker
   npx wrangler dev --env development
   ```

3. **配置 Cloudflare Tunnel：**
   - 在本地启动 cloudflared 连接到 Cloudflare
   - 在 Cloudflare Dashboard 配置 Tunnel 路由：
     - `/api/*` → Worker (`http://localhost:8787`)
     - `/internal/*` → 源服务器 (`http://localhost:12000`)

4. **配置本地环境：**
   创建 `worker/.dev.vars` 文件：
   ```bash
   MOONSHOT_API_KEY="sk-xxx"
   DEEPSEEK_API_KEY="sk-xxx"
   ZAI_API_KEY="sk-xxx"
   INTERNAL_SECRET="sk-xxx"
   BACKEND_URL="http://localhost:12000"
   ```

> **注意**：`INTERNAL_SECRET` 必须与后端服务配置的密钥一致，用于 Worker 与后端 `/internal/*` 接口的安全通信。

## 扩展开发

### 添加新的 Provider

1. 在 `src/providers/` 下创建新文件
2. 继承 `BaseProvider` 类
3. 实现 `chat_completions` 和 `chat_completions_stream` 方法
4. 在 `main.py` 中注册

### 自定义 Pipeline

1. 继承 `BasePipeline` 类
2. 重写以下方法：
   - `preprocess_request()` - 请求预处理
   - `postprocess_response()` - 响应后处理
   - `rewrite_sse_lines()` - 流式响应行重写

## 日志

日志文件存储在 `logs/` 目录，可通过设置 `DEBUG=true` 启用详细日志。

## License

MIT License
