"""
Day 1: 第一次调用 DeepSeek API
目标：跑通最基础的单轮对话
"""
import os
from dotenv import load_dotenv
import requests

# 加载 .env 文件中的环境变量
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 安全检查：确保 Key 加载成功
if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY，请检查 .env 文件")


def chat_with_deepseek(user_message: str) -> str:
    """
    调用 DeepSeek API 进行单轮对话
    
    Args:
        user_message: 用户输入的问题
    
    Returns:
        AI 的回答文本
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个友好的 AI 编程导师"},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,  # 0-2，越高越有创造性
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print("🤖 正在调用 DeepSeek...")
    answer = chat_with_deepseek("用一句话告诉我，学大模型应用开发最重要的能力是什么？")
    print("\n💡 AI 回答：")
    print(answer)