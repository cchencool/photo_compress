# Docker 部署说明

## 镜像信息

- **镜像名称**: `cchencool/photo-compressor:latest`
- **基础镜像**: `python:3.12-slim`
- **暴露端口**: 5000 (Web 管理后台)

## 快速开始

### 方式一：Web 管理后台（推荐）

```bash
# 使用 docker-compose
docker-compose up -d

# 访问管理后台
http://localhost:5000
```

### 方式二：CLI 模式

```bash
docker run --rm \
  -v /path/to/input:/photos:ro \
  -v /path/to/output:/output \
  cchencool/photo-compressor:latest \
  -i /photos -o /output -j 4 --prefix DSC
```

## 构建镜像

```bash
docker build -t photo-compressor .
```

## 运行容器

### Web 模式

**基本用法：**
```bash
docker run --rm -d \
  -p 5000:5000 \
  -v /path/to/input:/photos:ro \
  -v /path/to/output:/output \
  -e DEFAULT_INPUT_DIR=/photos \
  -e DEFAULT_OUTPUT_DIR=/output \
  photo-compressor
```

**参数说明：**

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `DEFAULT_INPUT_DIR` | Web 界面默认输入路径 | /photos |
| `DEFAULT_OUTPUT_DIR` | Web 界面默认输出路径 | /output |

### CLI 模式

**基本用法：**
```bash
docker run --rm \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  photo-compressor -i /input -o /output
```

**带参数运行：**
```bash
docker run --rm \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  photo-compressor -i /input -o /output -j 8 --prefix DSC
```

## 使用 docker-compose

1. 编辑 `docker-compose.yml`，修改 volumes 路径：

```yaml
volumes:
  - /your/photos/path:/photos:ro
  - ./output:/output
```

2. 运行：

```bash
# 构建并运行
docker-compose up --build

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入图片目录（容器内路径） | 必填 |
| `-o, --output` | 输出目录（容器内路径） | 必填 |
| `-j, --jobs` | 并行线程数 | CPU 核心数 |
| `--prefix` | 文件名前缀过滤 | DSC |
| `--no-skip` | 禁用跳过已压缩文件 | 启用跳过 |

## 示例

### 示例 1：压缩家庭照片

压缩 `/home/user/photos/2024` 目录下所有 DSC 开头的图片：

```bash
docker run --rm \
  -v /home/user/photos/2024:/photos:ro \
  -v /home/user/compressed:/output \
  cchencool/photo-compressor:latest \
  -i /photos -o /output -j 4
```

### 示例 2：使用 Web 管理后台

```bash
docker-compose up -d
```

然后在浏览器访问 `http://localhost:5000`，在界面上配置路径并开始压缩。

## 日志

日志会输出到：
- 控制台
- 容器内的 `/logs/image_compressor.log`
- Web 管理后台（实时查看）

挂载本地日志目录：
```yaml
volumes:
  - ./logs:/logs
```

## 网络

Web 管理后台默认暴露 **5000** 端口。

如需修改端口：
```yaml
ports:
  - "8080:5000"  # 宿主机 8080 映射到容器 5000
```

## 安全考虑

1. **只读挂载**: 输入目录使用 `:ro` 只读挂载，防止误修改原文件
2. **路径限制**: 容器内无法访问宿主机其他路径
3. **内网访问**: 默认仅本地可访问，如需外网访问请配置防火墙
