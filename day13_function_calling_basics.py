"""
Day 13-1: Function Calling 入门
🎯 让 AI 主动调用一个"获取当前时间"的工具
"""
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 1. 定义工具（普通 Python 函数）=====
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """
    🔑 这是一个普通函数，跟 AI 无关
    AI 不会真的执行它，AI 只会"建议"调用它
    """
    # 简化版：忽略 timezone，直接返回当前时间
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ===== 2. 用 JSON Schema 描述工具（这是 AI 能看懂的格式）=====
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区，如 Asia/Shanghai。默认上海时间",
                    }
                },
                "required": [],
            },
        },
    }
]

# 工具名 → 实际函数的映射
available_tools = {
    "get_current_time": get_current_time,
}


# ===== 3. 调用 LLM 时带上 tools =====
def call_llm_with_tools(messages: list[dict]) -> dict:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "tools": tools_schema,  # ⭐ 关键
            "tool_choice": "auto",  # 让模型自己决定要不要调
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()


# ===== 4. 完整流程 =====
def chat_with_tools(user_message: str) -> str:
    """完整的 Function Calling 流程"""
    messages = [
        {"role": "system", "content": "你是一个能调用工具的助手"},
        {"role": "user", "content": user_message},
    ]
    
    print(f"\n💬 用户：{user_message}")
    
    # === 第 1 次调用：LLM 决定要不要用工具 ===
    response = call_llm_with_tools(messages)
    assistant_msg = response["choices"][0]["message"]
    
    # 🔑 检查 LLM 是否要求调工具
    tool_calls = assistant_msg.get("tool_calls")
    
    if not tool_calls:
        # LLM 觉得不需要工具，直接答
        print(f"🤖 AI（无工具）：{assistant_msg['content']}")
        return assistant_msg["content"]
    
    # === LLM 要求调工具 ===
    print(f"🔧 AI 决定调用工具：")
    
    # 把 LLM 的"工具调用请求"加入历史
    messages.append(assistant_msg)
    
    # 执行每个工具调用
    for tool_call in tool_calls:
        func_name = tool_call["function"]["name"]
        func_args = json.loads(tool_call["function"]["arguments"])
        
        print(f"   → {func_name}({func_args})")
        
        # 真正执行函数
        if func_name in available_tools:
            result = available_tools[func_name](**func_args)
        else:
            result = f"未知工具: {func_name}"
        
        print(f"   ← 返回: {result}")
        
        # 🔑 把结果作为 role="tool" 加入历史
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(result),
        })
    
    # === 第 2 次调用：带着工具结果让 LLM 生成最终回答 ===
    response = call_llm_with_tools(messages)
    final_reply = response["choices"][0]["message"]["content"]
    print(f"🤖 AI（带工具结果）：{final_reply}")
    return final_reply


# ===== 实战测试 =====
if __name__ == "__main__":
    # 应该触发工具调用
    chat_with_tools("现在几点了？")
    print("-" * 60)
    
    # 不应该触发工具
    chat_with_tools("你好，介绍一下自己")
    print("-" * 60)
    
    # 边界测试：用户用英文问
    chat_with_tools("What time is it now?")