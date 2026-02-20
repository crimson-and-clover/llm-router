# Worker 部署说明

本文档介绍如何使用 `npx wrangler` 部署 LLM Router Worker。

## 架构概述

本项目使用单个 Worker 处理所有请求，包含两个主要功能：

| 功能 | 作用 | 触发方式 |
|------|------|----------|
| API 服务 | 处理 LLM API 请求 | HTTP 请求 |
| 结算服务 | 处理用量结算和日志 | Queue Consumer + Cron Trigger |

Worker 入口文件为 `src/index.ts`，根据触发类型自动路由到相应处理器。

### 环境说明

| 环境 | 部署目标 | 使用方式 |
|------|----------|----------|
| `production` | Cloudflare Workers | 生产环境部署 |
| `development` | 本地电脑 | 本地开发 + Cloudflare Tunnel 反代 |

## 支持的提供商

| 提供商 | 英文名 | 支持的模型 |
|--------|--------|------------|
| 月之暗面 | Moonshot | `kimi-k2.5`, `kimi-k2-0905-preview`, `kimi-k2-thinking` |
| 深度求索 | DeepSeek | `deepseek-chat`, `deepseek-reasoner` |
| 智谱 | Zai | `glm-5` |

## 前置要求

1. 安装依赖：
```bash
cd worker && npm install
```

2. 登录 Cloudflare 账号：
```bash
npx wrangler login
```

## 环境变量配置

### 1. Secrets（敏感信息）

以下变量需要通过 `wrangler secret put` 命令设置，**不会**存储在代码仓库中：

```bash
# 设置生产环境的 Secrets
npx wrangler secret put MOONSHOT_API_KEY --env production
npx wrangler secret put DEEPSEEK_API_KEY --env production
npx wrangler secret put ZAI_API_KEY --env production
npx wrangler secret put INTERNAL_SECRET --env production
```

| Secret 名称 | 说明 | 使用场景 |
|-------------|------|----------|
| `MOONSHOT_API_KEY` | 月之暗面（Moonshot）API 密钥 | 向月之暗面发起请求时认证 |
| `DEEPSEEK_API_KEY` | 深度求索（DeepSeek）API 密钥 | 向深度求索发起请求时认证 |
| `ZAI_API_KEY` | 智谱（Zai）API 密钥 | 向智谱发起请求时认证 |
| `INTERNAL_SECRET` | 内部通信密钥 | Worker 与后端服务之间的认证 |

> **注意**：开发环境使用 `.dev.vars` 文件管理 Secrets，无需执行 `wrangler secret put`。

### 2. Vars（非敏感变量）

在 `wrangler.jsonc` 的 `env.{environment}.vars` 部分配置：

**生产环境 (`production`)：**
```jsonc
"vars": {
  "BACKEND_URL": "https://llm.mrzero.site",
  "MOONSHOT_BASE_URL": "https://api.moonshot.cn/v1",
  "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
  "ZAI_BASE_URL": "https://open.bigmodel.cn/api/paas/v4"
}
```

**开发环境 (`development`)：**
```jsonc
"vars": {
  "BACKEND_URL": "https://test-llm.mrzero.site",
  "MOONSHOT_BASE_URL": "https://api.moonshot.cn/v1",
  "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
  "ZAI_BASE_URL": "https://open.bigmodel.cn/api/paas/v4"
}
```

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MOONSHOT_BASE_URL` | 月之暗面（Moonshot）API 回源地址 | `https://api.moonshot.cn/v1` |
| `DEEPSEEK_BASE_URL` | 深度求索（DeepSeek）API 回源地址 | `https://api.deepseek.com` |
| `ZAI_BASE_URL` | 智谱（Zai）API 回源地址 | `https://open.bigmodel.cn/api/paas/v4` |
| `BACKEND_URL` | 后端服务地址（用于用量结算） | - |

## 部署步骤

### 步骤 1：配置 KV 命名空间

KV 命名空间已在 `wrangler.jsonc` 中配置：

```jsonc
"kv_namespaces": [
  {
    "binding": "KV_CACHE",
    "id": "3d33fd5a9f8d493ea65a693fae7df4ba"  // 生产环境
    // "id": "llm-router-kv-cache"  // 开发环境
  }
]
```

如需创建新的 KV 命名空间：
```bash
# 生产环境
npx wrangler kv namespace create "llm-router-cache"

# 开发环境
npx wrangler kv namespace create "llm-router-cache-dev"
```

### 步骤 2：配置 Queue

Queue 配置已在 `wrangler.jsonc` 中指定：

```jsonc
"queues": {
  "producers": [
    {
      "binding": "USAGE_QUEUE",
      "queue": "llm-router-usage"  // 生产环境
      // "queue": "llm-router-usage-dev"  // 开发环境
    }
  ],
  "consumers": [
    {
      "queue": "llm-router-usage",
      "max_batch_size": 100,
      "max_batch_timeout": 30,
      "max_retries": 3
    }
  ]
}
```

如需创建新的 Queue：
```bash
# 生产环境
npx wrangler queues create llm-router-usage

# 开发环境
npx wrangler queues create llm-router-usage-dev
```

### 步骤 3：配置 Cron Trigger

用量结算定时任务已在 `wrangler.jsonc` 中配置：

```jsonc
"triggers": {
  "crons": [
    "0 * * * *"      // 生产环境：每小时执行
    // "*/10 * * * *"  // 开发环境：每10分钟执行
  ]
}
```

### 步骤 4：修改部署配置（重要）

在部署前，必须修改 `wrangler.jsonc` 中的以下配置为你的实际域名：

**1. 修改 Routes（路由）：**
```jsonc
// 生产环境 - 修改为你的域名
"routes": [
  {
    "pattern": "llm.your-domain.com/api/*",
    "zone_name": "your-domain.com"
  },
  {
    "pattern": "llm.your-domain.com/worker/*",
    "zone_name": "your-domain.com"
  }
]

// 开发环境 - 修改为你的测试域名
"routes": [
  {
    "pattern": "test-llm.your-domain.com/api/*",
    "zone_name": "your-domain.com"
  },
  {
    "pattern": "test-llm.your-domain.com/worker/*",
    "zone_name": "your-domain.com"
  }
]
```

**2. 修改 BACKEND_URL（后端地址）：**
```jsonc
// 生产环境
"vars": {
  "BACKEND_URL": "https://llm.your-domain.com",
  ...
}

// 开发环境
"vars": {
  "BACKEND_URL": "https://test-llm.your-domain.com",
  ...
}
```

### 步骤 5：部署 Worker

**生产环境部署：**
```bash
npx wrangler deploy --env production
```

部署成功后，Worker 将可通过你配置的地址访问。

**开发环境部署（如需预览环境）：**
```bash
npx wrangler deploy --env development
```

> **注意**：日常开发建议使用 `npx wrangler dev --env development` 本地运行，而非部署到 Cloudflare。

## 本地开发

开发模式在本地运行 Worker，通过 Cloudflare Tunnel 将请求反代到本地电脑，无需部署到 Cloudflare。

### 1. 配置本地环境变量

创建 `.dev.vars` 文件（参考 `.dev.vars.example`）：

```bash
# .dev.vars
MOONSHOT_BASE_URL="https://api.moonshot.cn/v1"
DEEPSEEK_BASE_URL="https://api.deepseek.com"
ZAI_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
BACKEND_URL=http://localhost:12000
MOONSHOT_API_KEY="sk-xxx"
DEEPSEEK_API_KEY="sk-xxx"
ZAI_API_KEY="sk-xxx"
INTERNAL_SECRET="sk-xxx"
```

> 开发环境的 Secrets 直接写入 `.dev.vars` 文件，无需使用 `wrangler secret put`。

### 2. 启动本地开发服务器

```bash
# 启动本地开发服务器（使用 development 环境配置）
npx wrangler dev --env development
```

Worker 将在本地启动，默认监听 `http://localhost:8787`。

### 3. 配置 Cloudflare Tunnel

使用 Cloudflare Tunnel 将外部请求反向代理到本地开发环境：

1. 在本地启动 cloudflared 并连接到 Cloudflare
2. 在 Cloudflare Dashboard 中配置 Tunnel 路由
3. 配置域名将以下路径路由到本地服务：
   - `/api/*` → Worker (`http://localhost:8787`)
   - `/internal/*` → 源服务器 (`http://localhost:12000`)

开发环境的路由配置（`wrangler.jsonc`，仅 Worker 路由）：
```jsonc
"routes": [
  {
    "pattern": "test-llm.your-domain.com/api/*",
    "zone_name": "your-domain.com"
  },
  {
    "pattern": "test-llm.your-domain.com/worker/*",
    "zone_name": "your-domain.com"
  }
]
```

## 配置检查清单

部署前请确认以下配置：

### 通用配置
- [ ] KV 命名空间 `KV_CACHE` 已创建并绑定
- [ ] Queue `llm-router-usage`（生产）或 `llm-router-usage-dev`（开发）已创建
- [ ] Queue Consumer 已配置
- [ ] Cron Trigger 已配置（每小时执行）

### 部署前必须修改
- [ ] `wrangler.jsonc` 中的 Routes 已修改为你的域名
- [ ] `wrangler.jsonc` 中的 `BACKEND_URL` 已修改为你的域名
- [ ] KV 命名空间 ID 已更新为你创建的 ID

### 生产环境 (`production`)
- [ ] `MOONSHOT_API_KEY` Secret 已设置
- [ ] `DEEPSEEK_API_KEY` Secret 已设置
- [ ] `ZAI_API_KEY` Secret 已设置（如使用智谱）
- [ ] `INTERNAL_SECRET` Secret 已设置
- [ ] `vars` 中的各提供商 `BASE_URL` 已正确配置

### 开发环境（本地运行）
- [ ] `.dev.vars` 文件已创建并配置所有 Secrets
- [ ] `npx wrangler dev --env development` 可以正常启动
- [ ] Cloudflare Tunnel 可以正常转发请求

## 回源地址说明

### 月之暗面（Moonshot）回源地址
- 官方地址：`https://api.moonshot.cn/v1`
- 如需使用代理或中转服务，修改 `MOONSHOT_BASE_URL`

### 深度求索（DeepSeek）回源地址
- 官方地址：`https://api.deepseek.com`
- 如需使用代理或中转服务，修改 `DEEPSEEK_BASE_URL`

### 智谱（Zai）回源地址
- 官方地址：`https://open.bigmodel.cn/api/paas/v4`
- 如需使用代理或中转服务，修改 `ZAI_BASE_URL`

### 后端服务地址 (BACKEND_URL)
用于用量结算，Worker 会将用量数据推送到此地址：
- 开发环境：`http://localhost:12000`
- 生产环境：`https://llm.mrzero.site`（或你的域名）

## Internal Secret 说明

`INTERNAL_SECRET` 用于 Worker 与后端服务之间的安全通信：

1. **用量结算** 使用它向 `BACKEND_URL` 推送用量数据时进行认证
2. **后端服务** 需要验证此 Secret 以确保请求来自合法的 Worker

建议生成强随机字符串作为 `INTERNAL_SECRET`：
```bash
openssl rand -base64 32
```

## 故障排查

### 部署失败
```bash
# 查看详细错误信息
npx wrangler deploy --env production --dry-run

# 验证配置文件
npx wrangler deploy --env production --outdir dist
```

### Secrets 未生效
```bash
# 列出已设置的 Secrets
npx wrangler secret list --env production

# 重新设置 Secret
npx wrangler secret put INTERNAL_SECRET --env production
```

### 查看日志
```bash
# 实时查看生产环境日志
npx wrangler tail --env production

# 实时查看开发环境日志
npx wrangler tail --env development
```

## 参考文档

- [Wrangler 配置文档](https://developers.cloudflare.com/workers/wrangler/configuration/)
- [Workers Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
- [Workers KV](https://developers.cloudflare.com/kv/)
- [Workers Queues](https://developers.cloudflare.com/queues/)
- [Workers Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
