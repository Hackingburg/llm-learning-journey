"""
Qwen-VL Hello World — 鉴书灵 AI 第一行代码

目标：跑通"传 1 张图 + 1 句话 → 拿到 AI 回答"。
用途：建立对视觉大模型能力的"手感"。

下月第 1 天，运行这个文件就算正式开始。
"""

import os
import base64
from pathlib import Path

# ⚠️ 下月开始前，需要先安装：
#   pip install dashscope python-dotenv
import dashscope  # type: ignore
from dotenv import load_dotenv  # type: ignore

# 读取 .env 中的 DASHSCOPE_API_KEY
# 在 https://dashscope.console.aliyun.com/ 申请，新用户有免费额度
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


def encode_image_to_base64(image_path: str) -> str:
    """把本地图片转成 base64，给 Qwen-VL 用"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ask_about_image(image_path: str, question: str, model: str = "qwen-vl-plus") -> str:
    """
    给 Qwen-VL 一张图 + 一个问题，拿回答。

    Args:
        image_path: 本地图片路径
        question:   你想问 AI 的问题
        model:      qwen-vl-plus（便宜） or qwen-vl-max（强但贵）

    Returns:
        AI 的文字回答
    """
    image_b64 = encode_image_to_base64(image_path)

    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"data:image/jpeg;base64,{image_b64}"},
                {"text": question},
            ],
        }
    ]

    response = dashscope.MultiModalConversation.call(
        model=model,
        messages=messages,
    )

    if response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        raise RuntimeError(f"Qwen-VL 调用失败：{response.code} - {response.message}")


def main():
    """
    第 1 天的 3 个练习 —— 由浅入深感受视觉 LLM 的能力。
    """
    # ─────────────────────────────────────────────
    # 练习 1：让 AI 描述一张普通照片（验证环境跑通）
    # ─────────────────────────────────────────────
    sample_dir = Path(__file__).parent / "samples"
    sample_dir.mkdir(exist_ok=True)

    test_image = sample_dir / "test.jpg"
    if not test_image.exists():
        print(f"⚠️  请先放一张测试图片到：{test_image}")
        print("   （随便一张图都行：风景、人物、宠物、文件...）")
        return

    print("\n" + "=" * 60)
    print("🌱 练习 1：让 AI 描述一张普通图片")
    print("=" * 60)
    answer = ask_about_image(
        str(test_image),
        "请用中文详细描述这张图片里有什么。"
    )
    print(f"\n🤖 AI 回答：\n{answer}\n")

    # ─────────────────────────────────────────────
    # 练习 2：让 AI 看图书封面（验证文字识别能力）
    # ─────────────────────────────────────────────
    book_cover = sample_dir / "book_cover.jpg"
    if book_cover.exists():
        print("\n" + "=" * 60)
        print("📕 练习 2：让 AI 识别图书封面信息")
        print("=" * 60)
        answer = ask_about_image(
            str(book_cover),
            "这是一本书的封面。请告诉我：1) 书名 2) 作者 3) 出版社 4) 封面有哪些视觉元素。"
        )
        print(f"\n🤖 AI 回答：\n{answer}\n")

    # ─────────────────────────────────────────────
    # 练习 3：让 AI 评估印刷质量（最接近鉴书灵的核心能力）
    # ─────────────────────────────────────────────
    text_closeup = sample_dir / "text_closeup.jpg"
    if text_closeup.exists():
        print("\n" + "=" * 60)
        print("🔍 练习 3：让 AI 评估印刷质量（鉴书灵核心能力的雏形）")
        print("=" * 60)
        answer = ask_about_image(
            str(text_closeup),
            """你是一位专业的印刷质量评估师。这是一张图书内文的局部特写。
请重点观察并描述：
1. 文字边缘是否光滑（有无锯齿/毛刺）
2. 油墨是否均匀（有无晕染/断墨）
3. 字体是否清晰
4. 整体印刷质量评分（1-10 分）

请用中文回答，结构化输出。"""
        )
        print(f"\n🤖 AI 回答：\n{answer}\n")

    print("\n" + "=" * 60)
    print("✅ Hello World 完成！现在你已经感受过视觉 LLM 的能力了。")
    print("📌 下一步：用真实的图书正版/盗版对照图，跑 jianshu_prompt_v1.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
