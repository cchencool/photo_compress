# 图片压缩工具

使用 ImageMagick 进行批量图片压缩的 Python CLI 工具，支持多线程并行处理。

## 功能特点

- 支持多种图片格式：JPG, JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC
- 多线程并行压缩，充分利用 CPU 性能
- 递归处理子目录
- 支持文件名前缀过滤
- 自动跳过已压缩文件
- 质量可配置（默认 80%）
- 详细的日志输出

## 环境要求

- Python 3.x
- ImageMagick (`magick` 命令需在 PATH 中)

## 安装依赖

```bash
# 安装 ImageMagick
# Ubuntu/Debian
sudo apt-get install imagemagick

# macOS
brew install imagemagick

# CentOS/RHEL
sudo yum install ImageMagick
```

## 使用方法

### 基本用法

```bash
python compress_image.py -i <输入目录> -o <输出目录>
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

# 压缩所有图片（不限制前缀）
python compress_image.py -i ./photos -o ./output --prefix ""
```

## Docker 部署

### 从 Docker Hub 拉取

```bash
docker pull cchencool/photo-compressor:latest
```

### 运行容器

```bash
docker run --rm \
  -v /path/to/input:/photos:ro \
  -v /path/to/output:/output \
  cchencool/photo-compressor:latest \
  -i /photos -o /output -j 4 --prefix DSC
```

### 使用 docker-compose

1. 编辑 `docker-compose.yml`，修改 volumes 路径为实际路径
2. 运行：

```bash
# 构建并运行
docker-compose up --build

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f
```

详见 [README.Docker.md](README.Docker.md)

## 输出说明

- 输出目录结构会镜像输入目录的层级
- 日志输出到：
  - 控制台
  - `image_compressor.log` 文件

## 项目结构

```
photo_compress/
├── compress_image.py      # 主程序
├── Dockerfile             # Docker 镜像配置
├── docker-compose.yml     # Docker Compose 配置
├── README.md              # 项目说明
└── README.Docker.md       # Docker 部署说明
```

## License

MIT
