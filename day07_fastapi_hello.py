"""
Day 7-1: FastAPI 入门 - Hello World
目标：理解什么是 API endpoint，5 分钟开一个 Web 服务
"""

from fastapi import FastAPI
from pydantic import BaseModel

# 创建一个 FastAPI 应用
app = FastAPI(
    title="我的第一个 Web 服务",
    description="Day 7 学习项目",
    version="0.1.0"
)


# ===== 端点 1：最简单的 GET 接口 =====
@app.get("/")
def root():
    """根路径，访问 http://localhost:8000/ 就能看到"""
    return {"message": "Hello, FastAPI!", "status": "running"}

# ===== 端点 2: 带路径参数 =====

@app.get("/hello/{name}")
def say_hello(name: str):
    """
    路径参数：URL 里的 {name} 会被传入函数参数 name
    访问 http://localhost:8000/hello/jack
    """ 
    return {"greeting": f"你好, {name}! 欢迎学习 FastAPI!"}

# ===== 端点 3: 带查询参数 =====
@app.get("/add")
def add_numbers(a: int, b: int):
    """
    查询参数：访问 http://localhost:8000/add?a=3&b=5
    """
    return {"a": a, "b": b, "sum": a + b}

# ===== 端点 4: POST 请求 + Pydantic 模型 =====
class UserInput(BaseModel):
    """用 Pydantic 定义请求体"""
    name: str
    age: int 

@app.post("/register")
def register(user: UserInput):
    """
    POST 请求需要用工具测试（浏览器只能 GET）
    访问 http://localhost:8000/docs 自动生成的交互文档
    """
    return {
        "message": f"注册成功！欢迎 {user.name}",
        "received": user.model_dump()
    }