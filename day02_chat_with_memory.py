"""
Day 2-2: 带记忆的多轮对话
目标： 构建一个能够记住上下文的命令行 ChatBot
"""
import os
import requests
from dotenv import load_dotenv
from typing import Literal
from pydantic import BaseModel

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY，请检查 .env 文件")

# ===== 数据模型 =====
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str 

# ===== ChatBot 核心类 =====
class ChatBot:
    """
    一个有记忆的对话机器人   
    核心思路： 维护一个messages 列表，每次对话都带上历史
    """
    def __init__(self, system_prompt: str = "你是一个友好的 AI 助手"):
        self.history: list[Message] = [Message(role="system", content=system_prompt)]
        self.url = "https://api.deepseek.com/v1/chat/completions"
    def chat(self, user_input: str) -> str:
        """发送一条消息，并把对话加入历史""" 
        # 1. 把用户的话加入历史
        self.history.append(Message(role="user", content=user_input))

        # 2. 调用 API（注意：把整个历史都发过去）
        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                # 把 Pydantic 模型转成字典列表
                "messages": [msg.model_dump() for msg in self.history],
                "temperature": 0.7,
            },
            timeout=30 # 加上超时，避免卡死
        )
        response.raise_for_status()

        # 3. 提取 AI 回复
        ai_reply = response.json()["choices"][0]["message"]["content"]

        # 4. 把 AI 的回复也加入历史（关键！，下次对话才能“记得”）
        self.history.append(Message(role="assistant", content=ai_reply))
        return ai_reply
    def reset(self):
        """重制对话， 只保留系统提示"""
        self.history = self.history[:1]
        print("🔄 对话已重置！")

    def show_history(self):
        """查看历史消息（条使用）"""
        print(f"\n📜 当前对话历史（共 {len(self.history)} 条）:")
        for i, msg in enumerate(self.history):
            print(f" [{i}] {msg.role}: {msg.content[:50]}...")
    
# ===== 命令行交互 =====
def main():
    print("=" * 50)
    print("🤖 DeepSeek ChatBot （输入 'exit' 推出， 'reset' 重置， 'history' 看历史）")
    print("=" * 50)

    bot = ChatBot(system_prompt="你是一个简洁有趣的AI助手， 回答控制在100字内")

    while True:
        user_input = input("\n👤 你说: ").strip()

        if not user_input:
            continue 
        if user_input.lower() == "exit":
            print("👋 再见！")
            break
        elif user_input.lower() == "reset":
            bot.reset()
            continue
        elif user_input.lower() == "history":
            bot.show_history()
            continue
        
        try:
            reply = bot.chat(user_input)
            print(f"\n🤖 AI 回答: {reply}")
        except Exception as e:
            print(f"❌ 出错了: {e}")

if __name__ == "__main__":
    main()
