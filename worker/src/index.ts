/**
 * LLM Router Worker - 统一入口
 *
 * 处理三种事件类型：
 * 1. fetch - HTTP 请求（API 路由和 Worker 路由）
 * 2. queue - 用量队列消费
 * 3. scheduled - 定时任务
 */

import { Hono } from 'hono';
import type { Env, UsageLogEntry } from './types';
import { UsageSettler } from './core/settlement';
import apiRouter from './routes/api';
import workerRouter from './routes/worker';

// 创建主 Hono 应用
const app = new Hono<{ Bindings: Env }>();

// 挂载路由
app.route('/api', apiRouter);
app.route('/worker', workerRouter);

// 404 处理
app.notFound((c) => c.json({ error: 'Not Found' }, 404));

/**
 * 队列消息处理器
 * 消费用量队列消息，批量结算到后端
 */
async function handleQueue(batch: MessageBatch<UsageLogEntry>, env: Env, ctx: ExecutionContext): Promise<void> {
	console.log(`[Settlement] Received batch: ${batch.messages.length} messages`);

	const settler = new UsageSettler(env);

	try {
		// 提取所有消息体
		const entries = batch.messages.map((msg) => msg.body);

		// 批量结算
		const result = await settler.batchSettle(entries);

		if (result.success) {
			console.log(`[Settlement] Batch settled successfully: ${result.processedCount} entries`);
			// 确认所有消息已处理
			for (const msg of batch.messages) {
				msg.ack();
			}
		} else {
			console.error(`[Settlement] Batch settlement failed: ${result.error}`);
			// 标记所有消息为失败，将进入重试队列
			for (const msg of batch.messages) {
				msg.retry();
			}
		}
	} catch (error) {
		console.error('[Settlement] Unexpected error in queue handler:', error);
		// 发生异常时重试所有消息
		for (const msg of batch.messages) {
			msg.retry();
		}
	}
}

/**
 * 定时任务处理器
 * 用于执行定期任务（目前为空实现，预留扩展）
 */
async function handleScheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
	console.log(`[Scheduled] Trigger fired at ${new Date(event.scheduledTime).toISOString()}`);

	// 预留：未来可添加定期任务
	// 例如：清理过期缓存、健康检查、数据同步等
}

/**
 * Worker 导出
 * Cloudflare Workers 运行时入口
 */
export default {
	/**
	 * HTTP 请求处理器
	 */
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		return app.fetch(request, env, ctx);
	},

	/**
	 * 队列消息处理器
	 */
	async queue(batch: MessageBatch<UsageLogEntry>, env: Env, ctx: ExecutionContext): Promise<void> {
		return handleQueue(batch, env, ctx);
	},

	/**
	 * 定时任务处理器
	 */
	async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
		return handleScheduled(event, env, ctx);
	},
};
