/**
 * 流式响应跟踪器 - 只跟踪 token 用量，不计算价格
 *
 * 用于：
 * 1. 跟踪流式响应中发送的内容长度（用于断连时预估）
 * 2. 记录实际收到的 usage 数据
 * 3. 在用户断连时提供预估的 usage 数据
 */

import { NormalizedUsage } from '../types';
import { estimateTokensFromChars } from './config';

export interface StreamTrackingInfo {
	// 已发送的字符数（用于估算）
	sentChars: number;
	// 已发送的行数
	sentLines: number;
	// 是否收到最终的 usage
	hasReceivedUsage: boolean;
	// 实际 usage（如果收到）
	actualUsage?: NormalizedUsage;
}

export class StreamTracker {
	private info: StreamTrackingInfo = {
		sentChars: 0,
		sentLines: 0,
		hasReceivedUsage: false,
	};

	/**
	 * 跟踪发送的文本内容
	 */
	trackContent(content: string): void {
		this.info.sentChars += content.length;
		this.info.sentLines++;
	}

	/**
	 * 记录收到的实际 usage
	 */
	recordActualUsage(usage: NormalizedUsage): void {
		this.info.actualUsage = usage;
		this.info.hasReceivedUsage = true;
	}

	/**
	 * 估算 completion tokens（用于用户断连时）
	 */
	estimateCompletionTokens(): number {
		if (this.info.hasReceivedUsage && this.info.actualUsage) {
			return this.info.actualUsage.completion_tokens;
		}
		// 基于字符数估算
		return estimateTokensFromChars(this.info.sentChars);
	}

	/**
	 * 获取当前跟踪信息
	 */
	getInfo(): StreamTrackingInfo {
		return { ...this.info };
	}

	/**
	 * 是否已收到实际 usage
	 */
	hasActualUsage(): boolean {
		return this.info.hasReceivedUsage;
	}

	/**
	 * 获取实际 usage（如果已收到）
	 */
	getActualUsage(): NormalizedUsage | undefined {
		return this.info.actualUsage;
	}

	/**
	 * 根据 prompt tokens 和实际/估算的 completion tokens 构建用量数据
	 *
	 * @param promptTokens 输入 token 数
	 * @param cachedTokens 缓存 token 数
	 * @returns NormalizedUsage 对象
	 */
	buildUsage(promptTokens: number, cachedTokens: number = 0): NormalizedUsage {
		if (this.info.hasReceivedUsage && this.info.actualUsage) {
			return this.info.actualUsage;
		}

		const completionTokens = this.estimateCompletionTokens();
		return {
			prompt_tokens: promptTokens,
			completion_tokens: completionTokens,
			total_tokens: promptTokens + completionTokens,
			cached_tokens: cachedTokens,
		};
	}
}
