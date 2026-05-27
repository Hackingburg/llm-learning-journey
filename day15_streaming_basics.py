"""
Day 15-1: FastAPI 流式输出入门
🎯 体验 Server-Sent Events (SSE)
"""
import time
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


# ===== 同步版（理解基础）=====
def slow_text_generator():
    """模拟一个"慢慢生成"的过程"""
    words = ["你好", "，", "这是", "一段", "流式", "输出", "测试", "！"]
    for word in words:
        time.sleep(0.5)  # 模拟思考
        # 🔑 SSE 格式：每行 'data: xxx\n\n'
        yield f"data: {word}\n\n"


@app.get("/stream-sync")
def stream_sync():
    """同步流式"""
    return StreamingResponse(
        slow_text_generator(),
        media_type="text/event-stream"  # 🔑 关键 MIME 类型
    )


# ===== 异步版（更高性能）=====
async def async_generator():
    """异步生成器，能让服务器同时处理多个请求"""
    for i in range(10):
        await asyncio.sleep(0.3)
        yield f"data: 第 {i+1} 块数据\n\n"


@app.get("/stream-async")
async def stream_async():
    return StreamingResponse(
        async_generator(),
        media_type="text/event-stream"
    )


# 启动：uvicorn day15_streaming_basics:app --reload