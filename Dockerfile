# 使用轻量级 Python 镜像
FROM python:3.12-slim

# 安装 ImageMagick
RUN apt-get update && apt-get install -y --no-install-recommends \
    imagemagick \
    && rm -rf /var/lib/apt/lists/* \
    # 禁用 ImageMagick 的安全策略限制（允许处理各种图片格式）
    && sed -i '/<policy domain="coder" rights="none" pattern="HTTPS"/d' /etc/ImageMagick-6/policy.xml \
    && sed -i '/<policy domain="coder" rights="none" pattern="HTTP"/d' /etc/ImageMagick-6/policy.xml \
    && sed -i '/<policy domain="coder" rights="none" pattern="URL"/d' /etc/ImageMagick-6/policy.xml

# 设置工作目录
WORKDIR /app

# 复制脚本
COPY compress_image.py .

# 创建日志目录并赋予写权限
RUN mkdir -p /logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 入口点
ENTRYPOINT ["python", "compress_image.py"]
