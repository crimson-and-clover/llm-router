/**
 * 模型列表路由
 *
 * GET /api/v1/models - 获取可用模型列表
 */

import { Hono } from 'hono';
import type { Env, ModelsCacheData, ModelInfo } from '../../types';
import { DeepSeekProvider } from '../../providers/deepseek';
import { MoonshotProvider } from '../../providers/moonshot';
import { ZaiProvider } from '../../providers/zai';
import { TestProvider } from '../../providers/test';

const app = new Hono<{ Bindings: Env }>();

// 模型列表缓存配置
const MODELS_CACHE_KEY = 'models_list';
const MODELS_CACHE_TTL = 300; // 5分钟（秒）

// 允许的模型白名单（为空数组表示允许该 Provider 的所有模型）
const ALLOWED_MODELS: Record<string, string[]> = {
	deepseek: [
		'deepseek-chat',
		'deepseek-reasoner'
	],
	moonshot: [
		'kimi-k2.5',
		'kimi-k2-0905-preview',
		'kimi-k2-0711-preview',
		'kimi-k2-thinking',
	],
	zai: [
		'glm-5',
		'glm-4.7',
	],
	test: ['test'],
};

// GET /api/v1/models
app.get('/', async (c) => {
	const kv = c.env.KV_CACHE;

	// 1. 先查 KV 缓存
	try {
		const cached = await kv.get<ModelsCacheData>(MODELS_CACHE_KEY, 'json');
		if (cached) {
			console.log('[Models] Cache hit from KV');
			return c.json(cached);
		}
	} catch (e) {
		console.error('[Models] Failed to read from KV cache:', e);
	}

	// 2. 缓存未命中，从 Provider 获取
	const providers = {
		deepseek: new DeepSeekProvider(c.env),
		moonshot: new MoonshotProvider(c.env),
		zai: new ZaiProvider(c.env),
		test: new TestProvider(c.env),
	};

	const allModels: ModelInfo[] = [];

	for (const [providerName, provider] of Object.entries(providers)) {
		try {
			const modelsData = await provider.listModels();
			if (modelsData?.data) {
				// 获取该 Provider 的白名单
				const whitelist = ALLOWED_MODELS[providerName];

				for (const model of modelsData.data) {
					if (model.id) {
						// 如果白名单为空数组，允许所有模型；否则只允许白名单中的模型
						if (whitelist && whitelist.length > 0 && !whitelist.includes(model.id)) {
							console.log(`[Models] Skipping ${providerName}/${model.id} (not in whitelist)`);
							continue;
						}

						allModels.push({
							id: `${providerName}/${model.id}`,
							object: 'model',
							created: model.created || 0,
							owned_by: model.owned_by || providerName,
						});
					}
				}
			}
		} catch (e) {
			console.error(`[Models] Failed to get models from ${providerName}:`, e);
		}
	}

	const result: ModelsCacheData = {
		object: 'list',
		data: allModels,
	};

	// 3. 写入 KV 缓存
	try {
		await kv.put(MODELS_CACHE_KEY, JSON.stringify(result), {
			expirationTtl: MODELS_CACHE_TTL,
		});
		console.log('[Models] Cache written to KV');
	} catch (e) {
		console.error('[Models] Failed to write to KV cache:', e);
	}

	return c.json(result);
});

export default app;
