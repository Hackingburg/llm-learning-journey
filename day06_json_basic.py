"""
Day 6-1: 朴素方法 - 靠 prompt 让 AI 输出 JSON 格式的文本
目标：体验"裸奔"输出 JSON 的感觉，看看它的优缺点
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY")

def call_llm(prompt: str) -> str:
    """普通模式调用，让 AI 自己决定怎么输出"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, # 结构化任务要低温度
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def extract_ticket_info_naive(user_input: str):
    """
    朴素方法：靠 prompt 央求 AI 输出 JSON 格式的文本
    """
    prompt = f"""请从用户的话里提取订票信息，返回 JSON 格式：
{{
"departure": "出发地",
"arrival": "到达地",
"date": "出发日期，格式 YYYY-MM-DD",
"time": "出发时间，格式 HH:MM",
"train_type": "车型"
}}

用户的话：{user_input}

请只返回 JSON, 不要任何解释。"""
    
    raw_reply = call_llm(prompt)
    print(f"\n💬 AI 原始回复：\n{raw_reply}\n")

    # 尝试解析 JSON
    try:
        data = json.loads(raw_reply)
        print(f"✅ 解析成功: {data}")
        return data 
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
        print(f"  AI 回复的文本可能不是纯 JSON, 或者格式有问题。")
        return None 
    
if __name__ == "__main__":
    # 测试 3 种不同的用户输入
    test_inputs = [
        "我想订明天从北京到上海的高铁，下午两点出发。",
        "帮我订一张下周五从广州到深圳的动车票，早上八点的。",
        "我要订票，出发地是成都，到达地是重庆，日期是2024-07-01，时间是10:30，车型是普通列车。"
    ]

    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{'=' * 60}")
        print(f"测试用例 {i}: {user_input}")
        print(f"{'=' * 60}")
        extract_ticket_info_naive(user_input)
        