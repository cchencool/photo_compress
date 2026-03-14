# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

使用 ImageMagick 进行批量图片压缩的 Python CLI 工具，支持多线程并行处理。

## 运行方式

```bash
python compress_image.py -i <输入目录> -o <输出目录> [-j 线程数] [--prefix 前缀]
```

**参数说明：**
- `-i, --input` (必填): 输入图片目录
- `-o, --output` (必填): 输出目录
- `-j, --jobs`: 并行线程数 (默认：CPU 核心数)
- `--prefix`: 文件名前缀过滤 (默认："DSC"，不区分大小写)
- `--no-skip`: 禁用跳过已压缩文件的功能

## 依赖要求

- Python 3.x (标准库：concurrent.futures, pathlib, argparse)
- ImageMagick (`magick` 命令需在 PATH 中可用)

## 代码结构

单文件脚本 `compress_image.py`:

- `compress_image(file_path, output_dir, processed_images)`: 压缩单张图片，若输出文件已存在则跳过
- `main()`: 解析命令行参数，递归查找匹配前缀的图片，使用 ThreadPoolExecutor 并行压缩

输出目录结构会镜像输入目录的层级，日志同时输出到 `image_compressor.log` 文件和控制台。

## Docker 部署

**构建镜像：**
```bash
docker build -t photo-compressor .
```

**运行容器：**
```bash
docker run --rm \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  photo-compressor -i /input -o /output -j 4 --prefix DSC
```

**使用 docker-compose：**
1. 编辑 `docker-compose.yml` 修改 volumes 路径
2. 运行 `docker-compose up --build`

详见 `README.Docker.md`
