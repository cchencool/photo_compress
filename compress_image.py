#!/usr/bin/env python
"""
CLI 模式图片压缩工具
"""
import os
import subprocess
import concurrent.futures
from pathlib import Path
import re
import argparse
import logging
from datetime import datetime

# 配置日志 - 使用专用 logger 避免污染根日志器
logger = logging.getLogger('photo_compressor_cli')
logger.setLevel(logging.INFO)

# 清除已有的 handler
if logger.handlers:
    logger.handlers.clear()

# 创建文件处理器
file_handler = logging.FileHandler("image_compressor.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)


def compress_image(file_path: Path, output_dir: Path, input_root: Path, processed_images: set, no_skip: bool) -> bool:
    """压缩单个图片文件"""
    try:
        # 计算输出文件的相对路径
        output_path = output_dir / file_path.relative_to(input_root)

        # 检查是否已压缩过
        if output_path.exists() and not no_skip:
            logger.info(f"⏭️ 已压缩，跳过：{file_path.name}")
            processed_images.add(output_path)
            return True

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建命令并执行
        cmd = [
            "magick", "mogrify",
            "-path", str(output_path.parent.resolve()),
            "-quality", "80",
            "-verbose",
            str(file_path.resolve())
        ]

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✅ 成功压缩：{file_path.name} → {output_path.name}")

        # 记录已处理文件
        processed_images.add(output_path)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ 压缩失败：{file_path.name}\n错误：{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"⚠️ 处理错误：{file_path.name}\n原因：{str(e)}")
        return False


def find_image_files(input_dir: Path, prefix: str) -> list[Path]:
    """查找所有符合条件的图片文件"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic']
    image_files = []
    prefix_pattern = re.compile(f"^{re.escape(prefix)}", re.IGNORECASE)

    for ext in image_extensions:
        for file_path in input_dir.rglob(f"*{ext}"):
            if file_path.is_file() and prefix_pattern.match(file_path.name):
                image_files.append(file_path)
        for file_path in input_dir.rglob(f"*{ext.upper()}"):
            if file_path.is_file() and prefix_pattern.match(file_path.name):
                image_files.append(file_path)

    return list(set(image_files))


def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='多线程图片压缩工具 - 仅处理 DSC 开头的文件')
    parser.add_argument('-i', '--input', type=str, required=True,
                        help='输入目录路径，包含待压缩图片')
    parser.add_argument('-o', '--output', type=str, required=True,
                        help='输出目录路径，用于保存压缩后的图片')
    parser.add_argument('-j', '--jobs', type=int, metavar='NUM',
                        default=os.cpu_count(),
                        help=f'并行任务数 (默认：CPU 核心数={os.cpu_count()})')
    parser.add_argument('--no-skip', action='store_true',
                        help='禁用跳过已压缩文件功能')
    parser.add_argument('--prefix', type=str, default="DSC",
                        help='文件名前缀 (默认：DSC)')
    args = parser.parse_args()

    # 解析输入输出路径
    input_root = Path(args.input).resolve()
    output_root = Path(args.output).resolve()

    # 在输出目录下创建以输入目录名称命名的子目录
    output_dir = output_root / input_root.name

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 输入目录：{input_root}")
    logger.info(f"📂 输出目录：{output_dir}")
    logger.info(f"🔤 文件名前缀：{args.prefix} (仅处理以此前缀开头的文件)")

    # 获取所有符合条件的图片文件
    image_files = find_image_files(input_root, args.prefix)

    if not image_files:
        logger.warning(f"⚠️ 输入目录未找到以 '{args.prefix}' 开头的图片文件")
        return

    logger.info(f"🔍 找到 {len(image_files)} 个符合条件的图片文件")
    logger.info(f"🚀 启动压缩任务 (线程数：{args.jobs})...")

    # 校验线程数
    jobs = max(1, min(args.jobs, len(image_files)))

    # 创建线程池并行处理
    success_count = 0
    processed_images = set()
    start_time = datetime.now()

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        # 提交所有压缩任务
        futures = []
        for file in image_files:
            future = executor.submit(
                compress_image,
                file,
                output_dir,
                input_root,
                processed_images,
                args.no_skip
            )
            futures.append(future)

        # 等待所有任务完成并统计结果
        for future in concurrent.futures.as_completed(futures):
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                logger.error(f"🔥 处理异常：{str(e)}")

    # 计算处理时间
    duration = datetime.now() - start_time
    mins, secs = divmod(duration.total_seconds(), 60)

    logger.info(f"\n🎉 压缩完成！成功：{success_count}/{len(image_files)} 失败：{len(image_files) - success_count}")
    logger.info(f"⏱️ 处理时间：{int(mins)}分{int(secs)}秒")
    logger.info(f"💾 压缩图片保存在：{output_dir}")
    logger.info(f"📝 已处理文件数：{len(processed_images)}")


if __name__ == "__main__":
    main()
