/**
 * 双视频同步播放器
 * 实现原视频和骨架视频的同步播放、暂停、拖动、帧级跳转
 */

class VideoPlayer {
    constructor() {
        this.originalVideo = document.getElementById('originalVideo');
        this.skeletonVideo = document.getElementById('skeletonVideo');
        this.playPauseBtn = document.getElementById('playPauseBtn');
        this.timeline = document.getElementById('timeline');
        this.timelineProgress = document.getElementById('timelineProgress');
        this.timelineHandle = document.getElementById('timelineHandle');
        this.currentTimeDisplay = document.getElementById('currentTime');
        this.totalTimeDisplay = document.getElementById('totalTime');
        this.currentFrameDisplay = document.getElementById('currentFrame');
        this.totalFramesDisplay = document.getElementById('totalFrames');
        this.speedDisplay = document.getElementById('speedDisplay');
        
        this.fps = 30; // 默认帧率，稍后从视频元数据更新
        this.totalFrames = 0;
        this.currentSpeed = 1.0;
        this.isDragging = false;
        this.isPlaying = false;
        
        this.init();
    }
    
    init() {
        // 绑定事件监听器
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        
        // 时间轴拖动
        this.timeline.addEventListener('mousedown', (e) => this.startDrag(e));
        document.addEventListener('mousemove', (e) => this.drag(e));
        document.addEventListener('mouseup', () => this.endDrag());
        
        // 视频加载完成
        this.originalVideo.addEventListener('loadedmetadata', () => {
            this.updateMetadata();
        });
        
        // 同步时间更新
        this.originalVideo.addEventListener('timeupdate', () => {
            if (!this.isDragging) {
                this.syncVideoTime();
                this.updateTimeDisplay();
            }
        });
        
        // 播放结束
        this.originalVideo.addEventListener('ended', () => {
            this.isPlaying = false;
            this.playPauseBtn.textContent = '▶ 播放';
        });
        
        // 键盘控制
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        // 隐藏加载提示
        this.originalVideo.addEventListener('canplay', () => {
            console.log('原视频加载成功');
            document.getElementById('originalOverlay').style.display = 'none';
        });
        this.skeletonVideo.addEventListener('canplay', () => {
            console.log('骨架视频加载成功');
            document.getElementById('skeletonOverlay').style.display = 'none';
        });
        
        // 添加错误处理
        this.originalVideo.addEventListener('error', (e) => {
            console.error('原视频加载失败:', e);
            console.error('原视频错误详情:', {
                error: this.originalVideo.error,
                code: this.originalVideo.error?.code,
                message: this.originalVideo.error?.message,
                src: this.originalVideo.querySelector('source')?.src
            });
            const overlay = document.getElementById('originalOverlay');
            overlay.innerHTML = '<span style="color: #ff4444;">❌ 原视频加载失败</span><br><small>请检查视频文件是否存在</small>';
        });
        this.skeletonVideo.addEventListener('error', (e) => {
            console.error('骨架视频加载失败:', e);
            console.error('骨架视频错误详情:', {
                error: this.skeletonVideo.error,
                code: this.skeletonVideo.error?.code,
                message: this.skeletonVideo.error?.message,
                src: this.skeletonVideo.querySelector('source')?.src
            });
            const overlay = document.getElementById('skeletonOverlay');
            overlay.innerHTML = '<span style="color: #ff4444;">❌ 骨架视频加载失败</span><br><small>可能分析尚未完成</small>';
        });
        
        // 添加加载进度日志
        this.originalVideo.addEventListener('loadstart', () => {
            console.log('开始加载原视频');
        });
        this.skeletonVideo.addEventListener('loadstart', () => {
            console.log('开始加载骨架视频');
        });
        
        this.originalVideo.addEventListener('loadeddata', () => {
            console.log('原视频数据加载完成');
        });
        this.skeletonVideo.addEventListener('loadeddata', () => {
            console.log('骨架视频数据加载完成');
        });
    }
    
    updateMetadata() {
        const duration = this.originalVideo.duration;
        this.totalTimeDisplay.textContent = this.formatTime(duration);
        
        if (this.totalFrames > 0 && duration > 0) {
            // 如果总帧数已知（例如从分析数据中获取），则反推FPS
            this.fps = this.totalFrames / duration;
            console.log(`[Player] FPS updated to ${this.fps.toFixed(2)} based on totalFrames ${this.totalFrames}`);
        } else {
            // 估算总帧数（稍后从分析数据更新）
            this.totalFrames = Math.floor(duration * this.fps);
        }
        this.totalFramesDisplay.textContent = this.totalFrames;
    }

    setTotalFrames(frames) {
        this.totalFrames = frames;
        this.totalFramesDisplay.textContent = this.totalFrames;
        
        // 如果视频已加载，立即更新FPS
        if (this.originalVideo.duration > 0) {
            this.fps = this.totalFrames / this.originalVideo.duration;
            console.log(`[Player] FPS updated to ${this.fps.toFixed(2)} (setTotalFrames)`);
        }
    }
    
    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }
    
    play() {
        this.originalVideo.play();
        this.skeletonVideo.play();
        this.isPlaying = true;
        this.playPauseBtn.textContent = '⏸ 暂停';
    }
    
    pause() {
        this.originalVideo.pause();
        this.skeletonVideo.pause();
        this.isPlaying = false;
        this.playPauseBtn.textContent = '▶ 播放';
    }
    
    syncVideoTime() {
        // 确保两个视频时间同步（以原视频为准）
        const diff = Math.abs(this.originalVideo.currentTime - this.skeletonVideo.currentTime);
        if (diff > 0.1) { // 如果偏差超过0.1秒，强制同步
            this.skeletonVideo.currentTime = this.originalVideo.currentTime;
        }
    }
    
    seekToTime(time) {
        this.originalVideo.currentTime = time;
        this.skeletonVideo.currentTime = time;
        this.updateTimeDisplay();
    }
    
    seekToFrame(frameNumber) {
        // Add a small offset (0.1 frame) to ensure we land safely inside the frame
        // and avoid floating point precision issues
        const time = (frameNumber + 0.1) / this.fps;
        this.seekToTime(time);
    }
    
    stepForward() {
        this.pause();
        const nextFrame = this.getCurrentFrame() + 1;
        if (nextFrame < this.totalFrames) {
            this.seekToFrame(nextFrame);
        }
    }
    
    stepBackward() {
        this.pause();
        const prevFrame = this.getCurrentFrame() - 1;
        if (prevFrame >= 0) {
            this.seekToFrame(prevFrame);
        }
    }
    
    getCurrentFrame() {
        // Add a small epsilon to handle precision issues
        return Math.floor(this.originalVideo.currentTime * this.fps + 0.001);
    }
    
    changeSpeed(delta) {
        this.currentSpeed = Math.max(0.25, Math.min(2.0, this.currentSpeed + delta));
        this.originalVideo.playbackRate = this.currentSpeed;
        this.skeletonVideo.playbackRate = this.currentSpeed;
        this.speedDisplay.textContent = this.currentSpeed.toFixed(2) + 'x';
    }
    
    startDrag(e) {
        this.isDragging = true;
        this.pause();
        this.updateTimelinePosition(e);
    }
    
    drag(e) {
        if (this.isDragging) {
            this.updateTimelinePosition(e);
        }
    }
    
    endDrag() {
        this.isDragging = false;
    }
    
    updateTimelinePosition(e) {
        const rect = this.timeline.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        const percentage = x / rect.width;
        
        const newTime = percentage * this.originalVideo.duration;
        this.seekToTime(newTime);
        
        this.timelineProgress.style.width = (percentage * 100) + '%';
        this.timelineHandle.style.left = (percentage * 100) + '%';
    }
    
    updateTimeDisplay() {
        const currentTime = this.originalVideo.currentTime;
        const percentage = (currentTime / this.originalVideo.duration) * 100;
        
        this.currentTimeDisplay.textContent = this.formatTime(currentTime);
        this.timelineProgress.style.width = percentage + '%';
        this.timelineHandle.style.left = percentage + '%';
        
        const currentFrame = this.getCurrentFrame();
        this.currentFrameDisplay.textContent = currentFrame;
        
        // 触发帧更新事件（用于更新指标显示）
        window.dispatchEvent(new CustomEvent('frameUpdate', { detail: { frame: currentFrame } }));
    }
    
    handleKeyboard(e) {
        switch(e.key) {
            case ' ':
                e.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                this.stepBackward();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.stepForward();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.changeSpeed(0.25);
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.changeSpeed(-0.25);
                break;
        }
    }
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    loadVideos(videoId) {
        console.log('开始加载视频，视频ID:', videoId);
        const originalOverlay = document.getElementById('originalOverlay');
        const skeletonOverlay = document.getElementById('skeletonOverlay');
        
        const originalUrl = `/video_file/${videoId}/original`;
        const skeletonUrl = `/video_file/${videoId}/skeleton`;
        
        console.log('原视频URL:', originalUrl);
        console.log('骨架视频URL:', skeletonUrl);
        
        // 确保overlay显示
        originalOverlay.style.display = 'block';
        skeletonOverlay.style.display = 'block';
        originalOverlay.innerHTML = '<span>加载中...</span>';
        skeletonOverlay.innerHTML = '<span>加载中...</span>';
        
        // 添加一次性canplay事件监听器
        const originalCanPlay = () => {
            console.log('原视频canplay事件触发（loadVideos内）');
            originalOverlay.style.display = 'none';
            this.originalVideo.removeEventListener('canplay', originalCanPlay);
        };
        
        const skeletonCanPlay = () => {
            console.log('骨架视频canplay事件触发（loadVideos内）');
            skeletonOverlay.style.display = 'none';
            this.skeletonVideo.removeEventListener('canplay', skeletonCanPlay);
        };
        
        this.originalVideo.addEventListener('canplay', originalCanPlay);
        this.skeletonVideo.addEventListener('canplay', skeletonCanPlay);
        
        // 强制设置preload
        this.originalVideo.preload = 'auto';
        this.skeletonVideo.preload = 'auto';
        
        // 直接在video元素上设置src，不使用source元素
        this.originalVideo.src = originalUrl;
        this.skeletonVideo.src = skeletonUrl;
        
        // 强制加载
        this.originalVideo.load();
        this.skeletonVideo.load();
        
        console.log('视频加载命令已发送');
        console.log('原视频src:', this.originalVideo.src);
        console.log('骨架视频src:', this.skeletonVideo.src);
        console.log('原视频preload:', this.originalVideo.preload);
        console.log('骨架视频preload:', this.skeletonVideo.preload);
        
        // 5秒后如果还在加载，显示提示
        setTimeout(() => {
            if (originalOverlay.style.display !== 'none') {
                console.warn('原视频加载超时（5秒）');
                console.log('原视频状态:', {
                    readyState: this.originalVideo.readyState,
                    networkState: this.originalVideo.networkState,
                    error: this.originalVideo.error,
                    src: this.originalVideo.src,
                    currentSrc: this.originalVideo.currentSrc
                });
                
                // 如果是网络问题，显示提示
                if (this.originalVideo.networkState === 2) { // NETWORK_LOADING
                    originalOverlay.innerHTML = '<span>⏳ 视频加载中...</span><br><small>网络较慢，请等待</small>';
                } else if (this.originalVideo.networkState === 3) { // NETWORK_NO_SOURCE
                    originalOverlay.innerHTML = '<span style="color: #ff4444;">❌ 无视频源</span><br><small>请检查网络连接</small>';
                }
            }
            if (skeletonOverlay.style.display !== 'none') {
                console.warn('骨架视频加载超时（5秒）');
                console.log('骨架视频状态:', {
                    readyState: this.skeletonVideo.readyState,
                    networkState: this.skeletonVideo.networkState,
                    error: this.skeletonVideo.error,
                    src: this.skeletonVideo.src,
                    currentSrc: this.skeletonVideo.currentSrc
                });
                
                // 如果是网络问题，显示提示
                if (this.skeletonVideo.networkState === 2) { // NETWORK_LOADING
                    skeletonOverlay.innerHTML = '<span>⏳ 视频加载中...</span><br><small>网络较慢，请等待</small>';
                } else if (this.skeletonVideo.networkState === 3) { // NETWORK_NO_SOURCE
                    skeletonOverlay.innerHTML = '<span style="color: #ff4444;">❌ 无视频源</span><br><small>分析可能未完成</small>';
                }
            }
        }, 5000);
    }
    
    addKeyframeMarker(frameNumber, label, color = '#ff6b6b') {
        const percentage = (frameNumber / this.totalFrames) * 100;
        
        const marker = document.createElement('div');
        marker.className = 'keyframe-marker';
        marker.style.left = percentage + '%';
        marker.style.backgroundColor = color;
        marker.title = `${label} (帧${frameNumber})`;
        marker.dataset.frame = frameNumber;
        
        marker.addEventListener('click', () => {
            this.seekToFrame(frameNumber);
        });
        
        document.getElementById('keyframeMarkers').appendChild(marker);
    }
    
    clearKeyframeMarkers() {
        document.getElementById('keyframeMarkers').innerHTML = '';
    }
}

// 全局实例
const player = new VideoPlayer();
