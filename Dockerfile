# 1. 选一个干净的 Python 基础镜像
FROM python:3.12-slim

# 2. 设工作目录
WORKDIR /app

# 3. 先拷贝依赖文件，单独安装（利用 Docker 缓存机制）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 拷贝项目所有代码进来
COPY . .

# 5. 创建数据目录（持久化用）
RUN mkdir -p /app/data

# 6. 暴露端口（FastAPI 默认 8000）
EXPOSE 8000

# 7. 启动命令
#    --host 0.0.0.0 让容器外能访问（127.0.0.1 只允许容器内访问）
CMD ["uvicorn", "day16_deepchat_pro:app", "--host", "0.0.0.0", "--port", "8000"]