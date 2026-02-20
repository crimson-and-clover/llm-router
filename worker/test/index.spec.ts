import { env, SELF } from 'cloudflare:test';
import { describe, it, expect, beforeAll, beforeEach, afterEach } from 'vitest';

// 测试用的 API Key
const TEST_API_KEY = 'test-api-key-12345';
const TEST_API_KEY_DATA = {
	key_value: TEST_API_KEY,
	user_id: 1,
	is_active: true,
	purpose: 'default' as const,
};

const CURSOR_API_KEY = 'cursor-api-key-67890';
const CURSOR_API_KEY_DATA = {
	key_value: CURSOR_API_KEY,
	user_id: 2,
	is_active: true,
	purpose: 'cursor' as const,
};

describe('LLM Router API Tests', () => {
	// 保存原始的 fetch
	let originalFetch: typeof globalThis.fetch;

	beforeAll(() => {
		originalFetch = globalThis.fetch;
	});

	beforeEach(() => {
		// Mock fetch 来模拟后端和 Provider API
		globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
			const url = input.toString();

			// Mock 后端 API Key 验证
			if (url.includes('/internal/keys/verify')) {
				const body = JSON.parse(init?.body as string || '{}');
				const key = body.key;

				if (key === TEST_API_KEY) {
					return new Response(JSON.stringify(TEST_API_KEY_DATA), {
						status: 200,
						headers: { 'Content-Type': 'application/json; charset=utf-8' },
					});
				}
				if (key === CURSOR_API_KEY) {
					return new Response(JSON.stringify(CURSOR_API_KEY_DATA), {
						status: 200,
						headers: { 'Content-Type': 'application/json; charset=utf-8' },
					});
				}
				return new Response(null, { status: 404 });
			}

			// Mock DeepSeek API
			if (url.includes('api.deepseek.com')) {
				if (url.includes('/models')) {
					return new Response(
						JSON.stringify({
							data: [
								{ id: 'deepseek-chat', object: 'model', created: 1700000000, owned_by: 'deepseek' },
								{ id: 'deepseek-reasoner', object: 'model', created: 1700000000, owned_by: 'deepseek' },
							],
						}),
						{ status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
					);
				}
				if (url.includes('/chat/completions')) {
					return new Response(
						JSON.stringify({
							id: 'chatcmpl-test',
							object: 'chat.completion',
							created: Date.now(),
							model: 'deepseek-chat',
							choices: [
								{
									index: 0,
									message: { role: 'assistant', content: 'Hello from DeepSeek!' },
									finish_reason: 'stop',
								},
							],
							usage: {
								prompt_tokens: 10,
								completion_tokens: 5,
								total_tokens: 15,
							},
						}),
						{ status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
					);
				}
			}

			// Mock Kimi API
			if (url.includes('api.moonshot.cn')) {
				if (url.includes('/models')) {
					return new Response(
						JSON.stringify({
							data: [
								{ id: 'kimi-latest', object: 'model', created: 1700000000, owned_by: 'moonshot' },
								{ id: 'kimi-k2.5', object: 'model', created: 1700000000, owned_by: 'moonshot' },
							],
						}),
						{ status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
					);
				}
				if (url.includes('/chat/completions')) {
					return new Response(
						JSON.stringify({
							id: 'chatcmpl-test',
							object: 'chat.completion',
							created: Date.now(),
							model: 'kimi-latest',
							choices: [
								{
									index: 0,
									message: { role: 'assistant', content: 'Hello from Kimi!' },
									finish_reason: 'stop',
								},
							],
							usage: {
								prompt_tokens: 10,
								completion_tokens: 5,
								total_tokens: 15,
							},
						}),
						{ status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
					);
				}
			}

			// 其他请求使用原始 fetch
			return originalFetch(input, init);
		};
	});

	afterEach(() => {
		globalThis.fetch = originalFetch;
	});

	describe('Health Check', () => {
		it('GET /api/v1/ping should return OK with valid API key', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/ping', {
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
				},
			});

			expect(response.status).toBe(200);
			const text = await response.text();
			expect(text).toBe('OK');
		});

		it('POST /api/v1/ping should return OK with valid API key', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/ping', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
				},
			});

			expect(response.status).toBe(200);
			const text = await response.text();
			expect(text).toBe('OK');
		});
	});

	describe('Authentication', () => {
		it('should return 401 without Authorization header', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/models');

			expect(response.status).toBe(401);
			const data = await response.json();
			expect(data).toHaveProperty('error');
		});

		it('should return 401 with invalid API key', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/models', {
				headers: {
					Authorization: 'Bearer invalid-key',
				},
			});

			expect(response.status).toBe(401);
			const data = await response.json();
			expect(data).toHaveProperty('error');
		});

		it('should return 401 with malformed Authorization header', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/models', {
				headers: {
					Authorization: 'Basic dGVzdDp0ZXN0',
				},
			});

			expect(response.status).toBe(401);
		});
	});

	describe('Models API', () => {
		it('GET /api/v1/models should return models list', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/models', {
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
				},
			});

			expect(response.status).toBe(200);
			const data = (await response.json()) as { object: string; data: any[] };
			expect(data.object).toBe('list');
			expect(Array.isArray(data.data)).toBe(true);

			// 验证模型格式为 provider/model
			const modelIds = data.data.map((m) => m.id);
			expect(modelIds.some((id) => id.startsWith('deepseek/'))).toBe(true);
			expect(modelIds.some((id) => id.startsWith('kimi/'))).toBe(true);
		});
	});

	describe('Chat Completions API', () => {
		it('should return 404 for invalid model format', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/chat/completions', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
					'Content-Type': 'application/json; charset=utf-8',
				},
				body: JSON.stringify({
					model: 'invalid-model-without-slash',
					messages: [{ role: 'user', content: 'Hello' }],
				}),
			});

			expect(response.status).toBe(404);
			const data = (await response.json()) as { error: string };
			expect(data.error).toBe('Model not found');
		});

		it('should return 404 for non-existent provider', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/chat/completions', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
					'Content-Type': 'application/json; charset=utf-8',
				},
				body: JSON.stringify({
					model: 'nonexistent/model-name',
					messages: [{ role: 'user', content: 'Hello' }],
				}),
			});

			expect(response.status).toBe(404);
			const data = (await response.json()) as { error: string };
			expect(data.error).toBe('Model not found');
		});

		it('should return 400 for invalid JSON body', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/chat/completions', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
					'Content-Type': 'application/json; charset=utf-8',
				},
				body: 'invalid json',
			});

			expect(response.status).toBe(400);
			const data = (await response.json()) as { error: string };
			expect(data.error).toBe('Invalid Body');
		});

		it('should handle chat completion with deepseek provider', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/chat/completions', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
					'Content-Type': 'application/json; charset=utf-8',
				},
				body: JSON.stringify({
					model: 'deepseek/deepseek-chat',
					messages: [{ role: 'user', content: 'Hello' }],
					stream: false,
				}),
			});

			expect(response.status).toBe(200);
			const data = (await response.json()) as { choices: any[]; usage: any };
			expect(data.choices).toBeDefined();
			expect(data.choices.length).toBeGreaterThan(0);
			expect(data.usage).toBeDefined();
		});

		it('should handle chat completion with kimi provider', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/chat/completions', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${TEST_API_KEY}`,
					'Content-Type': 'application/json; charset=utf-8',
				},
				body: JSON.stringify({
					model: 'kimi/kimi-latest',
					messages: [{ role: 'user', content: 'Hello' }],
					stream: false,
				}),
			});

			expect(response.status).toBe(200);
			const data = (await response.json()) as { choices: any[]; usage: any };
			expect(data.choices).toBeDefined();
			expect(data.choices.length).toBeGreaterThan(0);
		});

		it('should handle request with cursor API key', async () => {
			const response = await SELF.fetch('https://example.com/api/v1/chat/completions', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${CURSOR_API_KEY}`,
					'Content-Type': 'application/json; charset=utf-8',
				},
				body: JSON.stringify({
					model: 'deepseek/deepseek-chat',
					messages: [{ role: 'user', content: 'Hello' }],
					stream: false,
				}),
			});

			expect(response.status).toBe(200);
		});
	});
});
