"""
Day 14-2: ReAct + Function Calling
🎯 工业级 ReAct：结构化工具调用 + 显式思考过程
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 工具集 =====
def get_weather(city: str) -> dict:
    fake_db = {
        "北京": {"温度": 5, "天气": "晴"},
        "上海": {"温度": 10, "天气": "多云"},
        "广州": {"温度": 20, "天气": "雨"},
        "成都": {"温度": 8, "天气": "阴"},
    }
    return fake_db.get(city, {"error": f"没有 {city} 的数据"})


def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "错误：非法字符"
        return str(eval(expression))
    except Exception as e:
        return f"错误: {e}"


def get_calendar(date: str) -> list:
    """模拟日历查询"""
    fake_calendar = {
        "today": [
            {"time": "14:00-15:00", "event": "和团队开周会", "location": "公司会议室"},
            {"time": "19:30-21:00", "event": "晚上学习 LLM", "location": "家"},
        ],
        "tomorrow": [
            {"time": "10:00-12:00", "event": "客户演示", "location": "客户公司"},
        ],
    }
    return fake_calendar.get(date, [])


available_tools = {
    "get_weather": get_weather,
    "calculator": calculator,
    "get_calendar": get_calendar,
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某城市的天气和温度",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar",
            "description": "查询某天的日程安排",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，'today' 或 'tomorrow'",
                    }
                },
                "required": ["date"],
            },
        },
    },
]


# 🔑 ReAct 关键：System Prompt 引导 AI 显式思考
REACT_SYSTEM_PROMPT = """你是一个会主动思考的 AI 助手（ReAct 模式）。

工作流程：
1. 收到用户问题，先在 content 里写下你的"思考"（用"💭 思考："开头）
2. 思考完后，决定要调用哪些工具
3. 看到工具结果后，继续思考"还需要什么信息"
4. 信息够了，给出最终答案（用"✅ 答案："开头）

⚠️ 即使你认为问题简单，也要至少写一句思考，让用户看到你的判断逻辑。
⚠️ 不要编造数据，所有事实都要通过工具获取。
"""


def call_llm(messages: list[dict]) -> dict:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "tools": tools_schema,
            "tool_choice": "auto",
            "temperature": 0.3,
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def run_react_agent(question: str, max_steps: int = 6) -> str:
    """ReAct + Function Calling 主循环"""
    print(f"\n💬 用户：{question}")
    print("=" * 60)
    
    messages = [
        {"role": "system", "content": REACT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    for step in range(max_steps):
        response = call_llm(messages)
        msg = response["choices"][0]["message"]
        
        # 🔑 关键：先打印 AI 的思考（content 部分）
        if msg.get("content"):
            print(f"\n【Step {step+1}】{msg['content']}")
        
        tool_calls = msg.get("tool_calls")
        
        # 没有工具调用 = 完成
        if not tool_calls:
            print("=" * 60)
            return msg.get("content", "")
        
        messages.append(msg)
        
        # 执行工具
        for tc in tool_calls:
            fn = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            
            print(f"   🔧 调用 {fn}({args})")
            
            if fn in available_tools:
                result = available_tools[fn](**args)
            else:
                result = f"未知工具 {fn}"
            
            print(f"   📊 结果：{result}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })
    
    return "⚠️ 达到最大步数"


# ===== 实战 =====
if __name__ == "__main__":
    test_cases = [
        # 简单题
        "北京今天冷吗？",
        
        # 多步推理：查日程 + 查天气 + 综合建议
        "我今天有什么安排？根据我的日程和北京天气，给穿衣建议",
    ]
    
    for q in test_cases:
        run_react_agent(q)
        print("\n" + "🔚" * 30)