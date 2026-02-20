/**
 * Worker 配置模块
 *
 * 集中管理各类配置参数，便于统一调整和复用
 */

/**
 * Token 估算配置
 *
 * 基于经验值的字符到 token 转换系数
 * - 中文约 1:1.5 (1 token ≈ 1.5 字符)
 * - 英文约 1:0.3 (1 token ≈ 0.3 字符)
 * - 混合内容取平均值约 1:0.6-0.7
 */
export const TOKEN_ESTIMATE_CONFIG = {
	/** 每个 token 平均对应的字符数（用于字符数 -> token 数估算） */
	charsPerToken: 2,
	/** 每个字符平均对应的 token 数（用于 token 数 -> 字符数估算） */
	tokensPerChar: 0.5,
	/** 最小估算 token 数（避免零值） */
	minTokens: 1,
} as const;

/**
 * 根据字符数估算 token 数
 *
 * @param charCount 字符数
 * @returns 估算的 token 数
 */
export function estimateTokensFromChars(charCount: number): number {
	return Math.max(TOKEN_ESTIMATE_CONFIG.minTokens, Math.ceil(charCount / TOKEN_ESTIMATE_CONFIG.charsPerToken));
}

/**
 * 根据 token 数估算字符数
 *
 * @param tokenCount token 数
 * @returns 估算的字符数
 */
export function estimateCharsFromTokens(tokenCount: number): number {
	return Math.ceil(tokenCount * TOKEN_ESTIMATE_CONFIG.charsPerToken);
}
