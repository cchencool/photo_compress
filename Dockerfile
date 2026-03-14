# 使用轻量级 Python 镜像
FROM python:3.12-slim

# 安装 ImageMagick
RUN apt-get update && apt-get install -y --no-install-recommends \
    imagemagick \
    && rm -rf /var/lib/apt/lists/* \
    # 禁用 ImageMagick 的安全策略限制（允许处理各种图片格式）
    && (sed -i '/<policy domain="coder" rights="none" pattern="HTTPS"/d' /etc/ImageMagick-7/policy.xml 2>/dev/null || true) \
    && (sed -i '/<policy domain="coder" rights="none" pattern="HTTP"/d' /etc/ImageMagick-7/policy.xml 2>/dev/null || true) \
    && (sed -i '/<policy domain="coder" rights="none" pattern="URL"/d' /etc/ImageMagick-7/policy.xml 2>/dev/null || true)

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY compress_image.py compressor.py web.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# 创建日志目录并赋予写权限
RUN mkdir -p /logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DEFAULT_INPUT_DIR=/photos
ENV DEFAULT_OUTPUT_DIR=/output

# 暴露 Web 端口
EXPOSE 5555

# 入口点 - Flask Web 应用
ENTRYPOINT ["python", "web.py"]
