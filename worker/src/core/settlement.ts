/**
 * 用量结算模块
 *
 * 负责批量发送用量数据到后端进行结算
 */

import type { UsageLogEntry, Env } from '../types';

export interface SettlementResult {
	success: boolean;
	processedCount: number;
	error?: string;
}

export interface HealthCheckResult {
	ok: boolean;
	backendUrl: string;
	canConnect: boolean;
	error?: string;
}

export class UsageSettler {
	private env: Env;
	private backendUrl: string;
	private internalSecret: string;

	constructor(env: Env) {
		this.env = env;
		this.backendUrl = env.BACKEND_URL || '';
		this.internalSecret = env.INTERNAL_SECRET || '';
	}

	/**
	 * 批量结算用量数据
	 *
	 * @param entries 用量日志条目数组
	 * @returns 结算结果
	 */
	async batchSettle(entries: UsageLogEntry[]): Promise<SettlementResult> {
		if (entries.length === 0) {
			return { success: true, processedCount: 0 };
		}

		// 验证配置
		if (!this.backendUrl) {
			console.error('[Settlement] BACKEND_URL not configured');
			return { success: false, processedCount: 0, error: 'BACKEND_URL not configured' };
		}

		if (!this.internalSecret) {
			console.error('[Settlement] INTERNAL_SECRET not configured');
			return { success: false, processedCount: 0, error: 'INTERNAL_SECRET not configured' };
		}

		const settleUrl = `${this.backendUrl}/internal/usage/settle`;

		try {
			console.log(`[Settlement] Sending ${entries.length} entries to ${settleUrl}`);

			const response = await fetch(settleUrl, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json; charset=utf-8',
					'Authorization': `Bearer ${this.internalSecret}`,
				},
				body: JSON.stringify({ entries }),
			});

			if (!response.ok) {
				const errorText = await response.text();
				console.error(`[Settlement] Backend returned ${response.status}: ${errorText}`);
				return {
					success: false,
					processedCount: 0,
					error: `Backend returned ${response.status}: ${errorText}`,
				};
			}

			const result = await response.json() as SettlementResult;
			console.log(`[Settlement] Success: ${result.processedCount} entries processed`);

			return {
				success: true,
				processedCount: result.processedCount || entries.length,
			};
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.error('[Settlement] Failed to send to backend:', errorMessage);
			return {
				success: false,
				processedCount: 0,
				error: errorMessage,
			};
		}
	}

	/**
	 * 健康检查
	 * 验证后端连接状态
	 */
	async healthCheck(): Promise<HealthCheckResult> {
		if (!this.backendUrl) {
			return {
				ok: false,
				backendUrl: '',
				canConnect: false,
				error: 'BACKEND_URL not configured',
			};
		}

		try {
			// 尝试连接后端健康检查端点（如果存在）
			// 或者使用结算端点进行轻量级检查
			const healthUrl = `${this.backendUrl}/internal/health`;

			const response = await fetch(healthUrl, {
				method: 'GET',
				headers: {
					'Authorization': `Bearer ${this.internalSecret}`,
				},
			});

			return {
				ok: response.ok,
				backendUrl: this.backendUrl,
				canConnect: true,
			};
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			return {
				ok: false,
				backendUrl: this.backendUrl,
				canConnect: false,
				error: errorMessage,
			};
		}
	}
}
