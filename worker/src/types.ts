/**
 * Worker 环境变量
 *
 * 支持 fetch、queue、scheduled 三种事件处理
 */
export interface Env {
	// KV 命名空间（共享缓存）
	KV_CACHE: KVNamespace;

	// Queues - 既是生产者也是消费者
	USAGE_QUEUE: Queue;

	// Secrets - Provider API Keys
	MOONSHOT_API_KEY: string;
	DEEPSEEK_API_KEY: string;
	ZAI_API_KEY: string;

	// Secrets - 内部认证
	INTERNAL_SECRET: string;

	// Vars - Provider Base URLs
	MOONSHOT_BASE_URL: string;
	DEEPSEEK_BASE_URL: string;
	ZAI_BASE_URL: string;

	// Vars - 后端服务
	BACKEND_URL: string;
}

export interface APIKeyData {
	key_value: string;
	user_id: number;
	is_active: boolean;
	purpose: 'default' | 'cursor';
}

export interface ChatMessage {
	role: 'system' | 'user' | 'assistant' | 'tool';
	content: string | Array<{ type: string; text?: string; image_url?: { url: string } }>;
	name?: string;
	tool_calls?: any[];
	reasoning_content?: string;
}

export interface ChatCompletionRequest {
	model: string;
	messages: ChatMessage[];
	stream?: boolean;
	temperature?: number;
	max_tokens?: number;
	tools?: any[];
}

// 模型信息
export interface ModelInfo {
	id: string;
	object: 'model';
	created: number;
	owned_by: string;
}

// 模型列表缓存数据结构
export interface ModelsCacheData {
	object: 'list';
	data: ModelInfo[];
}

// 用量日志条目 - 用于记录 token 使用情况
export interface UsageLogEntry {
	// 请求标识
	requestId: string;
	// 时间戳（毫秒）
	timestamp: number;
	// 用户标识
	userId?: number;
	// API Key 用途
	purpose?: string;
	// 提供商名称
	providerName: string;
	// 模型名称（包含 provider 前缀，如 deepseek/deepseek-chat）
	modelName: string;
	// Prompt tokens（输入）
	promptTokens: number;
	// Completion tokens（输出）
	completionTokens: number;
	// 缓存命中 tokens
	cachedTokens: number;
	// 总 tokens
	totalTokens: number;
	// 是否为预估用量（流式响应断连时）
	isEstimated?: boolean;
}

// 统一用量格式
export interface NormalizedUsage {
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	cached_tokens?: number;
}
