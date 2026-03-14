# Docker 部署说明

## 快速开始

### 1. 构建镜像

```bash
docker build -t photo-compressor .
```

### 2. 运行容器

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

### 3. 使用 docker-compose

1. 编辑 `docker-compose.yml`，修改 volumes 路径为实际路径
2. 运行：

```bash
# 构建并运行
docker-compose up --build

# 或后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f
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

压缩 `/home/user/photos` 目录下所有 DSC 开头的图片：

```bash
docker run --rm \
  -v /home/user/photos:/input \
  -v /home/user/compressed:/output \
  photo-compressor -i /input -o /output -j 4
```

## 日志

日志会输出到：
- 控制台
- 容器内的 `/logs/image_compressor.log`

挂载本地日志目录：
```bash
-v /path/to/local/logs:/logs
```
