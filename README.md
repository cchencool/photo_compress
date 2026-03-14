# 图片压缩工具 v1.1

使用 ImageMagick 进行批量图片压缩的 Python 工具，支持 CLI 和 Web 管理后台两种使用方式。

## 功能特点

- 支持多种图片格式：JPG, JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC
- 多线程并行压缩，充分利用 CPU 性能
- 递归处理子目录
- 支持文件名前缀过滤
- 自动跳过已压缩文件
- 质量可配置（默认 80%）
- 详细的日志输出
- **Web 管理后台**：实时进度、日志查看、任务中断

## 环境要求

- Python 3.x
- ImageMagick (`magick` 命令需在 PATH 中)
- Flask (Web 模式)

## 安装依赖

```bash
# 安装 ImageMagick
# Ubuntu/Debian
sudo apt-get install imagemagick

# macOS
brew install imagemagick

# CentOS/RHEL
sudo yum install ImageMagick

# 安装 Python 依赖（Web 模式）
pip install -r requirements.txt
```

## 使用方法

### CLI 模式

```bash
python compress_image.py -i <输入目录> -o <输出目录>
```

### Web 模式

```bash
python web.py
# 访问 http://localhost:5000
```

### 完整参数

```bash
python compress_image.py -i <输入目录> -o <输出目录> [-j 线程数] [--prefix 前缀] [--no-skip]
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入图片目录 | 必填 |
| `-o, --output` | 输出目录 | 必填 |
| `-j, --jobs` | 并行线程数 | CPU 核心数 |
| `--prefix` | 文件名前缀过滤（不区分大小写） | DSC |
| `--no-skip` | 禁用跳过已压缩文件功能 | 启用跳过 |

### 示例

```bash
# 压缩所有 DSC 开头的图片
python compress_image.py -i /home/user/photos -o /home/user/compressed

# 使用 8 个线程压缩
python compress_image.py -i ./photos -o ./output -j 8

# 压缩特定前缀的图片
python compress_image.py -i ./photos -o ./output --prefix IMG

# 启动 Web 管理后台
python web.py
```

## Web 管理后台

### 功能

- 自定义输入/输出路径
- 实时进度显示（百分比、已处理数/总数）
- 实时日志推送（SSE）
- 任务中断控制

### API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 管理后台首页 |
| `/api/status` | GET | 获取当前状态 |
| `/api/start` | POST | 开始压缩任务 |
| `/api/stop` | POST | 停止压缩任务 |
| `/api/logs` | GET (SSE) | 实时日志推送 |
| `/api/progress` | GET (SSE) | 实时进度推送 |

## Docker 部署

### 从 Docker Hub 拉取

```bash
docker pull cchencool/photo-compressor:latest
```

### Web 模式运行

```bash
docker run --rm -d \
  -p 5000:5000 \
  -v /path/to/input:/photos:ro \
  -v /path/to/output:/output \
  -e DEFAULT_INPUT_DIR=/photos \
  -e DEFAULT_OUTPUT_DIR=/output \
  cchencool/photo-compressor:latest
```

访问 `http://localhost:5000` 使用 Web 管理后台。

### CLI 模式运行

```bash
docker run --rm \
  -v /path/to/input:/photos:ro \
  -v /path/to/output:/output \
  cchencool/photo-compressor:latest \
  -i /photos -o /output -j 4 --prefix DSC
```

### 使用 docker-compose

```bash
# 启动 Web 服务
docker-compose up -d

# 访问 http://localhost:5000

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 项目结构

```
photo_compress/
├── compressor.py          # 压缩核心类
├── web.py                 # Flask Web 应用
├── compress_image.py      # CLI 入口（兼容旧版）
├── requirements.txt       # Python 依赖
├── templates/
│   └── index.html        # 管理后台页面
├── static/
│   ├── style.css         # 样式
│   └── script.js         # 前端逻辑
├── Dockerfile             # Docker 镜像配置
├── docker-compose.yml     # Docker Compose 配置
└── README.md              # 项目说明
```

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │   Flask     │◄──►│   Compression │◄──►│ ImageMagick│  │
│  │   Web Server│    │    Manager    │    │   (magick) │  │
│  └──────┬──────┘    └──────┬───────┘    └────────────┘  │
│         │                  │                              │
│  ┌──────▼──────┐    ┌──────▼───────┐                     │
│  │   Static    │    │   SSE        │                     │
│  │    Files    │    │   Push       │                     │
│  └─────────────┘    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP/SSE
                          │
                    用户浏览器
```

## 输出说明

- 输出目录自动使用输入目录的最后一级文件夹名
  - 例如：输入 `/photos/2024-trip/` → 输出 `/output/2024-trip/`
- 输出目录结构会镜像输入目录的层级
- 日志输出到：
  - 控制台
  - `image_compressor.log` 文件
  - Web 管理后台（实时）

## License

MIT
