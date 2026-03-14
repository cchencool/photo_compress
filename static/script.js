/**
 * 图片压缩工具 - 前端脚本
 * 处理 SSE 日志/进度推送和 UI 交互
 */

// DOM 元素引用
const elements = {
    inputDir: document.getElementById('inputDir'),
    outputDir: document.getElementById('outputDir'),
    jobs: document.getElementById('jobs'),
    prefix: document.getElementById('prefix'),
    noSkip: document.getElementById('noSkip'),
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText'),
    successCount: document.getElementById('successCount'),
    failedCount: document.getElementById('failedCount'),
    totalCount: document.getElementById('totalCount'),
    statusBadge: document.getElementById('statusBadge'),
    logContainer: document.getElementById('logContainer'),
    browseInputBtn: document.getElementById('browseInputBtn'),
    browseOutputBtn: document.getElementById('browseOutputBtn'),
    directoryModal: document.getElementById('directoryModal'),
    directoryList: document.getElementById('directoryList'),
    pathNav: document.getElementById('pathNav'),
    modalClose: document.querySelector('.modal-close'),
    modalCancel: document.querySelector('.modal-cancel'),
    modalConfirm: document.querySelector('.modal-confirm')
};

// 状态
let isRunning = false;
let logSource = null;
let progressSource = null;
let logLineCount = 0;

// 目录浏览器状态
let directoryBrowser = {
    currentPath: '/photos',
    targetInput: null,  // 'input' or 'output'
    selectedPath: null
};

/**
 * 初始化事件监听
 */
function init() {
    elements.startBtn.addEventListener('click', startCompression);
    elements.stopBtn.addEventListener('click', stopCompression);

    // 目录浏览按钮
    if (elements.browseInputBtn) {
        elements.browseInputBtn.addEventListener('click', () => openDirectoryBrowser('input'));
    }
    if (elements.browseOutputBtn) {
        elements.browseOutputBtn.addEventListener('click', () => openDirectoryBrowser('output'));
    }

    // 模态框事件
    if (elements.modalClose) {
        elements.modalClose.addEventListener('click', closeModal);
    }
    if (elements.modalCancel) {
        elements.modalCancel.addEventListener('click', closeModal);
    }
    if (elements.modalConfirm) {
        elements.modalConfirm.addEventListener('click', confirmDirectorySelection);
    }

    // 点击模态框外部关闭
    if (elements.directoryModal) {
        elements.directoryModal.addEventListener('click', (e) => {
            if (e.target === elements.directoryModal) {
                closeModal();
            }
        });
    }

    // 初始检查状态
    checkStatus();
}

/**
 * 检查当前状态
 */
async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.status === 'running' && data.progress) {
            updateProgress(data.progress);
            setRunningState(true);
        }
    } catch (error) {
        console.error('检查状态失败:', error);
    }
}

/**
 * 开始压缩
 */
async function startCompression() {
    const config = {
        input_dir: elements.inputDir.value.trim(),
        output_dir: elements.outputDir.value.trim(),
        jobs: parseInt(elements.jobs.value) || 4,
        prefix: elements.prefix.value.trim() || 'DSC',
        no_skip: elements.noSkip.checked
    };

    // 验证输入
    if (!config.input_dir || !config.output_dir) {
        alert('请输入输入目录和输出目录');
        return;
    }

    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            addLog('▶️ 压缩任务已启动', 'info');
            setRunningState(true);
            startSSEListeners();
        } else {
            alert(data.message || '启动失败');
        }
    } catch (error) {
        console.error('启动压缩失败:', error);
        alert('启动压缩失败：' + error.message);
    }
}

/**
 * 停止压缩
 */
async function stopCompression() {
    try {
        const response = await fetch('/api/stop', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            addLog('⏹️ 已发送停止信号', 'warning');
        } else {
            console.warn(data.message);
        }
    } catch (error) {
        console.error('停止压缩失败:', error);
    }
}

/**
 * 设置运行状态
 */
function setRunningState(running) {
    isRunning = running;
    elements.startBtn.disabled = running;
    elements.stopBtn.disabled = !running;

    // 禁用配置输入
    const inputs = [elements.inputDir, elements.outputDir, elements.jobs, elements.prefix, elements.noSkip];
    inputs.forEach(input => {
        input.disabled = running;
    });

    if (running) {
        elements.statusBadge.className = 'status-badge running';
        elements.statusBadge.innerHTML = '<span class="dot"></span> 压缩中...';
    } else {
        elements.statusBadge.className = 'status-badge';
        elements.statusBadge.innerHTML = '<span class="dot"></span> 空闲';
    }
}

/**
 * 更新进度显示
 */
function updateProgress(progress) {
    const percentage = progress.percentage || 0;
    const processed = progress.processed_count || 0;
    const total = progress.total_files || 0;
    const success = progress.success_count || 0;
    const failed = progress.failed_count || 0;

    elements.progressFill.style.width = percentage + '%';
    elements.progressText.textContent = `${percentage}% (${processed}/${total})`;
    elements.successCount.textContent = success;
    elements.failedCount.textContent = failed;
    elements.totalCount.textContent = total;
}

/**
 * 启动 SSE 监听
 */
function startSSEListeners() {
    // 关闭旧的连接
    if (logSource) logSource.close();
    if (progressSource) progressSource.close();

    // 监听日志
    logSource = new EventSource('/api/logs');
    logSource.onmessage = function(event) {
        if (event.data === '__END__') {
            logSource.close();
            setRunningState(false);
            return;
        }
        addLog(event.data);
    };

    logSource.onerror = function() {
        console.error('日志 SSE 连接错误');
        logSource.close();
    };

    // 监听进度
    progressSource = new EventSource('/api/progress');
    progressSource.onmessage = function(event) {
        try {
            const progress = JSON.parse(event.data);
            updateProgress(progress);

            if (!progress.is_running) {
                progressSource.close();
                setRunningState(false);
            }
        } catch (e) {
            console.error('解析进度失败:', e);
        }
    };

    progressSource.onerror = function() {
        console.error('进度 SSE 连接错误');
        progressSource.close();
    };
}

/**
 * 添加日志条目
 */
function addLog(message, type = '') {
    // 清除空状态提示
    const emptyMsg = elements.logContainer.querySelector('.log-empty');
    if (emptyMsg) {
        emptyMsg.remove();
    }

    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry ' + type;
    logEntry.textContent = message;
    elements.logContainer.appendChild(logEntry);

    // 滚动到底部
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
}

/**
 * 打开目录浏览器
 */
async function openDirectoryBrowser(target) {
    directoryBrowser.targetInput = target;
    directoryBrowser.selectedPath = null;

    // 根据目标设置当前路径
    if (target === 'input') {
        directoryBrowser.currentPath = elements.inputDir.value.trim() || '/photos';
    } else {
        directoryBrowser.currentPath = elements.outputDir.value.trim() || '/output';
    }

    // 显示模态框
    elements.directoryModal.classList.add('show');

    // 加载目录列表
    await loadDirectories(directoryBrowser.currentPath);
}

/**
 * 加载目录列表
 */
async function loadDirectories(path) {
    try {
        const response = await fetch(`/api/directories?path=${encodeURIComponent(path)}`);
        const data = await response.json();

        if (data.success) {
            // 更新路径导航
            elements.pathNav.innerHTML = `<span class="path-current">${data.current_path}</span>`;

            // 构建目录列表
            let html = '';

            // 返回上级目录
            if (data.can_go_up) {
                html += `
                    <div class="dir-item dir-up" data-path="${data.parent_path}">
                        <span class="dir-icon">📁</span>
                        <span class="dir-name">.. 返回上级</span>
                    </div>
                `;
            }

            // 子目录列表
            if (data.directories.length === 0) {
                html += '<div class="dir-item" style="cursor: default; color: #999;">暂无子目录</div>';
            } else {
                data.directories.forEach(dir => {
                    const icon = dir.has_subdirs ? '📂' : '📁';
                    html += `
                        <div class="dir-item" data-path="${dir.path}" data-has-subdirs="${dir.has_subdirs}">
                            <span class="dir-icon">${icon}</span>
                            <span class="dir-name">${dir.name}</span>
                        </div>
                    `;
                });
            }

            elements.directoryList.innerHTML = html;

            // 绑定点击事件
            document.querySelectorAll('.dir-item').forEach(item => {
                item.addEventListener('click', () => {
                    const dirPath = item.dataset.path;
                    if (item.classList.contains('dir-up') || item.dataset.has_subdirs === 'true') {
                        // 导航到该目录
                        loadDirectories(dirPath);
                    } else {
                        // 选择该目录
                        selectDirectory(dirPath);
                    }
                });
            });

            // 更新当前路径
            directoryBrowser.currentPath = data.current_path;
        } else {
            elements.directoryList.innerHTML = `<div class="dir-item" style="color: #e74c3c;">${data.error || '加载失败'}</div>`;
        }
    } catch (error) {
        console.error('加载目录失败:', error);
        elements.directoryList.innerHTML = `<div class="dir-item" style="color: #e74c3c;">加载失败：${error.message}</div>`;
    }
}

/**
 * 选择目录
 */
function selectDirectory(path) {
    directoryBrowser.selectedPath = path;

    // 高亮选中项
    document.querySelectorAll('.dir-item').forEach(item => {
        item.style.background = '';
        item.style.borderColor = '';
        if (item.dataset.path === path) {
            item.style.background = '#d4edda';
            item.style.borderColor = '#28a745';
        }
    });
}

/**
 * 确认目录选择
 */
function confirmDirectorySelection() {
    const path = directoryBrowser.selectedPath || directoryBrowser.currentPath;

    if (directoryBrowser.targetInput === 'input') {
        elements.inputDir.value = path;
    } else {
        elements.outputDir.value = path;
    }

    closeModal();
}

/**
 * 关闭模态框
 */
function closeModal() {
    elements.directoryModal.classList.remove('show');
    directoryBrowser.selectedPath = null;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
