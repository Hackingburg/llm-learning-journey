"""
Day 6-3: Pydantic + JSON Mode = 工业级结构化输出
目标：让 AI 输出严格符合呀污规范的 JSON，不符合就报错
"""
import os
import json
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, Field 
from datetime import date, time 
from typing import Literal, Optional

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY") 

# ===== 业务数据模型（这就是“数据契约”） =====
class TicketRequest(BaseModel):
    """订票请求 - 严格定义业务字段"""
    departure: str = Field(description="出发城市")
    arrival: str = Field(description="到达城市")
    date: str = Field(description="出发日期，格式 YYYY-MM-DD")
    time: str = Field(description="出发时间，格式 HH:MM(24小时制)")
    train_type: Literal["高铁", "普通火车", "动车", "飞机"] = Field(description="车型")
    passengers: int = Field(default=1, ge=1, le=10, description="乘客人数，默认为1，范围1-10")

def call_llm_with_schema(user_input: str, model_class: type[BaseModel]) -> BaseModel:
    """
    🔑 终极方案：把 Pydantic 模型的 schema 嵌入 prompt
    然后用同一个模型校验返回值
    """
    # 1. 自动生成字段说明
    schema = model_class.model_json_schema()

    prompt = f"""从用户的话里提取信息，严格按照一下 JSON Schema 输出：

{json.dumps(schema, ensure_ascii=False, indent=2)}

要求：
- 必须返回合法 JSON
- 字段名必须完全匹配
- 不要包含 schema 中没有的字段
- 缺失信息可以使用合理推断

用户的话：{user_input}"""
    
    # 2. 调用 API （JSON Mode）
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个数据提取助手， 只返回 JSON 格式的结果"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}, 
        },
        timeout=30
    )
    response.raise_for_status()

    raw_reply = response.json()["choices"][0]["message"]["content"]
    raw_data = json.loads(raw_reply)

    # 3. 用 Pydantic 校验！不符合就抛 ValidationError
    validated = model_class.model_validate(raw_data)
    return validated

def safe_extract_ticket(user_input: str) -> Optional[TicketRequest]:
    """带完整异常处理的提取函数"""
    print(f"\n💬 用户输入：{user_input}")

    try:
        ticket = call_llm_with_schema(user_input, TicketRequest)
        print(f"✅ 校验通过！ 提取结果：")
        print(ticket.model_dump_json(indent=2))
        return ticket
    
    except ValidationError as e:
        print(f"❌ Pydantic 校验失败(AI 输出不符合业务规范): {e}")
        return None
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        return None
    
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return None
    
# ===== 实战： 模拟下游业务系统 =====
def book_ticket(ticket: TicketRequest):
    """模拟一个订票业务函数
    重点：这个函数只接收 TicketRequest 对象，类型安全！
    """

    print(f"\n💳 正在为您预定车票...")
    print(f"  {ticket.departure} -> {ticket.arrival}")
    print(f"  {ticket.date} {ticket.time}")
    print(f"  {ticket.train_type} 乘客数: {ticket.passengers}")
    print(f"✅ 预定成功！(模拟)")

if __name__ == "__main__":
    test_inputs = [
        "我要订明天从北京到上海的高铁，下午三点出发，2个人",
        "帮我订一张从广州到深圳的火车票，后天早上八点的",
        "我想订一张从杭州到南京的普通火车票，明天下午两点的，3个人",
        "我要订一张从成都到重庆的飞机票，明天中午12点的，1个人",
        "帮我订一张从武汉到长沙的动车票，后天晚上7点的，5个人",
        "随便聊聊天"
    ]

    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{'=' * 60}")
        print(f"测试用例 {i}:")
        ticket = safe_extract_ticket(user_input)
        if ticket:
            book_ticket(ticket)
        else:
            print("⚠️ 未能提取有效订票信息，请用户重新表述")
