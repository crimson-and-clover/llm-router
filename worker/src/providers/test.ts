import { BaseProvider, ModelData, StreamResponse } from './base';
import type { ChatCompletionRequest, Env } from '../types';

/**
 * Test Provider - 用于性能测试的模拟 Provider
 * 此 Provider 不调用外部 API，而是快速返回模拟响应，
 * 用于测试 API Mirror 本身的性能而不受外部服务影响。
 */
export class TestProvider implements BaseProvider {
	private env: Env;
	private fixedResponse: string;
	private responseDelayMs: number;
	private streamChunkCount: number;
	private streamChunkDelayMs: number;

	constructor(
		env: Env,
		options: {
			fixedResponse?: string;
			responseDelayMs?: number;
			streamChunkCount?: number;
			streamChunkDelayMs?: number;
		} = {}
	) {
		this.env = env;
		this.fixedResponse = options.fixedResponse ?? 'Hello! 这是测试响应。';
		this.responseDelayMs = options.responseDelayMs ?? 0;
		this.streamChunkCount = options.streamChunkCount ?? 10;
		this.streamChunkDelayMs = options.streamChunkDelayMs ?? 0;
	}

	/**
	 * 将内容分割成多个块
	 */
	private splitContent(content: string, chunks: number): string[] {
		const words = content.split(' ');
		if (chunks >= words.length) {
			return words;
		}

		const result: string[] = [];
		const chunkSize = Math.floor(words.length / chunks);
		for (let i = 0; i < chunks; i++) {
			const start = i * chunkSize;
			const end = i === chunks - 1 ? words.length : (i + 1) * chunkSize;
			result.push(words.slice(start, end).join(' '));
		}
		return result;
	}

	/**
	 * 根据用户消息生成响应内容
	 */
	private generateResponseContent(userMessage: string): string {
		const lowerMsg = userMessage.toLowerCase();
		if (lowerMsg.includes('hello') || lowerMsg.includes('hi')) {
			return 'Hello! This is TestProvider speaking.';
		}
		if (lowerMsg.includes('long') || lowerMsg.includes('paragraph')) {
			return 'This is a longer response for testing purposes. '.repeat(5);
		}
		return this.fixedResponse;
	}

	/**
	 * 获取用户消息
	 */
	private getUserMessage(messages: ChatCompletionRequest['messages']): string {
		if (!messages || messages.length === 0) return '';
		for (let i = messages.length - 1; i >= 0; i--) {
			const msg = messages[i];
			if (msg.role === 'user') {
				return typeof msg.content === 'string' ? msg.content : '';
			}
		}
		return '';
	}

	async chatCompletions(payload: ChatCompletionRequest): Promise<Response> {
		const model = payload.model || 'test-model';
		const userMessage = this.getUserMessage(payload.messages);
		const responseContent = this.generateResponseContent(userMessage);

		// 模拟延迟（如需）
		if (this.responseDelayMs > 0) {
			await new Promise(resolve => setTimeout(resolve, this.responseDelayMs));
		}

		const now = Math.floor(Date.now() / 1000);
		const data = {
			id: `test-${Date.now()}`,
			object: 'chat.completion',
			created: now,
			model: model,
			choices: [
				{
					index: 0,
					message: {
						role: 'assistant',
						content: responseContent,
					},
					finish_reason: 'stop',
				},
			],
			usage: {
				prompt_tokens: userMessage.split(' ').length * 2,
				completion_tokens: responseContent.split(' ').length,
				total_tokens: userMessage.split(' ').length * 2 + responseContent.split(' ').length,
			},
		};

		return new Response(JSON.stringify(data), {
			headers: { 'Content-Type': 'application/json; charset=utf-8' },
		});
	}

	async chatCompletionsStream(payload: ChatCompletionRequest): Promise<StreamResponse> {
		const model = payload.model || 'test-model';
		const userMessage = this.getUserMessage(payload.messages);
		const responseContent = this.generateResponseContent(userMessage);

		// 分割内容
		const chunks = this.splitContent(responseContent, this.streamChunkCount);

		const encoder = new TextEncoder();
		const stream = new ReadableStream({
			pull: async (controller) => {
				for (let i = 0; i < chunks.length; i++) {
					// 模拟流式延迟（如需）
					if (this.streamChunkDelayMs > 0) {
						await new Promise(resolve => setTimeout(resolve, this.streamChunkDelayMs));
					}

					const now = Math.floor(Date.now() / 1000);
					const data = {
						id: `test-${Date.now()}`,
						object: 'chat.completion.chunk',
						created: now,
						model: model,
						choices: [
							{
								index: 0,
								delta: {
									content: i < chunks.length - 1 ? chunks[i] + ' ' : chunks[i],
								},
								finish_reason: i < chunks.length - 1 ? null : 'stop',
							},
						],
					};

					controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
				}

				controller.enqueue(encoder.encode('data: [DONE]\n\n'));
				controller.close();
			},
		});

		return {
			response: new Response(stream, {
				headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
			}),
			iterator: this.createIterator(stream),
		};
	}

	private async *createIterator(stream: ReadableStream): AsyncIterable<string> {
		const reader = stream.getReader();
		const decoder = new TextDecoder();
		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				const lines = decoder.decode(value).split('\n');
				for (const line of lines) {
					if (!line.trim()) continue;
					yield line;
				}
			}
		} finally {
			reader.releaseLock();
		}
	}

	async listModels(): Promise<{ object: string; data: ModelData[] }> {
		const now = Math.floor(Date.now() / 1000);
		return {
			object: 'list',
			data: [
				{
					id: 'test',
					object: 'model',
					created: now,
					owned_by: 'test-provider',
				},
			],
		};
	}
}
