#!/bin/bash
# =============================================================================
# go-wrk 压测命令速查手册
# =============================================================================
#
# 安装 go-wrk:
#   go install github.com/tsliwowicz/go-wrk@latest
#
#   或者下载二进制:
#   https://github.com/tsliwowicz/go-wrk/releases
#
# =============================================================================

# -----------------------------------------------------------------------------
# 基础用法
# -----------------------------------------------------------------------------

# 默认参数测试
# -c 400: 400 个并发连接
# -d 5:   持续 5 秒
go-wrk -c 400 -d 5 http://10.4.169.108:12000/api/v1/ping

# 指定线程数 (默认自动，一般不需要改)
go-wrk -c 400 -d 5 -t 8 http://10.4.169.108:12000/api/v1/ping

# 设置超时时间
go-wrk -c 400 -d 5 -T 10 http://10.4.169.108:12000/api/v1/ping


# -----------------------------------------------------------------------------
# 常用并发度测试 (用于找最佳并发点)
# -----------------------------------------------------------------------------

# 低并发基准
go-wrk -c 50  -d 5 http://10.4.169.108:12000/api/v1/ping
go-wrk -c 100 -d 5 http://10.4.169.108:12000/api/v1/ping

# 中等并发
go-wrk -c 200 -d 5 http://10.4.169.108:12000/api/v1/ping
go-wrk -c 300 -d 5 http://10.4.169.12000/api/v1/ping

# 高并发 (你目前用的)
go-wrk -c 400 -d 5 http://10.4.169.108:12000/api/v1/ping

# 超高并发 (如果 Slowest < 1s 可以尝试)
go-wrk -c 500 -d 5 http://10.4.169.108:12000/api/v1/ping
go-wrk -c 1000 -d 5 http://10.4.169.108:12000/api/v1/ping


# -----------------------------------------------------------------------------
# 不同接口测试
# -----------------------------------------------------------------------------

# --- 基础接口 ---

# Ping 接口 (无 DB, 无 Auth, 纯网络开销)
go-wrk -c 400 -d 5 http://10.4.169.108:12000/api/v1/ping

# Health 检查
go-wrk -c 400 -d 5 http://10.4.169.108:12000/api/v1/health


# --- 业务接口 (需要 API Key) ---

# 设置 API Key (从 .env 或数据库获取)
API_KEY="your_api_key_here"

# Models 接口 - 获取模型列表 (带缓存，有 DB 查询)
# 注意: 第一次请求会查询 DB，后续 5 分钟内走缓存
go-wrk -c 50 -d 5 \
    -H "Authorization: Bearer ${API_KEY}" \
    http://10.4.169.108:12000/api/v1/models


# Chat Completions 接口 - 核心业务 (需要 POST + JSON Body)
# 注意: 这个接口会真实调用 LLM Provider，压测时注意费用!

# 非流式请求 (stream=false)
go-wrk -c 10 -d 30 \
    -M POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_KEY}" \
    -b '{"model":"deepseek/deepseek-chat","messages":[{"role":"user","content":"你好"}],"stream":false}' \
    -T 60 \
    http://10.4.169.108:12000/api/v1/chat/completions

# 流式请求 (stream=true) - 注意: go-wrk 可能无法正确处理 SSE 流
go-wrk -c 10 -d 30 \
    -M POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${API_KEY}" \
    -b '{"model":"kimi/kimi-latest","messages":[{"role":"user","content":"你好"}],"stream":true}' \
    -T 60 \
    http://10.4.169.108:12000/api/v1/chat/completions


# --- 业务接口压力梯度测试 ---

# Models 接口梯度 (注意缓存影响，首次测试前先预热)
go-wrk -c 10  -d 10 -H "Authorization: Bearer ${API_KEY}" http://10.4.169.108:12000/api/v1/models
go-wrk -c 50  -d 10 -H "Authorization: Bearer ${API_KEY}" http://10.4.169.108:12000/api/v1/models
go-wrk -c 100 -d 10 -H "Authorization: Bearer ${API_KEY}" http://10.4.169.108:12000/api/v1/models

# Chat 接口梯度 (注意: 会产生真实 LLM 调用费用!)
# 建议先用低并发测试，确认稳定后再提高
# -c 1:  串行测试，测单请求延迟
go-wrk -c 1 -d 30 -M POST -H "Content-Type: application/json" -H "Authorization: Bearer ${API_KEY}" -b '{"model":"deepseek/deepseek-chat","messages":[{"role":"user","content":"你好"}],"stream":false}' -T 60 http://10.4.169.108:12000/api/v1/chat/completions

# -c 5:  低并发
go-wrk -c 5 -d 30 -M POST -H "Content-Type: application/json" -H "Authorization: Bearer ${API_KEY}" -b '{"model":"deepseek/deepseek-chat","messages":[{"role":"user","content":"你好"}],"stream":false}' -T 60 http://10.4.169.108:12000/api/v1/chat/completions

# -c 10: 中等并发 (根据 Provider 限流调整)
go-wrk -c 10 -d 30 -M POST -H "Content-Type: application/json" -H "Authorization: Bearer ${API_KEY}" -b '{"model":"deepseek/deepseek-chat","messages":[{"role":"user","content":"你好"}],"stream":false}' -T 60 http://10.4.169.108:12000/api/v1/chat/completions


# -----------------------------------------------------------------------------
# 常用参数参考
# -----------------------------------------------------------------------------
#
# -c N    并发连接数 (connections)
# -d N    测试持续时间，单位秒 (duration)
# -t N    线程数 (threads)，默认等于 CPU 核心数
# -T N    超时时间，单位秒 (timeout)
# -H K:V  添加 HTTP Header，如: -H "Authorization: Bearer xxx"
# -M STR  HTTP 方法，默认 GET，可设 POST/PUT/DELETE 等
# -b STR  请求 body，用于 POST/PUT 测试
# -f STR  从文件读取请求 body
#


# -----------------------------------------------------------------------------
# 结果解读速查
# -----------------------------------------------------------------------------
#
# Requests/sec: XXXXX.XX   <-- 关键指标: 每秒请求数
# Avg Req Time: X.XXXXms   <-- 平均延迟
# Slowest Request: X.XXms  <-- 最慢请求 (超过 1秒要降并发)
#
# Latency Distribution:
#   50%: X.XXms   (中位数，一半请求快于这个值)
#   90%: X.XXms   (90%请求快于这个值，关注这个)
#   99%: X.XXms   (尾部延迟)
#


# -----------------------------------------------------------------------------
# 接口特点说明
# -----------------------------------------------------------------------------
#
# Ping/Health:
#   - 无鉴权、无 DB、无 Provider 调用
#   - 测试纯网络+框架开销
#   - 可以用高并发 (-c 400+)
#
# Models:
#   - 需要鉴权 (Authorization Header)
#   - 首次请求查 DB，后续 5 分钟缓存
#   - 建议先预热: curl -H "Authorization: Bearer xxx" <url>
#   - 并发建议 -c 50~100
#
# Chat Completions:
#   - 核心业务接口，会真实调用 LLM Provider
#   - 需要鉴权 + POST JSON Body
#   - 注意: 会产生真实 API 调用费用!
#   - 注意: 受 Provider 限流影响 (RPM/TPS)
#   - 建议并发 -c 5~20，根据 Provider 限制调整
#   - 超时设长一点 (-T 60) 因为 LLM 响应较慢
#
#
# -----------------------------------------------------------------------------
# 重要提示
# -----------------------------------------------------------------------------
#
# 如果 Slowest Request > 1秒 (1000ms):
#   说明并发过高，服务器过载
#   应该降低 -c 参数重新测试
#
# 找到最佳并发度的方法:
#   从低到高测试，找到 RPS 最高且 Slowest < 1s 的点
#
# Chat 接口压测特别注意:
#   1. 先设置正确的 API_KEY
#   2. 确认账户余额充足
#   3. 了解 Provider 的限流策略
#   4. 从 -c 1 开始逐步增加
#   5. 关注 90%/95% 延迟，平均值容易被长尾拉平
#
