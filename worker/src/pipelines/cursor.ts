import { BasePipeline, PipelineContext, SSETransformer } from './base';
import { ChatCompletionRequest, ChatMessage } from '../types';

export class CursorPipeline extends BasePipeline {
	private static readonly THINK_BOS = "<think>\n";
	private static readonly THINK_EOS = "\n</think>";

	private extractThinkAndAnswer(text: string): [string | null, string] {
		const { THINK_BOS, THINK_EOS } = CursorPipeline;
		if (text.includes(THINK_BOS) && text.includes(THINK_EOS)) {
			const thinkText = text.split(THINK_BOS)[1].split(THINK_EOS)[0];
			const newText = text.replace(THINK_BOS + thinkText + THINK_EOS, '');
			return [thinkText, newText];
		}
		return [null, text];
	}

	preprocessRequest(ctx: PipelineContext, payload: ChatCompletionRequest): ChatCompletionRequest {
		const newPayload = { ...payload };
		const messages = payload.messages.map((msg) => {
			if (msg.role === 'assistant' && typeof msg.content !== 'string') {
				const content = msg.content?.[0]?.text || '';
				const [thinkText, answerText] = this.extractThinkAndAnswer(content);

				const newMsg: ChatMessage = { ...msg };
				if (thinkText) {
					newMsg.reasoning_content = thinkText;
				}

				if (answerText.length > 0) {
					newMsg.content = [{ type: 'text', text: answerText }];
				} else {
					newMsg.content = [];
				}

				return newMsg;
			}
			return msg;
		});

		newPayload.messages = messages;
		return newPayload;
	}

	postprocessResponse(
		ctx: PipelineContext,
		raw: Record<string, any>
	): Record<string, any> {
		console.log(`[Pipeline] RequestID: ${ctx.requestId} | Postprocess Response`);

		// 处理 reasoning_content：将其包装进 content
		const message = raw.choices?.[0]?.message;
		if (message?.reasoning_content) {
			const reasoning = message.reasoning_content;
			const originalContent = message.content || '';
			// 包装成 <think> 格式
			message.content = `<think>${reasoning}</think>${originalContent}`;
			// 删除 reasoning_content 字段
			delete message.reasoning_content;
		}

		return raw;
	}

	/**
	 * 创建 SSE 数据转换函数（Cursor 专用）
	 * 处理 reasoning_content 转换，支持一次生成多个消息
	 */
	createSSETransformer(ctx: PipelineContext): SSETransformer {
		let reasoningFlag = false;

		return (data: Record<string, any>): Record<string, any>[] => {
			const delta = data.choices?.[0]?.delta;

			// 处理 reasoning_content 转换
			if (delta?.reasoning_content && !reasoningFlag) {
				reasoningFlag = true;
				return [
					{
						...data,
						choices: [{
							index: 0,
							finish_reason: null,
							delta: { content: CursorPipeline.THINK_BOS }
						}],
					},
					{
						...data,
						choices: [{
							...data.choices[0],
							delta: { content: delta.reasoning_content }
						}],
					},
				];
			} else if (delta?.reasoning_content && reasoningFlag) {
				return [
					{
						...data,
						choices: [{
							...data.choices[0],
							delta: { content: delta.reasoning_content }
						}],
					},
				]
			} else if (!delta?.reasoning_content && reasoningFlag) {
				reasoningFlag = false
				return [
					{
						...data,
						choices: [{
							index: 0,
							finish_reason: null,
							delta: { content: CursorPipeline.THINK_EOS }
						}]
					},
					data,
				]
			}

			return [data];
		};
	}
}
