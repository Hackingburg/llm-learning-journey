"""
Day 6-2: JSON Mode - 强制让 AI 只输出 JSON 格式
目标：用 API 内置的参数解决 AI 不听话的问题，看看效果如何
"""
import os
import json 
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY") 

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY")  

def call_llm_json_mode(prompt: str) -> dict:
    """
    🔑 关键： response_format = {"type": "json_object"}
    这会让 API 在底层强制输出合法 JSON 
    """
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个数据提取助手， 只返回 JSON 格式的结果"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}, # 关键参数
        },
        timeout=30
    )
    response.raise_for_status()

    raw_reply = response.json()["choices"][0]["message"]["content"]
    return json.loads(raw_reply)  # 直接解析成 dict 返回

def extract_ticket_info_safe(user_input: str):
    """安全版本： JSON Mode + 异常处理"""
    prompt = f"""从用户的话里提取订票信息，输出 JSON 格式：
- departure: 出发地
- arrival: 到达地
- date: 出发日期，格式 YYYY-MM-DD
- time: 出发时间，格式 HH:MM
- train_type: 车型(如高铁、普通火车等)

用户的话：{user_input}"""
    
    try: 
        data = call_llm_json_mode(prompt)
        print(f"✅ 解析成功: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ 解析失败: {e}")
        return None
    
if __name__ == "__main__":
    test_inputs = [
        "我要订明天从北京到上海的高铁，下午三点出发",
        "帮我订一张从广州到深圳的火车票，后天早上八点的",
        "我想订一张从杭州到南京的普通火车票，明天下午两点的",
    ]

    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{'=' * 60}")
        print(f"测试用例 {i}: {user_input}")
        print(f"{'=' * 60}")
        extract_ticket_info_safe(user_input)