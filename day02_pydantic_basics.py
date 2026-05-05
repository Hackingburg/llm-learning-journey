"""
Day 2-1: Pydantic 基础
目标：理解为什么要用数据模型代替字典
"""
from pydantic import BaseModel, Field
from typing import Literal


# ===== 对比： 字典 VS pydantic =====

# ❌ 老办法：字典（容易出错，没有提示）
message_dict = {
    "role": "user",
    "content": "你好"
}
# 问题：拼错 “rolo” 不会报错，content 写成数字也不会报错


# ✅  新办法：Pydantic 模型（自动校验，IDE 补全）
class Message(BaseModel):
    """一条聊天消息"""
    role: Literal["system", "user", "assistant"] # 只能这三个值
    content: str # 必须是字符串

class ChatRequest(BaseModel):
    """发给llm的请求体"""
    model: str = "DeepSeek-Chat" #默认值
    messages: list [Message]
    temprature: float = Field(default=0.7, ge=0, le=2) # 限制范围 0-2

# ===== 实战演示 =====
if __name__ == "__main__":

    # 1. 创建消息
    msg = Message(role="user", content="你好")
    print("✅ 创建消息成功：", msg)
    print("  转成字典: ", msg.model_dump())

    # 2. 自动校验: role 写错会立刻报错
    try: 
        bad_msg = Message(role="hacker", content="你好")
    except Exception as e:
        print("\n❌ 校验失败（这是好事，提前发现错误）： ")
        print(f"  {e}")

    # 3. 创建完整请求 
    request = ChatRequest(
        messages = [
            Message(role="system", content="你是一个友好的 AI 编程导师"),
            Message(role="user", content="1+1=?")

        ],
        temprature=0.5
    )

    print("\n✅ 请求体：")
    print(request.model_dump_json(indent=2))
    