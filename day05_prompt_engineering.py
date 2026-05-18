"""
Day 5: Prompt 工程实战
目标： 通过对比试验，亲眼看到 Prompt 技巧带来的效果差异
"""

import os 
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("❌ 没找到 DEEPSEEK_API_KEY")

def call_llm(messages: list[dict], temperature: float = 0.7) -> str:
    """统一的 API 调用函数 （今天我们专注 prompt 不重复造轮子）"""
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
    return response.json()["choices"][0]["message"]["content"]

def print_section(title: str):
    """打印分隔标题，便于阅读"""
    print("\n" + "=" * 60)
    print(f"📌 {title}")
    print("=" * 60)


# ========== 实验 1: 角色扮演（Role Prompting） ==========
def experiment_1_role():
    """
    对比： 有没有“角色设定”，回答风格差距巨大
    场景： 解释什么是"递归"
    """
    print_section("实验 1: 角色扮演 - 解释「递归」")

    question = "请解释什么是递归"

    # 版本 A: 无角色设定
    print("\n👤 版本 A (无角色):")
    reply_a = call_llm([{"role": "user", "content": question}])
    print(f"🤖 回答:{reply_a}")

    # 版本B: 扮演幼儿园老师
    print("\n👤 版本 B (幼儿园老师):")
    reply_b = call_llm([{"role": "system", "content": "你是一个有耐心的幼儿园老师，善于用简单的语言解释复杂的概念,回答 100 字以内。"},
                        {"role": "user", "content": question}
    ])
    print(f"🤖 回答:{reply_b}")

    # 版本 C: 扮演大学计算机教授
    print("\n👤 版本 C (大学教授):")
    reply_c = call_llm([
        {"role": "system", "content": "你是 MIT 的计算机科学教授，擅长深入浅出地解释复杂的概念,回答 100 字以内。"},
        {"role": "user", "content": question}
    ])
    print(f"🤖 回答:{reply_c}")

    print("\n🔍 观察：版本 A 的回答可能比较笼统，缺乏针对性；版本 B 用了更简单的语言，更适合初学者；版本 C 则可能提供更专业的解释。角色设定直接影响了回答的风格和深度！")


# ========== 实验 2: Few-Shot Learning (少样本学习) ==========
def experiment_2_few_shot():
    """
    对比： 给不给"示例", AI 输出格式差距巨大
    场景： 把用户评论分类为 正面 / 负面 / 中性
    """
    print_section("实验 2: Few-shot - 评论情感分类")

    test_comment = [
        "这家餐厅的菜真的太好吃了，服务也很周到，下次还会再来！",
        "等了半小时才上菜，味道也一般，感觉很失望",
        "菜的味道还行，服务态度不错，但环境有点吵。"
    ]

    # 版本 A： Zero-shot (无示例)
    print("\n👤 版本 A (Zero-shot):")
    for comment in test_comment:
        reply_a = call_llm([
            {"role": "user", "content": f"判断以下评论的情感：{comment}"}
        ])
        print(f"  评论：{comment}")
        print(f" AI: {reply_a}")

    # 版本 B： Few-shot （给 3 个示例）
    print("\n👤 版本 B (Few-shot 给 3 个示例):")
    few_shot_prompt = """请判断以下评论的情感倾向, 只返回一个词：正面 / 负面 / 中性
    
示例：
评论：这个产品超出预期，强烈推荐！
情感：正面
    
评论：质量太差了，浪费钱
情感：负面
    
评论： 还行吧，没什么特别的
情感：中性
    
现在请判断：
评论：{comment}
情感："""
    for comment in test_comment:
        reply_b = call_llm([
            {"role": "user", "content": few_shot_prompt.format(comment=comment)}
        ])
        print(f"  评论：{comment}")
        print(f" AI: {reply_b}")

    print("💡 观察点： Few-shot 让 AI 输出格式严格统一，方便后续程序处理")

# ========== 实验 3: Chain-of-Thought (思维链) ==========
def experiment_3_cot():
    """
    对比： 让不让 AI "一步一步思考", 答数学题准确率天差地别
    场景： 经典逻辑题
    """
    print_section("实验 3: Chain-of-Thought - 经典逻辑题")      

    question = "一个池塘里的荷花，每天数量翻一倍。如果第 30 天荷花覆盖了整个池塘，那么第几天覆盖了半个池塘？"

    # 版本 A: 直接问答案
    print("\n👤 版本 A (直接问答案):")
    reply_a = call_llm([
        {"role": "user", "content": question + "请直接给出答案，不要解释过程。"}
    ], temperature=0.1) # 数学题用低温度更稳定
    print(f"🤖 回答:{reply_a}")

    # 版本 B: Chain-of-Thought (思维链)
    print("\n👤 版本 B (Chain-of-Thought):")
    reply_b = call_llm([
        {"role": "user", "content": question + "请一步一步思考，最后给出答案 。"}
    ], temperature=0.1) # 数学题用低温度更稳定
    print(f"🤖 回答:{reply_b}")

    print("\n🔍 观察：版本 A 可能直接给出错误答案（第 15 天），而版本 B 通过思维链正确推理出答案（第 29 天）。")

# ========== 实验 4: 温度调控 ==========
def experiment_4_temperature():
    """
    对比： 同一个创意任务，不同温度的输出多样性
    场景： 起一个产品名字
    """
    print_section("实验 4: 温度调控 - 起产品名")

    prompt = "为一款主打'年轻人减压'的薄荷糖起 3 个有创意的中文产品名"
    
    for temp in [0.2, 0.7, 1.2]:
        print(f"\n👤 温度: {temp}({['极保守', '平衡', '极发散'][[0.2, 0.7,1.2].index(temp)]}):")
        reply = call_llm([
            {"role": "user", "content": prompt}
        ], temperature=temp)
        print(f"🤖 回答:{reply}")

    print("\n🔍 观察：温度越高，输出越发散和有创意；温度越低，输出越保守和一致。根据需求调整温度，可以得到更符合预期的结果！")
    print("   实战建议： 代码生成用 0-0.3, 对话用 0.7, 创意任务用 0.7-1.2")

# ========== 主函数: 运行所有实验 ==========
if __name__ == "__main__":
    print("🎓 Day 5: Prompt 工程四大法宝实验")
    print("⏳ 总共会调用 12 次 API, 预计花费 0.05元左右，稍等片刻看结果吧！\n")

    experiment_1_role()
    experiment_2_few_shot()
    experiment_3_cot()
    experiment_4_temperature()

    print("\n" + "=" * 60)
    print("✅ 全部实验完成！")
    print("💡 总结：通过这四个实验，我们直观地看到了 Prompt 工程的威力。角色设定、示例引导、思维链和温度调控都是提升 LLM 输出质量的关键技巧。实践中灵活运用这些方法，可以让你事半功倍！")
    print("=" * 60)