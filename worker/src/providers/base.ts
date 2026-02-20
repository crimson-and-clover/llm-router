import { ChatCompletionRequest } from '../types';

export interface ModelData {
  id: string;
  object: 'model';
  created: number;
  owned_by: string;
}

export interface StreamResponse {
  response: Response;
  iterator: AsyncIterable<string>;
}

export interface BaseProvider {
  chatCompletions(payload: ChatCompletionRequest): Promise<Response>;
  chatCompletionsStream(payload: ChatCompletionRequest): Promise<StreamResponse>;
  listModels(): Promise<{object: string; data: ModelData[]}>;
}
