# FC 自定义容器镜像
# 构建: docker build -t travel-notification:latest -f deploy/fc/Dockerfile .
# 推送到 ACR 后在 FC 控制台选择"容器镜像"部署

FROM python:3.11-slim

WORKDIR /code

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir httpx jinja2

# 复制源代码和 bootstrap
COPY src/ ./src/
COPY deploy/fc/bootstrap ./bootstrap
RUN chmod +x ./bootstrap

# FC 自定义运行时需要此文件
ENV FC_SERVER_PORT=9000
EXPOSE 9000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/api/health || exit 1

ENTRYPOINT ["/code/bootstrap"]
