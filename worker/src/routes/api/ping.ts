/**
 * 健康检查路由
 *
 * GET/POST /api/v1/ping - 服务健康检查
 */

import { Hono } from 'hono';
import type { Env } from '../../types';

const app = new Hono<{ Bindings: Env }>();

// GET /api/v1/ping
app.get('/', (c) => c.text('OK'));

// POST /api/v1/ping
app.post('/', (c) => c.text('OK'));

export default app;
