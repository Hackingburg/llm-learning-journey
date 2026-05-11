import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY")

def call_llm(messages: list[dict], temperature: float = 0.7) -> str:
    """统一的 API 调用函数 """
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def experiment_role():
    """角色扮演实验"""
    print("\n" + "=" * 60)
    print("📌 实验: 不同角色对同一个问题的回答 ")
    print("=" * 60)

    question = "减脂最快且不伤身体的科学方法是什么？"
    print(f"\n❓ 问题: {question}")
    # 版本 A: 扮演健身教练
    print("\n👤 版本 A (健身教练):")
    reply_a = call_llm([{"role": "system", "content": "你是一个专业的健身教练，擅长科学减脂方法。回答100字以内。"},
                        {"role": "user", "content": question}
    ])
    print(f"🤖 回答:{reply_a['choices'][0]['message']['content']}")
    print("\n" + f"本次回答共使用了 {reply_a['usage']['total_tokens']} 个 token")

    # 版本B: 扮演营养师
    print("\n👤 版本 B (营养师):")
    reply_b = call_llm([{"role": "system", "content": "你是一个专业的营养师，擅长科学饮食和减脂方法。回答100字以内。"},
                        {"role": "user", "content": question}
    ])
    print(f"🤖 回答:{reply_b['choices'][0]['message']['content']}")
    print("\n" + f"本次回答共使用了 {reply_b['usage']['total_tokens']} 个 token")

if __name__ == "__main__":
    experiment_role()