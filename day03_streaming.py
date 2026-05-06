"""

Day 3-1: 流式输出
目标： 让 AI 像打字机一样实时输出，体验感大幅提升
"""

import os 
import json
import requests
from dotenv import load_dotenv 

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY，请检查环境变量设置")

def chat_streaming(user_message: str) -> str:
    """
    流式调用 DeepSeek API
    返回完整回复，但过程中实时打印
    """
    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个友好的 AI 助手"},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "stream": True, # 🔑 关键：开启流式
    }

    # stream=True 让 requests 不要一次性下载完整相应
    response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
    response.raise_for_status()

    full_reply = "" # 积累完整回复

    # 逐行读取流式数据 
    for line in response.iter_lines():
        if not line:
            continue

        # SSE 格式： 每行以“data：” 开头
        line_str = line.decode("utf-8")
        if not line_str.startswith("data: "):
            continue 

        # 去掉“data： ”前缀
        data_str = line_str[6:]

        # 流结束标志
        if data_str == "[DONE]":
            break

        # 解析 JSON 数据块
        try:
            chunk = json.loads(data_str)
            # delta 里是本次推送的增量内容
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")

            if content:
                # 实时打印（end=““ 不换行， flush=True 立刻显示）
                print(content, end="", flush=True)
                full_reply += content
        except json.JSONDecodeError:
            continue
    print() # 最后换航
    return full_reply

if __name__ == "__main__":
    print("🤖 AI 正在思考")
    print("-" * 50)

    reply = chat_streaming("用 200 字介绍一下 Python 这门编程语言的发展史")
    print("-" * 50)
    print(f"\n📊 总字数：{len(reply)}字")

