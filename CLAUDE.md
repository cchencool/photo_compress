# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

图片压缩工具 v1.1，支持 CLI 和 Web 管理后台两种模式：
- **CLI 模式**：纯命令行批量压缩
- **Web 模式**：Flask 管理后台，支持实时进度、日志查看、任务中断

## 技术栈

- **后端**: Python 3.12, Flask 3.x, ImageMagick
- **前端**: 原生 HTML/CSS/JS, SSE (Server-Sent Events)
- **部署**: Docker, docker-compose

## 代码结构

| 文件 | 描述 |
|------|------|
| `compressor.py` | 核心压缩类 `ImageCompressor`，支持 start/stop/get_progress/get_logs |
| `web.py` | Flask Web 应用入口，提供 REST API 和 SSE 推送 |
| `compress_image.py` | CLI 入口（兼容旧版） |
| `templates/index.html` | 管理后台页面 |
| `static/` | 前端资源（style.css, script.js） |
| `requirements.txt` | Python 依赖 |

## 运行方式

### CLI 模式
```bash
python compress_image.py -i <输入目录> -o <输出目录> [-j 线程数] [--prefix 前缀]
```

### Web 模式
```bash
python web.py
# 访问 http://localhost:5000
```

### Docker 模式
```bash
docker-compose up --build
# 访问 http://localhost:5000
```

## API 接口

| 路由 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 管理后台首页 |
| `/api/status` | GET | 获取当前状态（空闲/压缩中） |
| `/api/start` | POST | 开始压缩任务 |
| `/api/stop` | POST | 停止压缩任务 |
| `/api/logs` | GET (SSE) | 实时日志推送 |
| `/api/progress` | GET (SSE) | 实时进度推送 |

## 依赖要求

- Python 3.x (标准库：concurrent.futures, pathlib, threading, queue)
- Flask 3.x (Web 模式)
- ImageMagick (`magick` 命令需在 PATH 中可用)

## 关键实现细节

### ImageCompressor 类
- `start()`: 开始压缩任务，返回布尔值表示是否成功启动
- `stop()`: 设置停止标志，当前处理完成后停止
- `get_progress()`: 返回进度字典（is_running, total_files, processed_count, percentage 等）
- `get_logs(start_line)`: 返回指定行之后的日志列表
- 使用 `threading.Lock` 保护共享状态
- 日志使用队列收集，限制最大缓冲行数（1000 行）

### SSE 推送
- 日志和进度都使用 SSE 推送，非 WebSocket
- 客户端使用 `EventSource` 监听
- 日志推送在任务完成时发送 `__END__` 标记

## Docker 部署

**构建镜像：**
```bash
docker build -t photo-compressor .
```

**Web 模式运行：**
```bash
docker run --rm -d -p 5000:5000 \
  -v /path/to/input:/photos:ro \
  -v /path/to/output:/output \
  -e DEFAULT_INPUT_DIR=/photos \
  -e DEFAULT_OUTPUT_DIR=/output \
  photo-compressor
```

**使用 docker-compose：**
```bash
docker-compose up -d
```

详见 `README.Docker.md`
