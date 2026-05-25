"""
Day 13-2: 多工具 + 工具循环
🎯 让 AI 自主使用多个工具，自主决定调用次数
"""
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY") 


# ===== 工具集 =====
def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_weather(city: str) -> dict:
    """模拟天气查询（实际可接真实 API）"""
    fake_weather_db = {
        "北京": {"温度": "5°C", "天气": "晴", "风力": "3级"},
        "上海": {"温度": "10°C", "天气": "多云", "风力": "2级"},
        "广州": {"温度": "20°C", "天气": "雨", "风力": "4级"},          
        "成都": {"温度": "8°C", "天气": "阴", "风力": "3级"},
    }
    return fake_weather_db.get(city, {"error": f"没有 {city} 的天气数据"})


def calculator(expression: str) -> str:
    """安全计算器"""
    try:
        # 注意：实际生产要更严格的安全控制，eval 有风险
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "错误：表达式包含非法字符"
        return str(eval(expression))
    except Exception as e:
        return f"计算错误: {e}"
    

# ===== 工具映射 + Schema =====
available_tools = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "calculator": calculator,
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如 北京"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算一个数学表达式，支持 + - * / ( )",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": '数学表达式，如 "(1+2)*3"'}
                },
                "required": ["expression"],
            },
        },
    },       
]


def call_llm(messages: list[dict]) -> dict:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "tools": tools_schema,
            "tool_choice": "auto",
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def execute_tool(tool_call: dict) -> str:
    """执行单个工具调用"""
    function_name = tool_call["function"]["name"]
    function_args = json.loads(tool_call["function"]["arguments"])

    print(f" 🔧 调用：{function_name}，参数：{function_args}")

    if function_name in available_tools:
        result = available_tools[function_name](**function_args)
        print(f" ✅ 工具结果：{result}")
        return str(result)
    return f"错误：未知工具 {function_name}"


def chat_with_loops(user_message: str, max_iterations: int = 5) -> str:
    """
    🔑 关键升级：循环调用，直到AI 不再需要工具
    max_iterations 防止死循环
    """
    messages = [
        {"role": "system", "content": "你是一个能调用工具的助手"},
        {"role": "user", "content": user_message},
    ]
    
    print(f"\n💬 用户：{user_message}")
    
    for i in range(max_iterations):
        response = call_llm(messages)
        assistant_msg = response["choices"][0]["message"]
        tool_calls = assistant_msg.get("tool_calls")

        # 没有工具调用 ➡️ 完成
        if not tool_calls:
            print(f"🤖 最终回答：{assistant_msg['content']}\n")
            return assistant_msg["content"]
        
        # 执行所有工具调用
        print(f"🔁 第 {i+1} 轮：AI 要调用 {len(tool_calls)} 个工具")
        messages.append(assistant_msg)  # 把 AI 的请求加入历史

        for tool_call in tool_calls:
            tool_result = execute_tool(tool_call)
            # 将工具结果反馈给 LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result,
            })
    
    return "⚠️ 达到最大迭代次数。"


# ===== 实战测试 =====
if __name__ == "__main__":
    test_cases = [
        # 单工具
        "现在几点了？",

        # 单工具不同参数
        "帮我查一下上海的天气。",

        # 多工具：同一类型
        "北京和上海哪个地方现在更热？",

        # 多工具：不同类型
        "现在是什么时候？ 北京气温多少？ 帮我算一下 (1+2)*3 的结果。",

        # 数据缺失：AI 应该如实告知
        "帮我查一下纽约的天气。",

        # 推理 + 工具
        "如果我要去广州，需要带伞么？"
    ]

    for q in test_cases:
        chat_with_loops(q)
        print("=" * 60)