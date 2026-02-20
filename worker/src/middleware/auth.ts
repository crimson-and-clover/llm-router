/**
 * 认证中间件
 *
 * 验证 Bearer Token，加载 API Key 数据到上下文
 */

import type { MiddlewareHandler } from 'hono';
import type { Env, APIKeyData } from '../types';
import { HybridStorage } from '../storage/hybridStorage';

// 扩展 Hono Context 类型
declare module 'hono' {
	interface ContextVariableMap {
		apiKeyData: APIKeyData;
	}
}

/**
 * API Key 认证中间件
 * 验证 Authorization header 并加载 API Key 数据
 */
export const authMiddleware: MiddlewareHandler<{ Bindings: Env }> = async (c, next) => {
	const auth = c.req.header('Authorization');
	if (!auth || !auth.startsWith('Bearer ')) {
		return c.json({ error: 'Unauthorized' }, 401);
	}

	const apiKey = auth.slice(7);
	const storage = new HybridStorage(c.env);
	const keyData = await storage.getAPIKey(apiKey);

	if (!keyData) {
		return c.json({ error: 'Unauthorized' }, 401);
	}

	c.set('apiKeyData', keyData);
	await next();
};
