/**
 * 图片压缩工具 - Vue 3 前端应用
 */
const { createApp, ref, reactive, computed, onMounted, nextTick, watch } = Vue;

createApp({
    setup() {
        // 配置状态
        const config = reactive({
            input_dir: '/photos',
            output_dir: '/output',
            jobs: 4,
            prefix: 'DSC',
            no_skip: false
        });

        // 运行状态
        const isRunning = ref(false);
        const statusText = computed(() => isRunning.value ? '压缩中...' : '空闲');

        // 进度数据
        const progress = reactive({
            is_running: false,
            total_files: 0,
            processed_count: 0,
            success_count: 0,
            failed_count: 0,
            percentage: 0
        });

        // 日志列表
        const logs = ref([]);
        const logContainer = ref(null);

        // 模态框状态
        const modal = reactive({
            show: false,
            target: null,  // 'input' or 'output'
            currentPath: '',
            parentPath: null,
            canGoUp: false,
            selectedPath: null,
            directories: []
        });

        // SSE 连接
        let logSource = null;
        let progressSource = null;

        // 滚动日志到底部
        const scrollToBottom = async () => {
            await nextTick();
            if (logContainer.value) {
                logContainer.value.scrollTop = logContainer.value.scrollHeight;
            }
        };

        // 获取日志类型样式
        const getLogClass = (log) => {
            if (log.includes('✅')) return 'success';
            if (log.includes('❌')) return 'error';
            if (log.includes('⚠️') || log.includes('⏹️')) return 'warning';
            if (log.includes('⏭️')) return 'info';
            return '';
        };

        // 检查当前状态
        const checkStatus = async () => {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                if (data.status === 'running' && data.progress) {
                    Object.assign(progress, data.progress);
                    isRunning.value = true;
                    startSSEListeners();
                }
            } catch (error) {
                console.error('检查状态失败:', error);
            }
        };

        // 开始压缩
        const startCompression = async () => {
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
                    body: JSON.stringify({ ...config })
                });

                const data = await response.json();
                if (data.success) {
                    logs.value.push('▶️ 压缩任务已启动');
                    isRunning.value = true;
                    startSSEListeners();
                    await scrollToBottom();
                } else {
                    alert(data.message || '启动失败');
                }
            } catch (error) {
                console.error('启动压缩失败:', error);
                alert('启动压缩失败：' + error.message);
            }
        };

        // 停止压缩
        const stopCompression = async () => {
            try {
                const response = await fetch('/api/stop', {
                    method: 'POST'
                });
                const data = await response.json();
                if (data.success) {
                    logs.value.push('⏹️ 已发送停止信号');
                    await scrollToBottom();
                }
            } catch (error) {
                console.error('停止压缩失败:', error);
            }
        };

        // 从日志中解析进度信息（仅更新进度条，不更新成功/失败计数）
        const parseProgressFromLog = (log) => {
            // 匹配格式：[数字/数字]
            const match = log.match(/\[(\d+)\/(\d+)\]/);
            if (match) {
                const current = parseInt(match[1]);
                const total = parseInt(match[2]);
                if (total > 0) {
                    progress.processed_count = current;
                    progress.total_files = total;
                    progress.percentage = Math.round(current / total * 1000) / 10;
                }
            }
            // 成功/失败计数完全依赖 SSE 进度接口，不再从日志解析
        };

        // 启动 SSE 监听
        const startSSEListeners = () => {
            // 关闭旧的连接
            if (logSource) logSource.close();
            if (progressSource) progressSource.close();

            // 监听日志
            logSource = new EventSource('/api/logs');
            logSource.onmessage = (event) => {
                if (event.data === '__END__') {
                    logSource.close();
                    // 任务完成，重置状态
                    isRunning.value = false;
                    return;
                }
                logs.value.push(event.data);
                // 从日志中解析进度
                parseProgressFromLog(event.data);
                scrollToBottom();
            };
            logSource.onerror = () => {
                console.error('日志 SSE 连接错误');
                logSource.close();
            };

            // 监听进度 - 作为主要方案
            progressSource = new EventSource('/api/progress');
            progressSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // 直接使用 SSE 进度数据
                    progress.is_running = data.is_running;
                    progress.total_files = data.total_files;
                    progress.processed_count = data.processed_count;
                    progress.success_count = data.success_count;
                    progress.failed_count = data.failed_count;
                    progress.percentage = data.percentage;

                    // 当任务不再运行时，重置状态
                    if (!data.is_running && isRunning.value) {
                        isRunning.value = false;
                        progressSource.close();
                        logSource.close();
                    }
                } catch (e) {
                    console.error('解析进度失败:', e);
                }
            };
            progressSource.onerror = () => {
                console.error('进度 SSE 连接错误');
            };
        };

        // 打开目录浏览器
        const openDirectoryBrowser = async (target) => {
            modal.target = target;
            modal.selectedPath = null;
            modal.currentPath = target === 'input' ? config.input_dir : config.output_dir;
            modal.show = true;
            await loadDirectories(modal.currentPath);
        };

        // 加载目录列表
        const loadDirectories = async (path) => {
            try {
                const response = await fetch(`/api/directories?path=${encodeURIComponent(path)}`);
                const data = await response.json();
                if (data.success) {
                    modal.currentPath = data.current_path;
                    modal.parentPath = data.parent_path;
                    modal.canGoUp = data.can_go_up;
                    modal.directories = data.directories;
                } else {
                    modal.directories = [];
                }
            } catch (error) {
                console.error('加载目录失败:', error);
                modal.directories = [];
            }
        };

        // 选择或导航到目录
        const selectOrNavigate = (dir) => {
            if (dir.has_subdirs) {
                // 有子目录，导航进去
                loadDirectories(dir.path);
            } else {
                // 没有子目录，选中它
                modal.selectedPath = dir.path;
            }
        };

        // 导航到指定路径
        const navigateTo = (path) => {
            loadDirectories(path);
        };

        // 确认目录选择
        const confirmDirectory = () => {
            const path = modal.selectedPath || modal.currentPath;
            if (modal.target === 'input') {
                config.input_dir = path;
            } else {
                config.output_dir = path;
            }
            closeModal();
        };

        // 关闭模态框
        const closeModal = () => {
            modal.show = false;
            modal.selectedPath = null;
        };

        // 挂载时初始化
        onMounted(() => {
            checkStatus();
        });

        return {
            config,
            isRunning,
            statusText,
            progress,
            logs,
            logContainer,
            modal,
            getLogClass,
            startCompression,
            stopCompression,
            openDirectoryBrowser,
            closeModal,
            loadDirectories,
            selectOrNavigate,
            navigateTo,
            confirmDirectory
        };
    }
}).mount('#app');
