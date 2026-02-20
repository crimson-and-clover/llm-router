/**
 * 聊天补全路由
 *
 * POST /api/v1/chat/completions - 创建聊天补全
 */

import { Hono } from 'hono';
import { customAlphabet } from 'nanoid';
import type { Env, NormalizedUsage } from '../../types';
import type { PipelineContext } from '../../pipelines/base';
import { DeepSeekProvider } from '../../providers/deepseek';
import { MoonshotProvider } from '../../providers/moonshot';
import { ZaiProvider } from '../../providers/zai';
import { TestProvider } from '../../providers/test';
import { BasePipeline } from '../../pipelines/base';
import { CursorPipeline } from '../../pipelines/cursor';
import { StreamTracker } from '../../core/streamTracker';
import { createUsageLog, sendUsageLog, normalizeUsage, estimateUsage, estimatePromptTokens } from '../../core/usage';

const app = new Hono<{ Bindings: Env }>();

// 生成请求 ID（OpenAI 格式：chatcmpl-xxx）
function generateRequestId(): string {
	const alphabet = '0123456789abcdefghijklmnopqrstuvwxyz';
	const nanoid36 = customAlphabet(alphabet);
	return `chatcmpl-${nanoid36(32)}`;
}

// 允许的模型白名单
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

// POST /api/v1/chat/completions
app.post('/', async (c) => {
	let body: any;
	try {
		body = await c.req.json();
	} catch {
		return c.json({ error: 'Invalid Body' }, 400);
	}

	const model = body.model;
	if (!model || !model.includes('/')) {
		return c.json({ error: 'Model not found' }, 404);
	}

	const [providerName, realModelName] = model.split('/');

	const providers: Record<string, any> = {
		deepseek: new DeepSeekProvider(c.env),
		moonshot: new MoonshotProvider(c.env),
		zai: new ZaiProvider(c.env),
		test: new TestProvider(c.env),
	};

	const provider = providers[providerName];
	if (!provider) {
		return c.json({ error: 'Model not found' }, 404);
	}

	// 白名单检查
	const whitelist = ALLOWED_MODELS[providerName];
	if (whitelist && whitelist.length > 0 && !whitelist.includes(realModelName)) {
		console.log(`[Chat] Blocked model: ${providerName}/${realModelName} (not in whitelist)`);
		return c.json({ error: 'Model not found' }, 404);
	}

	// 获取 API Key 数据
	const apiKeyData = c.get('apiKeyData');

	// 选择 Pipeline
	const pipeline = apiKeyData?.purpose === 'cursor' ? new CursorPipeline() : new BasePipeline();

	// 获取用量队列
	const usageQueue = c.env.USAGE_QUEUE;

	// 生成请求 ID
	const requestId = generateRequestId();

	// 构建 Pipeline 上下文
	const ctx: PipelineContext = {
		requestId: requestId,
		modelName: realModelName,
		providerName: providerName,
		chatHistory: [] as any[],
		userId: apiKeyData?.user_id,
		purpose: apiKeyData?.purpose,
	};

	// 处理请求
	body.model = realModelName;
	const payload = pipeline.preprocessRequest(ctx, body);
	ctx.chatHistory = payload.messages || [];

	const stream = body.stream === true;

	if (!stream) {
		// 非流式响应
		const response = await provider.chatCompletions(payload);
		if (!response.ok) {
			const errorText = await response.text();
			console.error(`[Chat] Provider error: ${response.status} ${errorText}`);
			return c.json({ error: 'Internal Server Error' }, 500);
		}
		const data = await response.json();

		// 后处理响应
		const processed = pipeline.postprocessResponse(ctx, data as Record<string, any>);

		// 提取并标准化 usage
		let usage: NormalizedUsage | undefined;
		if (data.usage) {
			usage = normalizeUsage(data.usage);
			if (usage) {
				processed.usage = usage;
			}
		}
		// 如果没有 usage，使用兜底估算策略
		if (!usage) {
			console.log("No usage found, using fallback estimate strategy");
			const completionContent = data.choices?.[0] || {};
			usage = estimateUsage(ctx.chatHistory, completionContent);
		}

		// 发送用量日志（异步，不阻塞响应）
		if (usage) {
			const usageLog = createUsageLog({
				requestId: ctx.requestId,
				userId: ctx.userId,
				purpose: ctx.purpose,
				providerName: ctx.providerName,
				modelName: ctx.modelName,
				usage: usage,
				isEstimated: !data.usage, // 如果没有原始 usage，标记为估算
			});
			c.executionCtx.waitUntil(sendUsageLog(usageQueue, usageLog));
		}

		return c.json(processed);
	} else {
		// 流式响应
		const { response, iterator } = await provider.chatCompletionsStream(payload);
		const signal = c.req.raw.signal;

		if (!response.ok) {
			const errorText = await response.text();
			console.error(`[Chat] Provider stream error: ${response.status} ${errorText}`);
			return c.json({ error: 'Internal Server Error' }, 500);
		}

		// 创建流式跟踪器和 SSE 转换器
		const streamTracker = new StreamTracker();
		const transformer = pipeline.createSSETransformer(ctx);

		// 估算 prompt tokens
		const estimatedPromptTokens = estimatePromptTokens(ctx.chatHistory);

		// 标记是否已收到实际 usage
		let actualUsage: NormalizedUsage | undefined;
		let hasReceivedUsage = false;

		// 标记是否已完成清理（确保只执行一次）
		let finalized = false;

		// 统一的清理函数
		const handleFinalize = (reason: string) => {
			if (finalized) return;
			finalized = true;

			console.log(`[Stream] Finalizing: ${reason} for ${requestId}`);

			const usage = hasReceivedUsage && actualUsage
				? actualUsage
				: streamTracker.buildUsage(estimatedPromptTokens, 0);

			const usageLog = createUsageLog({
				requestId: ctx.requestId,
				userId: ctx.userId,
				purpose: ctx.purpose,
				providerName: ctx.providerName,
				modelName: ctx.modelName,
				usage: usage,
				isEstimated: !hasReceivedUsage,
			});
			c.executionCtx.waitUntil(sendUsageLog(usageQueue, usageLog));
		};

		// 处理单行 SSE 数据的辅助函数
		const processLine = (line: string): string[] => {
			const trimmed = line.trim();
			if (!trimmed) {
				return [line];
			}
			if (!trimmed.startsWith('data: ')) {
				return [line];
			}
			const dataContent = trimmed.slice(6);
			if (dataContent === '[DONE]') {
				return [line];
			}

			// 尝试解析 JSON
			let data: Record<string, any>;
			try {
				data = JSON.parse(dataContent);
			} catch (e) {
				// JSON 解析失败，原样返回
				console.warn(`[SSE] JSON parse failed for line: ${line.slice(0, 100)}...`);
				return [line];
			}

			try {
				// 设置请求 ID
				data.id = ctx.requestId;
				delete data.system_fingerprint;
				data.model = `${ctx.providerName}/${ctx.modelName}`;

				// 跟踪 delta 内容（用于估算）
				const delta = data.choices?.[0]?.delta;
				if (delta?.content) {
					streamTracker.trackContent(delta.content);
				}
				if (delta?.reasoning_content) {
					streamTracker.trackContent(delta.reasoning_content);
				}
				if (delta?.tool_calls) {
					streamTracker.trackContent(JSON.stringify(delta.tool_calls));
				}

				// 检查是否收到 usage
				if (data.usage) {
					const usage = normalizeUsage(data.usage);
					if (usage) {
						streamTracker.recordActualUsage(usage);
						actualUsage = usage;
						hasReceivedUsage = true;
						data.usage = usage;
					}
				}

				// 应用转换（可能返回多个消息）
				const transformedList = transformer(data);
				return transformedList.map(transformed => `data: ${JSON.stringify(transformed)}`);
			} catch (e) {
				// 处理过程中出错，返回原始 data 行
				console.error(`[SSE] Processing error:`, e);
				return [`data: ${JSON.stringify(data)}`];
			}
		};

		// 创建 TransformStream 处理 SSE 数据转换
		const transformStream = new TransformStream<string, string>({
			transform(chunk, controller) {
				try {
					const processedLines = processLine(chunk);
					// 处理可能生成的多条消息
					for (const processedLine of processedLines) {
						controller.enqueue(processedLine + '\n\n');
					}
				} catch (lineError) {
					// 单条数据处理错误，记录但继续处理后续数据
					console.error(`[Chat] Line processing error:`, lineError, 'Line:', chunk);
					// 尝试原样发送原始数据，确保不丢失内容
					if (chunk && chunk.trim()) {
						controller.enqueue(chunk + '\n\n');
					}
				}
			},
			flush() {
				// 流正常结束时的清理
				handleFinalize('complete');
			},
			cancel(reason: any) {
				handleFinalize('cancel');
				console.log(`[Chat] TransformStream cancel:`, reason);
			},
		});

		// 监听 abort 信号，处理用户断连
		signal.addEventListener('abort', () => {
			handleFinalize('abort');
		});

		// 将 provider 数据写入 TransformStream 的 writable 端
		const writer = transformStream.writable.getWriter();
		const pump = async () => {
			try {
				for await (const line of iterator) {
					// 检查是否已中止
					if (signal.aborted) {
						console.log(`[Stream] Abort detected, stopping pump for ${requestId}`);
						break;
					}
					await writer.write(line);
				}
			} catch (e) {
				console.error(`[Chat] Pump error:`, e);
				// 发生错误时尝试完成清理
				handleFinalize('error');
				throw e;
			} finally {
				writer.close().catch(e => {
					console.error(`[Chat] Writer close error:`, e);
				});
			}
		};

		c.executionCtx.waitUntil(pump().catch(e => {
			console.error(`[Chat] Pump promise error:`, e);
		}));

		// 返回响应，使用 TransformStream 的 readable 端
		return new Response(
			transformStream.readable.pipeThrough(new TextEncoderStream()),
			{
				headers: {
					'Content-Type': 'text/event-stream; charset=utf-8',
					'Cache-Control': 'no-cache, no-transform',
					'Connection': 'keep-alive',
				},
			}
		);
	}
});

export default app;
