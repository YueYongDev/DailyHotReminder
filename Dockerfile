FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录（如果需要）
RUN mkdir -p /app/logs

# 设置环境变量
ENV RUN_AS_SCHEDULER=true

# 暴露端口（如果应用需要）
# EXPOSE 8000

# 启动应用
CMD ["python", "daily_hot_scheduler.py"]