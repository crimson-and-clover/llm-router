/**
 * API 路由入口
 *
 * 组合所有 /api/* 路由
 */

import { Hono } from 'hono';
import type { Env } from '../../types';
import { authMiddleware } from '../../middleware/auth';
import modelsRouter from './models';
import pingRouter from './ping';
import chatRouter from './chat';

const app = new Hono<{ Bindings: Env }>();

// 认证中间件（应用于 /api/v1/*）
app.use('/v1/*', authMiddleware);

// 路由注册
app.route('/v1/models', modelsRouter);
app.route('/v1/ping', pingRouter);
app.route('/v1/chat/completions', chatRouter);

export default app;
