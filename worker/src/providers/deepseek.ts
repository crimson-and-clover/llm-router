import { BaseProvider, ModelData, StreamResponse } from './base';
import type { ChatCompletionRequest, Env } from '../types';

export class DeepSeekProvider implements BaseProvider {
	constructor(private env: Env) { }

	private getHeaders(): Record<string, string> {
		return {
			'Authorization': `Bearer ${this.env.DEEPSEEK_API_KEY}`,
			'Accept': 'application/json; charset=utf-8',
			'Content-Type': 'application/json; charset=utf-8',
		};
	}

	private preprocessPayload(payload: ChatCompletionRequest): ChatCompletionRequest {
		const newPayload = { ...payload };
		const messages = payload.messages.map(msg => {
			if (msg.role === 'tool' && typeof msg.content !== 'string') {
				const textParts: string[] = [];
				for (const item of msg.content || []) {
					if (typeof item === 'string') {
						textParts.push(item);
					} else if (item.type === 'text') {
						textParts.push(item.text || '');
					} else if (item.type === 'image_url') {
						textParts.push(`\n[Attached Image: ${item.image_url?.url}]\n`);
					} else {
						textParts.push(`\n[Unsupported Multimodal Block: ${item.type}]\n`);
					}
				}
				return { ...msg, content: textParts.join('') };
			}
			return msg;
		});
		newPayload.messages = messages;
		return newPayload;
	}

	async chatCompletions(payload: ChatCompletionRequest): Promise<Response> {
		const processedPayload = this.preprocessPayload(payload);
		return fetch(`${this.env.DEEPSEEK_BASE_URL}/chat/completions`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify(processedPayload),
		});
	}

	async chatCompletionsStream(payload: ChatCompletionRequest): Promise<StreamResponse> {
		const processedPayload = { ...this.preprocessPayload(payload), stream: true };
		const response = await fetch(`${this.env.DEEPSEEK_BASE_URL}/chat/completions`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify(processedPayload),
		});

		// 返回响应和迭代器，让调用者检查状态
		const iterator = this.createIterator(response);
		return { response, iterator };
	}

	private async *createIterator(response: Response): AsyncIterable<string> {
		if (!response.ok) {
			const text = await response.text();
			throw new Error(`DeepSeek API Error: ${response.status} ${text}`);
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
		const response = await fetch(`${this.env.DEEPSEEK_BASE_URL}/models`, {
			headers: this.getHeaders(),
		});
		return response.json();
	}
}
