import { BaseProvider, ModelData, StreamResponse } from './base';
import type { ChatCompletionRequest, Env } from '../types';

export class ZaiProvider implements BaseProvider {
	constructor(private env: Env) { }

	private getHeaders(): Record<string, string> {
		return {
			'Authorization': `Bearer ${this.env.ZAI_API_KEY}`,
			'Accept': 'application/json; charset=utf-8',
			'Content-Type': 'application/json; charset=utf-8',
		};
	}

	async chatCompletions(payload: ChatCompletionRequest): Promise<Response> {
		return fetch(`${this.env.ZAI_BASE_URL}/chat/completions`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify(payload),
		});
	}

	async chatCompletionsStream(payload: ChatCompletionRequest): Promise<StreamResponse> {
		const streamPayload = { ...payload, stream: true };
		const response = await fetch(`${this.env.ZAI_BASE_URL}/chat/completions`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify(streamPayload),
		});

		// 返回响应和迭代器，让调用者检查状态
		const iterator = this.createIterator(response);
		return { response, iterator };
	}

	private async *createIterator(response: Response): AsyncIterable<string> {
		if (!response.ok) {
			const text = await response.text();
			throw new Error(`Zai API Error: ${response.status} ${text}`);
		}

		const reader = response.body?.getReader();
		if (!reader) throw new Error('No response body');

		const decoder = new TextDecoder();
		let buffer = '';

		while (true) {
			const { done, value } = await reader.read();
			if (done) {
				// Flush decoder to get remaining bytes
				const remaining = decoder.decode();
				if (remaining) {
					buffer += remaining;
				}
				break;
			}

			buffer += decoder.decode(value, { stream: true });

			// 处理所有类型的换行符 (\r\n, \n, \r)
			const lines = buffer.split(/\r?\n/);
			buffer = lines.pop() || '';

			for (const line of lines) {
				if (!line.trim()) continue;
				yield line;
			}
		}

		// 处理流结束后的剩余数据
		if (buffer.trim()) {
			yield buffer.trim();
		}
	}

	async listModels(): Promise<{ object: string; data: ModelData[] }> {
		const response = await fetch(`${this.env.ZAI_BASE_URL}/models`, {
			headers: this.getHeaders(),
		});
		return response.json();
	}
}
