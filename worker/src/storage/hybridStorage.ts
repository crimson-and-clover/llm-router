import type { Env, APIKeyData } from '../types';

export class HybridStorage {
	private kv: KVNamespace;
	private backendUrl: string;
	private internalSecret: string;

	// 缓存配置（单位：秒）
	private readonly CACHE_HIT_TTL = 600;      // Key有效：缓存10分钟
	private readonly CACHE_NOT_FOUND_TTL = 3600; // Key不存在：缓存1小时（防穿透）
	private readonly CACHE_REVOKED_TTL = 3600;  // Key被吊销：缓存1小时（防穿透）
	private readonly CACHE_ERROR_TTL = 60;     // 回源失败：缓存1分钟（快速重试）

	constructor(env: Env) {
		this.kv = env.KV_CACHE;
		this.backendUrl = env.BACKEND_URL;
		this.internalSecret = env.INTERNAL_SECRET;
	}

	/**
	 * 获取 API Key 信息
	 * 1. 先查 KV 缓存（包括"不存在"的标记）
	 * 2. 未命中则 HTTP 回源到 Python 后端
	 * 3. 回填 KV 缓存（无论是否存在，都写入缓存防穿透）
	 */
	async getAPIKey(keyValue: string): Promise<APIKeyData | null> {
		const cacheKey = `apikey:${keyValue}`;

		// 1. 查 KV 缓存（使用 getWithMetadata 区分"未缓存"和"缓存值为 null"）
		const { value: cached, metadata } = await this.kv.getWithMetadata<APIKeyData, { is_revoked?: boolean; is_not_found?: boolean; is_error?: boolean }>(cacheKey, 'json');

		// 检查缓存标记状态
		if (metadata?.is_revoked) {
			console.log(`[HybridStorage] Key cache hit (revoked): ${keyValue.slice(0, 10)}...`);
			return null;
		}
		if (metadata?.is_not_found) {
			console.log(`[HybridStorage] Key cache hit (not found): ${keyValue.slice(0, 10)}...`);
			return null;
		}
		if (metadata?.is_error) {
			console.log(`[HybridStorage] Key cache hit (error): ${keyValue.slice(0, 10)}...`);
			return null;
		}

		// 正常缓存命中
		if (cached) {
			console.log(`[HybridStorage] Key cache hit: ${keyValue.slice(0, 10)}...`);
			return cached;
		}
		// 2. KV 未命中，HTTP 回源
		console.log(`[HybridStorage] Key cache miss, fetching from backend: ${keyValue.slice(0, 10)}...`);

		try {
			const result = await this.fetchFromBackend(keyValue);

			// 3. 回填 KV（无论是否存在都缓存，防止穿透）
			if (result.found && result.data) {
				await this.kv.put(cacheKey, JSON.stringify(result.data), {
					expirationTtl: this.CACHE_HIT_TTL,
				});
				console.log(`[HybridStorage] Key cached (valid): ${keyValue.slice(0, 10)}...`);
				return result.data;
			} else if (result.revoked) {
				// Key 被吊销，缓存较长时间
				await this.kv.put(cacheKey, JSON.stringify(null), {
					expirationTtl: this.CACHE_REVOKED_TTL,
					metadata: {
						is_revoked: true,
					}
				});
				console.warn(`[HybridStorage] Key cached (revoked): ${keyValue.slice(0, 10)}...`);
				return null;
			} else {
				// Key 不存在，缓存较短时间，防止无效Key打崩后端
				await this.kv.put(cacheKey, JSON.stringify(null), {
					expirationTtl: this.CACHE_NOT_FOUND_TTL,
					metadata: {
						is_not_found: true,
					}
				});
				console.log(`[HybridStorage] Key cached (not found): ${keyValue.slice(0, 10)}...`);
				return null;
			}
		} catch (error) {
			console.error(`[HybridStorage] Failed to fetch key from backend:`, error);

			// 回源失败，短暂缓存错误状态，避免持续冲击后端，但保留快速重试机会
			await this.kv.put(cacheKey, JSON.stringify(null), {
				expirationTtl: this.CACHE_ERROR_TTL,
				metadata: {
					is_error: true,
				}
			});
			console.warn(`[HybridStorage] Key cached (error): ${keyValue.slice(0, 10)}...`);

			return null;
		}
	}

	/**
	 * HTTP 回源到 Python 后端验证 API Key
	 * @returns {found: true, data: APIKeyData} - Key 存在且有效
	 * @returns {found: false, revoked: true} - Key 被吊销
	 * @returns {found: false, revoked: false} - Key 不存在
	 * @throws - 后端请求失败
	 */
	private async fetchFromBackend(keyValue: string): Promise<
		| { found: true; data: APIKeyData; revoked?: false }
		| { found: false; revoked: true; data?: null }
		| { found: false; revoked: false; data?: null }
	> {
		const response = await fetch(`${this.backendUrl}/internal/keys/verify`, {
			method: 'POST',
			headers: {
				'Authorization': `Bearer ${this.internalSecret}`,
				'Content-Type': 'application/json; charset=utf-8',
			},
			body: JSON.stringify({ key: keyValue }),
		});

		if (response.status === 404) {
			// Key 不存在 - 缓存防穿透
			console.log(`[HybridStorage] Backend returned 404 (not found): ${keyValue.slice(0, 10)}...`);
			return { found: false, revoked: false };
		}

		if (response.status === 403) {
			// Key 被吊销 - 缓存较长时间
			console.warn(`[HybridStorage] Backend returned 403 (revoked): ${keyValue.slice(0, 10)}...`);
			return { found: false, revoked: true };
		}

		if (!response.ok) {
			throw new Error(`Backend returned ${response.status}: ${await response.text()}`);
		}

		const data: APIKeyData = await response.json();
		return { found: true, data };
	}

	/**
	 * 删除缓存（用于 Key 吊销后主动失效）
	 */
	async invalidateCache(keyValue: string): Promise<void> {
		await this.kv.delete(`apikey:${keyValue}`);
	}
}
