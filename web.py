"""
Flask Web 应用入口
提供图片压缩工具的 Web 管理后台
"""
import os
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from compressor import ImageCompressor
import time

app = Flask(__name__)

# 全局压缩器实例
compressor: ImageCompressor = None
compressor_lock = threading.Lock()

# 从环境变量读取默认路径
DEFAULT_INPUT_DIR = os.environ.get('DEFAULT_INPUT_DIR', '/photos')
DEFAULT_OUTPUT_DIR = os.environ.get('DEFAULT_OUTPUT_DIR', '/output')


@app.route('/')
def index():
    """管理后台首页"""
    return render_template(
        'index.html',
        default_input=DEFAULT_INPUT_DIR,
        default_output=DEFAULT_OUTPUT_DIR
    )


@app.route('/api/status')
def api_status():
    """获取当前状态"""
    global compressor

    with compressor_lock:
        if compressor is None or not compressor.is_running:
            return jsonify({
                'status': 'idle',
                'message': '空闲'
            })

        progress = compressor.get_progress()
        return jsonify({
            'status': 'running',
            'message': '压缩中',
            'progress': progress
        })


@app.route('/api/start', methods=['POST'])
def api_start():
    """开始压缩任务"""
    global compressor

    data = request.get_json() or {}
    input_dir = data.get('input_dir', DEFAULT_INPUT_DIR)
    output_dir = data.get('output_dir', DEFAULT_OUTPUT_DIR)
    jobs = data.get('jobs', 4)
    prefix = data.get('prefix', 'DSC')
    no_skip = data.get('no_skip', False)

    with compressor_lock:
        # 检查是否已有任务运行
        if compressor is not None and compressor.is_running:
            return jsonify({
                'success': False,
                'message': '已有压缩任务正在运行'
            }), 400

        # 创建新的压缩器实例
        compressor = ImageCompressor(
            input_dir=input_dir,
            output_dir=output_dir,
            jobs=jobs,
            prefix=prefix,
            no_skip=no_skip
        )

        # 在新线程中启动压缩任务
        def run_compression():
            try:
                compressor.start()
            except Exception as e:
                compressor._log(f"❌ 压缩任务异常：{str(e)}")
            finally:
                with compressor_lock:
                    pass  # 保持实例以显示最终状态

        thread = threading.Thread(target=run_compression, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': '压缩任务已启动'
        })


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """停止压缩任务"""
    global compressor

    with compressor_lock:
        if compressor is None or not compressor.is_running:
            return jsonify({
                'success': False,
                'message': '没有正在运行的任务'
            }), 400

        compressor.stop()
        return jsonify({
            'success': True,
            'message': '已发送停止信号'
        })


@app.route('/api/logs')
def api_logs():
    """SSE 日志推送"""
    global compressor

    def generate():
        last_line = 0
        while True:
            with compressor_lock:
                if compressor is None:
                    logs = []
                else:
                    logs = compressor.get_logs(last_line)
                    last_line = len(compressor.get_logs())

            if logs:
                for log in logs:
                    yield f"data: {log}\n\n"
                last_line += len(logs)

            # 检查是否有压缩任务在完成
            with compressor_lock:
                is_running = compressor is not None and compressor.is_running

            if not is_running and not logs:
                # 任务完成且无新日志，发送结束标记
                yield "data: __END__\n\n"
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


@app.route('/api/progress')
def api_progress():
    """SSE 进度推送"""
    global compressor

    def generate():
        while True:
            with compressor_lock:
                if compressor is None:
                    progress = {
                        'is_running': False,
                        'total_files': 0,
                        'processed_count': 0,
                        'success_count': 0,
                        'failed_count': 0,
                        'percentage': 0
                    }
                else:
                    progress = compressor.get_progress()

            yield f"data: {progress}\n\n"

            if not progress['is_running']:
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

        # 添加父目录选项（如果有）
        parent = path.parent
        can_go_up = str(parent) != str(path) and str(path) != '/'

        return jsonify({
            'success': True,
            'current_path': str(path),
            'can_go_up': can_go_up,
            'parent_path': str(parent) if can_go_up else None,
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
    app.run(host='0.0.0.0', port=5000, debug=False)
