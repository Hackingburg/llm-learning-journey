"""
Day 15-2: DeepSeek 流式调用
🎯 让 LLM 边生成边返回，体验"打字机效果"
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")


def stream_chat(question: str):
    """🔑 关键：stream=True + 用 iter_lines 逐行读"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": question}],
            "stream": True,  # ⭐ 关键开关
        },
        stream=True,  # ⭐ requests 也要开
        timeout=30
    )
    
    print(f"💬 用户：{question}")
    print("🤖 AI: ", end="", flush=True)
    
    # 🔑 逐行读取，每行是一个 SSE event
    for line in response.iter_lines():
        if not line:
            continue
        
        line = line.decode("utf-8")
        if not line.startswith("data: "):
            continue
        
        data_str = line[6:]  # 去掉 "data: " 前缀
        
        # DeepSeek 用 [DONE] 标记结束
        if data_str == "[DONE]":
            break
        
        try:
            data = json.loads(data_str)
            delta = data["choices"][0]["delta"]
            
            # ⭐ delta 是"增量"——只包含本次新生成的字
            content = delta.get("content", "")
            if content:
                print(content, end="", flush=True)
        except json.JSONDecodeError:
            continue
    
    print()  # 结束换行


if __name__ == "__main__":
    stream_chat("用一句话介绍你自己")
    print("-" * 60)
    stream_chat("写一首关于程序员的短诗")