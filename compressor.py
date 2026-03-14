"""
图片压缩核心模块
提供 ImageCompressor 类，支持可中断的并发压缩任务
"""
import os
import subprocess
import concurrent.futures
from pathlib import Path
import re
import threading
import queue
import logging
from datetime import datetime
from typing import Optional, Set, Dict, Any


class ImageCompressor:
    """图片压缩器类，支持多线程并发压缩和任务中断"""

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        jobs: int = 4,
        prefix: str = "DSC",
        no_skip: bool = False
    ):
        self.input_dir = Path(input_dir).resolve()
        # 自动使用输入目录的最后一级文件夹名作为输出子目录
        base_output_dir = Path(output_dir).resolve()
        self.output_dir = base_output_dir / self.input_dir.name
        self.jobs = jobs
        self.prefix = prefix
        self.no_skip = no_skip

        # 任务状态
        self._stop_flag = False
        self._is_running = False
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._lock = threading.Lock()

        # 进度追踪
        self._total_files = 0
        self._processed_count = 0
        self._success_count = 0
        self._failed_count = 0

        # 日志队列和列表
        self._log_queue = queue.Queue()
        self._log_history: list[str] = []
        self._max_log_lines = 1000  # 限制日志缓冲行数

        # 已处理的文件集合
        self._processed_images: Set[Path] = set()

        # 配置日志处理器，将日志发送到队列
        self._setup_logging()

    def _setup_logging(self):
        """设置自定义日志处理器，将日志发送到队列"""
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue, history_list, max_lines):
                super().__init__()
                self.log_queue = log_queue
                self.history_list = history_list
                self.max_lines = max_lines

            def emit(self, record):
                msg = self.format(record)
                self.log_queue.put(msg)
                self.history_list.append(msg)
                # 限制历史记录长度
                if len(self.history_list) > self.max_lines:
                    self.history_list.pop(0)

        # 创建处理器
        handler = QueueHandler(self._log_queue, self._log_history, self._max_log_lines)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        handler.setLevel(logging.INFO)

        # 添加到根日志器
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        self._log_queue.put(log_msg)
        with self._lock:
            self._log_history.append(log_msg)
            if len(self._log_history) > self._max_log_lines:
                self._log_history.pop(0)

    def _find_image_files(self) -> list[Path]:
        """查找所有符合条件的图片文件"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic']
        image_files = []
        prefix_pattern = re.compile(f"^{re.escape(self.prefix)}", re.IGNORECASE)

        for ext in image_extensions:
            for file_path in self.input_dir.rglob(f"*{ext}"):
                if file_path.is_file() and prefix_pattern.match(file_path.name):
                    image_files.append(file_path)
            for file_path in self.input_dir.rglob(f"*{ext.upper()}"):
                if file_path.is_file() and prefix_pattern.match(file_path.name):
                    image_files.append(file_path)

        return list(set(image_files))

    def _compress_image(self, file_path: Path) -> bool:
        """压缩单张图片"""
        if self._stop_flag:
            return False

        try:
            # 计算输出文件路径
            output_path = self.output_dir / file_path.relative_to(self.input_dir)

            # 检查是否已压缩过
            if output_path.exists() and not self.no_skip:
                self._log(f"⏭️ 已压缩，跳过：{file_path.name}")
                self._processed_images.add(output_path)
                with self._lock:
                    self._processed_count += 1
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
            self._log(f"✅ 成功压缩：{file_path.name}")

            # 记录已处理文件
            self._processed_images.add(output_path)
            with self._lock:
                self._processed_count += 1
                self._success_count += 1
            return True

        except subprocess.CalledProcessError as e:
            self._log(f"❌ 压缩失败：{file_path.name} - 错误：{e.stderr}")
            with self._lock:
                self._processed_count += 1
                self._failed_count += 1
            return False
        except Exception as e:
            self._log(f"⚠️ 处理错误：{file_path.name} - 原因：{str(e)}")
            with self._lock:
                self._processed_count += 1
                self._failed_count += 1
            return False

    def start(self) -> bool:
        """开始压缩任务"""
        with self._lock:
            if self._is_running:
                self._log("⚠️ 已有压缩任务正在运行")
                return False
            self._stop_flag = False
            self._is_running = True

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._log(f"📁 输入目录：{self.input_dir}")
        self._log(f"📂 输出目录：{self.output_dir}")
        self._log(f"🔤 文件名前缀：{self.prefix}")

        # 查找所有图片文件
        image_files = self._find_image_files()

        # 在锁的保护下设置总数
        with self._lock:
            self._total_files = len(image_files)

        if not image_files:
            self._log(f"⚠️ 未找到以 '{self.prefix}' 开头的图片文件")
            with self._lock:
                self._is_running = False
            return False

        self._log(f"🔍 找到 {self._total_files} 个符合条件的图片文件")
        self._log(f"🚀 启动压缩任务 (线程数：{self.jobs})...")

        # 校验线程数
        jobs = max(1, min(self.jobs, self._total_files))

        # 开始时间
        start_time = datetime.now()

        # 创建线程池并执行
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
                self._executor = executor
                futures = [executor.submit(self._compress_image, f) for f in image_files]

                for future in concurrent.futures.as_completed(futures):
                    if self._stop_flag:
                        self._log("⏹️ 用户中断压缩任务")
                        break
                    try:
                        future.result()
                    except Exception as e:
                        self._log(f"🔥 处理异常：{str(e)}")
        finally:
            self._executor = None
            with self._lock:
                self._is_running = False

        # 计算处理时间
        duration = datetime.now() - start_time
        mins, secs = divmod(duration.total_seconds(), 60)

        self._log(f"\n🎉 压缩完成！成功：{self._success_count}/{self._total_files}")
        self._log(f"⏱️ 处理时间：{int(mins)}分{int(secs)}秒")
        self._log(f"💾 压缩图片保存在：{self.output_dir}")

        return True

    def stop(self):
        """停止压缩任务"""
        with self._lock:
            if not self._is_running:
                return
            self._stop_flag = True
            self._log("⏹️ 正在停止压缩任务...")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        # 使用锁保护读取，确保数据一致性
        with self._lock:
            is_running = self._is_running
            total_files = self._total_files
            processed_count = self._processed_count
            success_count = self._success_count
            failed_count = self._failed_count

        percentage = 0
        if total_files > 0:
            percentage = round(processed_count / total_files * 100, 1)

        return {
            "is_running": is_running,
            "total_files": total_files,
            "processed_count": processed_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "percentage": percentage
        }

    def get_logs(self, start_line: int = 0) -> list[str]:
        """获取日志"""
        if start_line >= len(self._log_history):
            return []
        return self._log_history[start_line:]

    def reset(self):
        """重置状态"""
        with self._lock:
            self._stop_flag = False
            self._is_running = False
            self._total_files = 0
            self._processed_count = 0
            self._success_count = 0
            self._failed_count = 0
            self._processed_images.clear()
