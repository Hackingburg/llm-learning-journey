"""
Day 7-2: 把 AI 能力变成 Web API
目标：任何人都能通过 HTTP 调用你的 AI
"""
import os 
import requests 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv 


load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

app = FastAPI(title="AI Service", version="0.2.0")

# ===== 请求/响应 数据模型 ===== 
class ChatRequest(BaseModel):
    """请求体：用户发来什么"""
    message: str = Field(min_length=1, max_length=2000, description="用户消息")
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = Field(default="你是一个友好的 AI 助手")

class ChatResponse(BaseModel):
    """响应体：AI 回复什么"""
    reply: str
    input_tokens: int
    output_tokens: int
    cost: float  

# ===== 核心：调用 DeepSeek API 的函数 ===== 
def call_deepseek(message: str, temperature: float, system_prompt: str) -> dict:
    """封装好的LLM 调用"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "temperature": temperature
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()


# ===== API 端点 ===== 
@app.get("/")
def root():
    """健康检查"""
    return {"service": "AI Chat API", "status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    🎯 核心 API：发一条消息给 AI，返回回复 + 成本
    
    POST /chat
    Body:{"message": "你好", "temperature": 0.7}
    """

    try:
        data = call_deepseek(
            message=request.message,
            temperature=request.temperature,
            system_prompt=request.system_prompt
        )

        reply = data["choices"][0]["message"]["content"]
        usage = data["usage"]

        #计算成本
        cost = (usage["prompt_tokens"]/1_000_000 * 2.0 
                + usage["completion_tokens"]/1_000_000 * 8.0)
        
        return ChatResponse(
            reply=reply,
            input_tokens=usage["prompt_tokens"],
            output_tokens=usage["completion_tokens"],
            cost=round(cost, 6)
        )
    except requests.RequestException as e:
        # 🔑 用 HTTPException 返回标准错误
        raise HTTPException(status_code=502, detail=f"上游 AI 服务出错: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")