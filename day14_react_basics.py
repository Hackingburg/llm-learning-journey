"""
Day 14-1: ReAct 模式入门
🎯 让 AI 显示输出"思考过程",而不只是答案
"""
import os 
import re
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 工具集（沿用 Day 13）=====
def get_weather(city: str) -> dict:
    fake_db = {
        "北京": "晴，5°C",
        "上海": "多云，10°C",
        "广州": "雨，20°C",
        "成都": "阴，8°C",
    }
    return fake_db.get(city, f"没有 {city} 的天气数据")


def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "错误：表达式包含非法字符"
        return str(eval(expression))
    except Exception as e:
        return f"计算错误: {e}"


available_tools = {
    "get_weather": get_weather,
    "calculator": calculator,
}


# ===== ReAct 的核心是 Prompt =====
REACT_PROMPT = """你是一个会思考的 AI 助手，按以下格式回答：

Thought: 我需要思考什么
Action: 工具名[参数]
Observation: 工具返回的结果（这一行有系统填，你不要谢）
... 可以重复 Thought/Action/Observation 多次...
Thought: 我已经有足够信息了
Final Answer: 最终给用户的答案

可用工具:
- get_weather[城市名]: 查询某城市天气
- calculator[表达式]: 数学计算

⚠️ 严格按格式输出，每次只输出到 Action 那行就停下，等等 Observation。

用户问题: {question}
"""


def call_llm(messages: list[dict], stop: list[str] = None) -> str:
    """调用 LLM，可以设置 stop 词让它在特定地方停下"""
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.1,  # 🔑 低温度让格式更稳
    }
    if stop:
        payload["stop"] = stop

    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_action(text: str) -> tuple[str, str] | None:
    """从文本里解析出 Action: tool_name[args]"""
    match = re.search(r"Action:\s*(\w+)\[(.+?)\]", text)
    if match:
        return match.group(1), match.group(2)
    return None 


def run_react(question: str, max_steps: int = 5) -> str:
    """🔑 ReAct 主循环"""
    print(f"\n💬 用户问题: {question}")
    print("=" * 60)

    # 初始化 Prompt 
    prompt = REACT_PROMPT.format(question=question)
    messages = [{"role": "user", "content": prompt}]

    full_trace = "" # 完整推理痕迹

    for step in range(max_steps):
        # 让 LLM 输出，遇到 "Observation:" 就停(避免它自己脑补结果)
        response = call_llm(messages, stop=["Observation:"])

        print(response, end="")
        full_trace += response

        # 如果它输出了 Final Answer，结束
        if "Final Answer:" in response:
            print() # 换行
            print("=" * 60)
            return response.split("Final Answer:")[-1].strip()
        
        # 解析 Action
        action = parse_action(response)
        if not action:
            print("\n 没有解析到 Action，停止")
            return "解析失败"
        
        tool_name, tool_arg = action

        # 执行工具
        if tool_name in available_tools:
            result = available_tools[tool_name](tool_arg.strip())
        else:
            result = f"错误：未知工具 {tool_name}" 

        # 把 Observation 加进对话，让 AI 继续
        observation_text = f"Observation: {result}\n"
        print(observation_text, end="")
        full_trace += observation_text

        # 🔑 把"原 prompt + AI 推理 + 系统观察"作为下一轮的输入
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": full_trace},
        ]

    return "达到最大步数"


# ===== 实战 =====
if __name__ == "__main__":
    test_questions = [
        "现在上海的天气怎么样？",
        "北京和上海的温差是多少？", # 需要查 2 次 + 计算
        "广州的温度乘以 3 是多少？", # 查询 + 计算
    ]

    for q in test_questions:
        run_react(q)
        print("\n" + "🔚" * 30 + "\n")
 