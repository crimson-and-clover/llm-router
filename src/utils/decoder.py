import json
from pathlib import Path


class SSEDecoder:
    def __init__(self):
        self.buffer = ""

    def decode(self, chunk: str):
        """
        解析逻辑：
        1. 将新到的 chunk 放入缓冲区
        2. 寻找双换行符 (\n\n)，这是 SSE 标准的消息分隔符
        3. 提取 data: 之后的内容进行 JSON 解析
        """
        self.buffer += chunk

        # SSE 消息通常以 \n\n 结尾
        while "\n\n" in self.buffer:
            message, self.buffer = self.buffer.split("\n\n", 1)

            for line in message.split("\n"):
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue

                # 提取 data: 之后的数据
                data_content = line[len("data: ") :]

                # 检查是否结束
                if data_content == "[DONE]":
                    return

                try:
                    yield json.loads(data_content)
                except json.JSONDecodeError:
                    # 记录错误或忽略不完整的 JSON
                    continue


def run_test():
    # 1. 你提供的原始测试数据（模拟从网络收到的 chunks）
    test_file = Path("logs\\details\\20260202\\22db1126089185d0\\stream.json")
    chunks = json.load(test_file.open("r", encoding="utf-8"))
    # 注意：为了代码简洁，我简化了上面 chunks 里的冗余字段，保留了核心的 delta 结构

    # 2. 初始化解码器
    decoder = SSEDecoder()

    print("--- 开始解析流式数据 ---")

    final_message = {"role": "assistant", "content": "", "tool_calls": []}

    for i, chunk in enumerate(chunks):
        print(f"收到 Chunk {i}...")
        for parsed_json in decoder.decode(chunk):
            choices = parsed_json.get("choices", [])
            if not choices:
                continue

            delta = choices[0].get("delta", {})

            # 1. 还原 Role (通常只在第一包)
            if "role" in delta:
                final_message["role"] = delta["role"]

            # 2. 还原 Content (文本内容拼接)
            if "content" in delta and delta["content"]:
                final_message["content"] += delta["content"]
                # 实时显示（模拟打字机）
                print(delta["content"], end="", flush=True)

            # 3. 还原 Tool Calls (工具调用拼接)
            if "tool_calls" in delta:
                for tc_delta in delta["tool_calls"]:
                    index = tc_delta.get("index")

                    # 如果是新的工具调用，初始化结构
                    if index >= len(final_message["tool_calls"]):
                        final_message["tool_calls"].append(
                            {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        )

                    target_tc = final_message["tool_calls"][index]

                    # 累加 ID
                    if "id" in tc_delta:
                        target_tc["id"] += tc_delta["id"]

                    # 累加函数名
                    if "function" in tc_delta:
                        fn_delta = tc_delta["function"]
                        if "name" in fn_delta:
                            target_tc["function"]["name"] += fn_delta["name"]
                        # 累加参数片段
                        if "arguments" in fn_delta:
                            target_tc["function"]["arguments"] += fn_delta["arguments"]
                            # 只有在 arguments 开始产生时才打印提示
                            if not target_tc["function"]["name"]:
                                print("\n[正在生成工具参数...]")

    print("\n--- 解析完成 ---")
    print(f"完整回复内容: {final_message}")


if __name__ == "__main__":
    run_test()
