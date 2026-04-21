# 后端 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 配置国内源
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装 Poetry（使用阿里云源）
RUN pip install --no-cache-dir "poetry>=2.0.0"

# 配置 Poetry
RUN poetry config virtualenvs.create false

# 复制依赖文件
COPY pyproject.toml poetry.lock ./

# 安装依赖（开发环境和生产环境都安装，以便支持开发模式）
RUN poetry install --no-root

# 复制应用代码
COPY . .

# 创建非 root 用户（生产环境最佳实践）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令（使用 uvicorn 并支持热重载）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
