/**
 * 用量记录模块 - 只记录 token 使用情况，不计算价格
 *
 * 设计原则：
 * 1. 只记录用量数据，价格计算由后端处理
 * 2. 使用 ctx.waitUntil() 异步发送，不阻塞响应
 * 3. 流式响应支持预估用量（用户断连时）
 */

import type { UsageLogEntry, NormalizedUsage } from '../types';
import { estimateTokensFromChars } from '../core/config';

/**
 * 从不同格式的 usage 中提取统一的字段
 *
 * 支持格式：
 * 1. DeepSeek: { prompt_tokens, completion_tokens, total_tokens, prompt_tokens_details: { cached_tokens } }
 * 2. 标准格式: { prompt_tokens, completion_tokens, total_tokens, cached_tokens }
 */
export function normalizeUsage(usage: Record<string, any> | undefined): NormalizedUsage | undefined {
	if (!usage) return undefined;

	const promptTokens = usage.prompt_tokens ?? 0;
	const completionTokens = usage.completion_tokens ?? 0;
	const totalTokens = usage.total_tokens ?? promptTokens + completionTokens;
	if (!usage.prompt_tokens) {
		console.error("Normalize Usage: prompt_tokens not found for line: ", JSON.stringify(usage));
		return undefined;
	}
	if (!usage.completion_tokens) {
		console.error("Normalize Usage: completion_tokens not found for line: ", JSON.stringify(usage));
		return undefined;
	}
	if (!usage.total_tokens) {
		console.warn("Normalize Usage: total_tokens not found for line: ", JSON.stringify(usage));
	}

	// 提取 cached_tokens（支持多种格式）
	let cachedTokens = 0;
	if (usage.cached_tokens !== undefined) {
		cachedTokens = usage.cached_tokens;
	} else if (usage.prompt_tokens_details?.cached_tokens !== undefined) {
		cachedTokens = usage.prompt_tokens_details.cached_tokens;
	} else if (usage.prompt_cache_hit_tokens !== undefined) {
		cachedTokens = usage.prompt_cache_hit_tokens;
	}

	return {
		prompt_tokens: promptTokens,
		completion_tokens: completionTokens,
		total_tokens: totalTokens,
		cached_tokens: cachedTokens,
	};
}

/**
 * 估算用量（当 Provider 未返回 usage 时使用）
 * @param chatHistory 请求消息历史
 * @param completionContent 响应内容
 * @returns 标准化的用量数据
 */
export function estimateUsage(
	chatHistory: any[],
	completionContent: any
): NormalizedUsage {
	const promptChars = chatHistory.reduce((sum: number, m: any) => {
		return sum + JSON.stringify(m.content).length;
	}, 0);
	const completionChars = JSON.stringify(completionContent).length;
	const promptTokens = estimateTokensFromChars(promptChars);
	const completionTokens = estimateTokensFromChars(completionChars);
	console.debug("Estimate Usage: promptTokens=", promptTokens, "completionTokens=", completionTokens);
	return {
		prompt_tokens: promptTokens,
		completion_tokens: completionTokens,
		total_tokens: promptTokens + completionTokens,
		cached_tokens: 0,
	};
}

export function estimatePromptTokens(
	chatHistory: any[],
): number {
	const promptChars = chatHistory.reduce((sum: number, m: any) => {
		return sum + JSON.stringify(m.content).length;
	}, 0);
	const promptTokens = estimateTokensFromChars(promptChars);
	return promptTokens;
}

/**
 * 创建用量日志条目
 */
export function createUsageLog(params: {
	requestId: string;
	userId?: number;
	purpose?: string;
	providerName: string;
	modelName: string;
	usage: NormalizedUsage;
	isEstimated?: boolean;
}): UsageLogEntry {
	return {
		requestId: params.requestId,
		timestamp: Date.now(),
		userId: params.userId,
		purpose: params.purpose,
		providerName: params.providerName,
		modelName: params.modelName,
		promptTokens: params.usage.prompt_tokens,
		completionTokens: params.usage.completion_tokens,
		cachedTokens: params.usage.cached_tokens ?? 0,
		totalTokens: params.usage.total_tokens,
		isEstimated: params.isEstimated ?? false,
	};
}

/**
 * 发送用量日志到 Cloudflare Queue
 *
 * @param queue Cloudflare Queue 绑定
 * @param entry 用量日志条目
 */
export async function sendUsageLog(queue: Queue, entry: UsageLogEntry): Promise<void> {
	try {
		await queue.send(entry);
		const type = entry.isEstimated ? 'Estimated' : 'Actual';
		console.log(
			`[Usage] ${type} | ${entry.requestId} | ` +
			`Tokens: ${entry.promptTokens}/${entry.completionTokens}/${entry.cachedTokens} | ` +
			`Total: ${entry.totalTokens}`
		);
	} catch (error) {
		console.error(`[Usage] Failed to send: ${entry.requestId}`, error);
	}
}

/**
 * 批量发送用量日志到 Cloudflare Queue
 *
 * @param queue Cloudflare Queue 绑定
 * @param entries 用量日志条目数组
 */
export async function sendUsageLogs(queue: Queue, entries: UsageLogEntry[]): Promise<void> {
	if (entries.length === 0) return;

	try {
		const messages = entries.map((entry) => ({ body: entry }));
		await queue.sendBatch(messages);
		console.log(`[Usage] Batch sent: ${entries.length} entries`);
	} catch (error) {
		console.error(`[Usage] Failed to batch send, falling back to individual:`, error);
		// 失败时逐个重试
		for (const entry of entries) {
			try {
				await queue.send(entry);
			} catch (e) {
				console.error(`[Usage] Failed to send individual entry: ${entry.requestId}`, e);
			}
		}
	}
}
