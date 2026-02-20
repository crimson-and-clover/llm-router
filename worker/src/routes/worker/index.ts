/**
 * Worker 业务路由
 *
 * 用于接收业务通知的端点
 * 例如：/worker/notify 等
 */

import { Hono } from 'hono';
import type { Env } from '../../types';

const app = new Hono<{ Bindings: Env }>();

// GET /worker/health - 健康检查
app.get('/health', (c) => {
	return c.text('OK');
});

app.post('/health', (c) => {
	return c.text('OK');
});

// POST /worker/notify - 预留的业务通知端点
// 示例：接收后端通知执行某些任务
app.post('/notify', async (c) => {
	// TODO: 实现业务通知处理逻辑
	// 例如：刷新缓存、同步配置等

	return c.json({
		success: true,
		message: 'Notification received',
	});
});

export default app;
