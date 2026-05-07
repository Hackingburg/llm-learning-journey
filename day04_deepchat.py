"""
Day 4: DeepChat - 产品级命令行 AI 助手
整合所学内容： 流式输出 + 多轮记忆 + 滑动窗口 + 陈本追踪 + 会话持久化
"""
import os 
import json
import requests
from dotenv import load_dotenv 
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import BaseModel

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK——API——KEY")

# ===== 配置 =====
class Config:
    """集中管理配置， 方便后续调整"""
    MODEL = "deepseek-chat"
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    TEMPERATURE = 0.7 

    # 滑动窗口： 最多保留多少轮对话 （1 轮 = user + assitant 两条消息）
    MAX_HISTORY_TURNS = 10

    # 价格（元 / 1M tokens）
    PRICE_INPUT = 2.0
    PRICE_OUTPUT = 8.0

    # 会话保存目录
    SESSIONS_DIR = Path("sessions")

# ===== 数据模型 =====
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str 

# ===== DeepChat 主类 =====
class DeepChat:
    def __init__(self, system_prompt: str = "你是一个友好，简洁的 AI 助手"):
        self.system_message = Message(role="system", content=system_prompt)
        self.history: list[Message] = [] # 不含 system, 方便管理

        # 成本累计
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.turn_count = 0

        # 确保会话目录存在
        Config.SESSIONS_DIR.mkdir(exist_ok=True)

    # ----- 核心： 发送消息 -----
    def chat(self, user_input: str) -> str:
        """流式发送消息， 返回完整回复"""
        self.history.append(Message(role="user", content=user_input))

        # 滑动窗口： 截断历史
        self._apply_sliding_window()

        # 构造完整 messages （system + 截断后的历史）
        messages = [self.system_message] + self.history

        payload = {
            "model": Config.MODEL,
            "messages": [m.model_dump() for m in messages],
            "temperature": Config.TEMPERATURE,
            "stream": True,
            "stream_options": {"include_usage": True}, # 🔑 流式也能拿到usage

        }

        response = requests.post(
            Config.API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            stream=True,
            timeout=60
        )
        if not response.ok:
           print(f"\n❌ API 返回错误 {response.status_code}:")
           print(response.text)
           response.raise_for_status()

        # 解析流式响应
        full_reply = ""
        usage = None 

        print("🤖 ", end="", flush=True)
        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if not line_str.startswith("data: "):
                continue 
            data_str = line_str[6:]
            if data_str == "[DONE]":
                break

            try:
                chunk = json.loads(data_str)

                # 提取增量内容
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        print(content, end="", flush=True)
                        full_reply += content
            
                # 提取 usage （流式响应里 usage 在最后一个块）
                if chunk.get("usage"):
                    usage = chunk["usage"]
            except json.JSONDecodeError: 
                continue

        print() # 换行

        # 更新历史
        self.history.append(Message(role="assistant", content=full_reply))
        self.turn_count += 1

        # 更新成本 
        if usage:
            self._update_cost(usage)

        return full_reply
    
    # ----- 滑动窗口管理 -----
    def _apply_sliding_window(self):
        """只保留最近 N 轮对话 (1 轮 = 2条消息)"""
        max_messages= Config.MAX_HISTORY_TURNS*2
        if len(self.history) > max_messages:
            removed = len(self.history) - max_messages 
            self.history = self.history[-max_messages:]
            print(f" ℹ️历史已截断， 移除最早{removed} 条消息")

    # ----- 成本计算 -----
    def _update_cost(self, usage:dict):
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        cost = (input_tokens/ 1_000_000 * Config.PRICE_INPUT + output_tokens / 1_000_000 * Config.PRICE_OUTPUT)

        self.total_input_tokens += input_tokens 
        self.total_output_tokens += output_tokens 
        self.total_cost += cost 

        print(f" 💰 本轮成本: {cost:.6f} 元 (输入 {input_tokens} tokens, 输出 {output_tokens} tokens)")
   
    # ----- 工具命令 -----
    def reset(self):
        self.history = []
        print("🔄 会话已重置(成本统计保留)")

    def show_history(self):
        print("\n📜 会话历史 (共 {len(self.history)} 条， {self.turn_count}轮):") 
        for i, msg in enumerate(self.history):
            preview = msg.content[:60].replace("\n", " ")
            print(f" [{i}] {msg.role}: {preview}...")

    def show_stats(self):
        print(f"\n📊 会话统计:")
        print(f" 总输入 tokens: {self.total_input_tokens}")
        print(f" 总输出 tokens: {self.total_output_tokens}")
        print(f" 累计成本: {self.total_cost:.6f} 元")
        print(f" 总轮数: {self.turn_count}")

    # ----- 会话持久化 -----
    def save(self, name: str = None):
        """"保留当前会话到 JSON 文件"""
        if not name:
            name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        filepath = Config.SESSIONS_DIR / f"{name}.json"
        
        data = {
            "saved_at": datetime.now().isoformat(),
            "system_prompt": self.system_message.content,
            "history": [m.model_dump() for m in self.history],
            "stats": {
                "turn_count": self.turn_count,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_cost": self.total_cost,
            }
        }
        
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"💾 会话已保存到 {filepath}")

    def load(self, name: str):
        """从 JSON 文件加载会话"""
        filepath = Config.SESSIONS_DIR / f"{name}.json"
        if not filepath.exists():
            print(f"❌ 没找到会话文件: {filepath}")
            return
        
        data = json.loads(filepath.read_text(encoding="utf-8"))
        self.system_message = Message(role="system", content=data["system_prompt"])
        self.history = [Message(**m) for m in data["history"]]
        stats = data.get("stats", {})
        self.turn_count = stats.get("turn_count", 0)
        self.total_input_tokens = stats.get("total_input_tokens", 0)
        self.total_output_tokens = stats.get("total_output_tokens", 0)
        self.total_cost = stats.get("total_cost", 0.0)  
        print(f"✅ 已加载会话: {name} ({self.turn_count} 轮对话)")


# ===== 命令行交互 ===== 
HELP_TEXT= """
📖 可用命令：
    /help - 显示帮助
    /history - 显示会话历史
    /stats - 显示会话统计
    /reset - 重置会话历史
    /save [name] - 保存当前会话 (可选 name)
    /load [name] - 加载指定会话
    /exit - 退出程序
    """

def main():
    print("=" * 60)
    print("🤖DeepChat - 产品级 AI 助手（Day 4 作品）")
    print("=" * 60)
    print(HELP_TEXT)

    bot = DeepChat(system_prompt="你是一个简洁有趣的 AI 助手，回答控制在 150 字内")

    while True:
        try:
            user_input = input("\n👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue

        #处理命令
        if user_input.startswith("/"):
            parts = user_input[1:].split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            if cmd == "exit":
                print("👋 再见！")
                break
            elif cmd == "help":
                print(HELP_TEXT)
            elif cmd == "history":
                bot.show_history()
            elif cmd == "stats":
                bot.show_stats()
            elif cmd == "reset":
                bot.reset()
            elif cmd == "save":
                bot.save(name=arg)
            elif cmd == "load":
                if arg:
                    bot.load(name=arg)
                else:
                    print("❌ 请提供要加载的会话名称")
            else:
                print(f"❌ 未知命令: {cmd}, 输入 /help 查看可用命令")
            continue

        #普通对话
        try:
            bot.chat(user_input)
        except Exception as e:
            print(f"❌ 出错了: {e}")

if __name__ == "__main__":
    main()
