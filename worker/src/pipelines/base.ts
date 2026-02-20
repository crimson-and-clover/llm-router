import type { ChatCompletionRequest, ChatMessage } from '../types';

export interface PipelineContext {
	requestId: string;
	modelName: string;
	providerName: string;
	chatHistory: ChatMessage[];
	userId?: number;
	purpose?: string;
}

/**
 * SSE 数据转换函数类型
 * 返回数组支持一次输入生成多个输出消息
 */
export type SSETransformer = (data: Record<string, any>) => Record<string, any>[];

export class BasePipeline {
	preprocessRequest(ctx: PipelineContext, payload: ChatCompletionRequest): ChatCompletionRequest {
		console.log(`[Pipeline] RequestID: ${ctx.requestId} | Preprocess Request`);
		return payload;
	}

	/**
	 * 后处理非流式响应
	 * 将 reasoning_content 包装进 content
	 */
	postprocessResponse(
		ctx: PipelineContext,
		raw: Record<string, any>
	): Record<string, any> {
		console.log(`[Pipeline] RequestID: ${ctx.requestId} | Postprocess Response`);
		return raw;
	}

	/**
	 * 创建 SSE 数据转换函数
	 * 用于流式响应中实时转换数据
	 */
	createSSETransformer(ctx: PipelineContext): SSETransformer {
		return (data: Record<string, any>): Record<string, any>[] => {
			return [data];
		};
	}
}
