"""
Day 3-2: Token 统计与成本计算
目标： 搞清楚每次 API 调用花了多少钱
"""

import os
from dotenv import load_dotenv 
import requests

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

# DeepSeek-Chat 价格（2026 年参考价， 请以官网为准）
# 单位： 元/ 1M tokens
PRICE_INPUT = 2.0  # 输入（你发的内容）
PRICE_OUTPUT= 8.0  # 输出 （AI 回复的内容）


def chat_with_usage(user_message: str):
    """调用 API 并打印 token 使用情况"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": user_message}
            ],
        },
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    # 提取回复
    reply = data["choices"][0]["message"]["content"]

    # 提取 token 使用情况🔑
    usage = data["usage"]
    input_tokens = usage["prompt_tokens"]
    output_tokens = usage["completion_tokens"]
    total_tokens = usage["total_tokens"]

    # 计算成本（元）
    input_cost = input_tokens / 1_000_000 * PRICE_INPUT 
    output_cost = output_tokens / 1_000_000 * PRICE_OUTPUT
    total_cost = input_cost + output_cost

    # 打印 
    print(f"\n💬 用户：{user_message}")
    print(f"🤖 AI 回复：{reply}\n")
    print("=" * 50)
    print("📊 Token 使用情况：")
    print(f"📝 输入 token：{input_tokens}，成本：{input_cost:.6f} 元")
    print(f"📝 输出 token：{output_tokens}，成本：{output_cost:.6f} 元")
    print(f"📝 总 token：{total_tokens}，总成本：{total_cost:.6f} 元")
    print("=" * 50)

    return reply 


if __name__ == "__main__":
    # 测试 1: 短问题
    chat_with_usage("1+1=?")

    # 测试 2: 长问题 
    chat_with_usage("请用 500 字介绍一下大语言模型的发展历程和未来趋势。")
