"""
Flask Web 应用入口
提供图片压缩工具的 Web 管理后台
"""
import os
import threading
import multiprocessing
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from compressor import ImageCompressor, run_compression_task
import time
import queue

app = Flask(__name__)

# 全局压缩进程状态
compressor_process: multiprocessing.Process = None
status_manager = multiprocessing.Manager()
status_dict = multiprocessing.Manager().dict()
log_queue = multiprocessing.Queue()
compressor_lock = threading.Lock()

# 从环境变量读取默认路径
DEFAULT_INPUT_DIR = os.environ.get('DEFAULT_INPUT_DIR', '/photos')
DEFAULT_OUTPUT_DIR = os.environ.get('DEFAULT_OUTPUT_DIR', '/output')


@app.route('/')
@app.route('/vue')
def index():
    """管理后台首页（Vue 版）"""
    return render_template(
        'index-vue.html',
        default_input=DEFAULT_INPUT_DIR,
        default_output=DEFAULT_OUTPUT_DIR
    )


@app.route('/api/status')
def api_status():
    """获取当前状态"""
    global compressor_process

    with compressor_lock:
        if compressor_process is None or not compressor_process.is_alive():
            return jsonify({
                'status': 'idle',
                'message': '空闲'
            })

        # 从共享状态字典读取进度
        progress = dict(status_dict) if status_dict else {}
        return jsonify({
            'status': 'running',
            'message': '压缩中',
            'progress': progress
        })


@app.route('/api/start', methods=['POST'])
def api_start():
    """开始压缩任务"""
    global compressor_process

    data = request.get_json() or {}
    input_dir = data.get('input_dir', DEFAULT_INPUT_DIR)
    output_dir = data.get('output_dir', DEFAULT_OUTPUT_DIR)
    jobs = int(data.get('jobs', 4))
    prefix = data.get('prefix', 'DSC')
    no_skip = data.get('no_skip', False)

    with compressor_lock:
        # 检查是否已有任务运行
        if compressor_process is not None and compressor_process.is_alive():
            return jsonify({
                'success': False,
                'message': '已有压缩任务正在运行'
            }), 400

        # 重置共享状态
        status_dict.clear()
        status_dict['is_running'] = False
        status_dict['total_files'] = 0
        status_dict['processed_count'] = 0
        status_dict['success_count'] = 0
        status_dict['failed_count'] = 0
        status_dict['percentage'] = 0

        # 清空旧日志队列
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except queue.Empty:
                break

        # 启动独立进程
        compressor_process = multiprocessing.Process(
            target=run_compression_task,
            args=(input_dir, output_dir, jobs, prefix, no_skip, status_dict, log_queue),
            daemon=True
        )
        compressor_process.start()

        return jsonify({
            'success': True,
            'message': '压缩任务已启动'
        })


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """停止压缩任务"""
    global compressor_process

    with compressor_lock:
        if compressor_process is None or not compressor_process.is_alive():
            return jsonify({
                'success': False,
                'message': '没有正在运行的任务'
            }), 400

        # 强制终止进程
        compressor_process.terminate()
        compressor_process.join(timeout=3)
        if compressor_process.is_alive():
            # 如果 SIGTERM 无效，使用 SIGKILL 强制杀死
            compressor_process.kill()
            compressor_process.join(timeout=1)

        # 等待一小段时间确保进程完全退出
        time.sleep(0.5)

    return jsonify({
        'success': True,
        'message': '已发送停止信号'
    })


@app.route('/api/logs')
def api_logs():
    """SSE 日志推送 - 从多进程队列读取日志"""
    def generate():
        while True:
            try:
                # 从多进程队列获取日志
                log = log_queue.get(timeout=0.5)
                yield f"data: {log}\n\n"
            except queue.Empty:
                # 检查进程状态
                with compressor_lock:
                    if compressor_process is None or not compressor_process.is_alive():
                        # 任务完成且无新日志，发送结束标记
                        yield "data: __END__\n\n"
                        break
                time.sleep(0.1)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/progress')
def api_progress():
    """SSE 进度推送 - 从共享状态字典读取"""
    def generate():
        while True:
            with compressor_lock:
                if compressor_process is None or not compressor_process.is_alive():
                    progress = {
                        'is_running': False,
                        'total_files': 0,
                        'processed_count': 0,
                        'success_count': 0,
                        'failed_count': 0,
                        'percentage': 0
                    }
                else:
                    progress = dict(status_dict)

            yield f"data: {progress}\n\n"

            if not progress.get('is_running', False):
                break

            time.sleep(0.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/directories')
def api_directories():
    """获取指定路径下的子目录列表"""
    base_path = request.args.get('path', DEFAULT_INPUT_DIR)

    try:
        path = Path(base_path)
        if not path.exists():
            return jsonify({
                'success': False,
                'error': '路径不存在',
                'directories': []
            })

        # 获取直接子目录
        subdirs = [d for d in path.iterdir() if d.is_dir()]

        directories = []
        for subdir in sorted(subdirs, key=lambda x: x.name.lower()):
            directories.append({
                'name': subdir.name,
                'path': str(subdir),
                'has_subdirs': any(d.is_dir() for d in subdir.iterdir())
            })

        # 不允许返回挂载路径的上级目录
        # 限制只能在 /photos 和 /output 目录下浏览
        allowed_roots = [Path('/photos'), Path('/output')]
        can_go_up = False
        parent_path = None

        if str(path) != '/' and path.parent in allowed_roots:
            # 当前路径是 allowed_roots 的直接子目录，可以返回上级
            can_go_up = True
            parent_path = str(path.parent)
        elif str(path) == '/' or path in allowed_roots:
            # 已经是根目录或允许的根目录，不能继续向上
            can_go_up = False
        # 其他情况（更深层级），不允许返回上级

        return jsonify({
            'success': True,
            'current_path': str(path),
            'can_go_up': can_go_up,
            'parent_path': parent_path,
            'directories': directories
        })
    except PermissionError:
        return jsonify({
            'success': False,
            'error': '无权访问该路径',
            'directories': []
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'directories': []
        }), 500


@app.route('/api/current-path')
def api_current_path():
    """获取当前默认路径配置"""
    return jsonify({
        'input_dir': DEFAULT_INPUT_DIR,
        'output_dir': DEFAULT_OUTPUT_DIR
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=False)
