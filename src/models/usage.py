"""
用量数据模型

用于接收 Worker 发送的用量结算数据
"""

from typing import Optional

from pydantic import BaseModel, Field


class UsageLogEntry(BaseModel):
    """用量日志条目 - 用于记录 token 使用情况"""

    # 请求标识
    requestId: str = Field(..., description="请求唯一标识")
    # 时间戳（毫秒）
    timestamp: int = Field(..., description="记录时间戳（毫秒）")
    # 用户标识
    userId: Optional[int] = Field(None, description="用户ID")
    # API Key 用途
    purpose: Optional[str] = Field(None, description="API Key 用途")
    # 提供商名称
    providerName: str = Field(..., description="LLM 提供商名称")
    # 模型名称（包含 provider 前缀，如 deepseek/deepseek-chat）
    modelName: str = Field(..., description="模型名称")
    # Prompt tokens（输入）
    promptTokens: int = Field(..., description="输入 token 数量", ge=0)
    # Completion tokens（输出）
    completionTokens: int = Field(..., description="输出 token 数量", ge=0)
    # 缓存命中 tokens
    cachedTokens: int = Field(0, description="缓存命中 token 数量", ge=0)
    # 总 tokens
    totalTokens: int = Field(..., description="总 token 数量", ge=0)
    # 是否为预估用量（流式响应断连时）
    isEstimated: Optional[bool] = Field(False, description="是否为预估用量")


class UsageSettlementRequest(BaseModel):
    """用量结算请求"""

    entries: list[UsageLogEntry] = Field(..., description="用量日志条目列表")


class UsageSettlementResponse(BaseModel):
    """用量结算响应"""

    success: bool = Field(..., description="是否处理成功")
    processedCount: int = Field(0, description="成功处理的条目数量", ge=0)
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
