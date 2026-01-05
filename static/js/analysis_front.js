/**
 * 正面分析页面逻辑
 * 加载分析数据、渲染指标卡片、处理交互
 * 专用于正面视角分析
 */

let analysisData = null;
let keyframeData = null;
let metricsStandards = null;
let videoInfo = null;

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    await loadVideoInfo();
    await loadMetrics();
    await loadAnalysisData();
    initTabs();
    
    // 监听帧更新事件
    window.addEventListener('frameUpdate', (e) => {
        updateMetricsForFrame(e.detail.frame);
    });
});

// 加载视频信息
async function loadVideoInfo() {
    try {
        const response = await fetch(`/videos/${VIDEO_ID}`);
        const data = await response.json();
        videoInfo = data.video;
        
        document.getElementById('videoInfo').innerHTML = `
            <span><strong>视频ID:</strong> ${videoInfo.video_id}</span>
            <span><strong>视角:</strong> ${videoInfo.view_angle}</span>
            <span><strong>状态:</strong> <span class="status-${videoInfo.status}">${getStatusText(videoInfo.status)}</span></span>
        `;
        
        // 加载视频
        player.loadVideos(VIDEO_ID);
        
    } catch (error) {
        console.error('加载视频信息失败:', error);
        alert('加载视频信息失败');
    }
}

// 加载分析数据
async function loadAnalysisData() {
    try {
        // 逐帧分析
        const frameResponse = await fetch(`/analysis/${VIDEO_ID}?type=frame_by_frame`);
        if (!frameResponse.ok) {
            const errorData = await frameResponse.json();
            throw new Error(errorData.error || `HTTP ${frameResponse.status}`);
        }
        const frameData = await frameResponse.json();
        analysisData = frameData;
        
        console.log('分析数据加载成功:', {
            总帧数: frameData.total_frames,
            列数: frameData.columns?.length,
            数据行数: frameData.data?.length
        });
        
        // 更新帧数和FPS
        if (frameData.total_frames) {
            player.totalFrames = frameData.total_frames;
            player.totalFramesDisplay.textContent = frameData.total_frames;
        }
        
        // 添加关键帧标记
        if (frameData.keyframes && frameData.keyframes.events) {
            const events = frameData.keyframes.events;
            const eventNames = ['准备', '起摆', '上杆', '顶点', '下杆', '击球瞬间', '送杆', '收杆'];
            events.forEach((frame, index) => {
                player.addKeyframeMarker(frame, eventNames[index] || `关键帧${index}`, '#4CAF50');
            });
        }
        
        // 渲染逐帧指标
        renderFrameByFrameMetrics();
        
        // 渲染关键帧导航
        if (frameData.keyframes) {
            renderKeyframeNavigation();
        }
        
        // 渲染视频汇总
        if (frameData.video_summary) {
            renderVideoSummary(frameData.video_summary);
        }
        
    } catch (error) {
        console.error('加载分析数据失败:', error);
        alert(`加载分析数据失败: ${error.message}\n\n请检查：\n1. 视频是否分析完成\n2. CSV文件是否生成\n3. 浏览器控制台查看详细错误`);
    }
}

// 加载指标标准
async function loadMetrics() {
    try {
        // 强制使用正面视角
        const viewAngle = '正面';
        const response = await fetch(`/metrics?view_angle=${viewAngle}&type=frame_by_frame`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        metricsStandards = await response.json();
        console.log('指标标准加载成功:', metricsStandards?.length || 0, '个指标');
    } catch (error) {
        console.error('加载指标标准失败:', error);
        metricsStandards = []; // 设置为空数组避免undefined
    }
}

// 渲染逐帧指标卡片
function renderFrameByFrameMetrics() {
    if (!analysisData || !analysisData.data || analysisData.data.length === 0) {
        console.error('渲染指标失败: 数据为空', analysisData);
        document.getElementById('metricsGrid').innerHTML = '<div class="error-message">暂无分析数据</div>';
        return;
    }
    
    if (!metricsStandards || metricsStandards.length === 0) {
        console.warn('警告: 指标标准未加载或为空，将无法显示标准范围');
    }
    
    const container = document.getElementById('metricsGrid');
    container.innerHTML = '';
    
    console.log('开始渲染指标卡片, 数据行数:', analysisData.data.length);
    
    // 获取第一帧数据，提取所有指标
    const firstFrame = analysisData.data[0];
    const metrics = [];
    
    for (let key in firstFrame) {
        // 找出原始指标（不含__合规、__超下限等后缀）
        if (!key.includes('__') && !['视频ID', '帧序号', '帧级加权偏差', '帧级评分_0到100', 
            '帧级结论', '帧级异常指标数', '帧级轻微指标数', '帧级结论_连续过滤后', '帧级异常_连续过滤后'].includes(key)) {
            metrics.push(key);
        }
    }
    
    console.log('提取到的指标:', metrics);
    
    // 为每个指标创建卡片
    metrics.forEach(metricName => {
        const standard = metricsStandards?.find(m => m.metric_name === metricName);
        const card = createMetricCard(metricName, standard);
        container.appendChild(card);
    });
    
    console.log(`已渲染 ${metrics.length} 个指标卡片`);
    
    // 初始化第一帧数据
    updateMetricsForFrame(0);
}

// 创建指标卡片
function createMetricCard(metricName, standard) {
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.dataset.metric = metricName;
    
    const category = standard?.category || '运动学指标';
    const unit = standard?.unit || '';
    const lowerLimit = (standard && standard.lower_limit != null) ? standard.lower_limit.toFixed(2) : '-';
    const upperLimit = (standard && standard.upper_limit != null) ? standard.upper_limit.toFixed(2) : '-';
    
    card.innerHTML = `
        <div class="metric-header">
            <span class="metric-category">${category}</span>
            <span class="metric-status" data-status="standard">标准</span>
        </div>
        <h4 class="metric-name">${metricName}</h4>
        <div class="metric-value">
            <span class="value-number">--</span>
            <span class="value-unit">${unit}</span>
        </div>
        <div class="metric-range">
            标准范围: ${lowerLimit} ~ ${upperLimit}
        </div>
        <div class="metric-chart">
            <canvas class="mini-chart"></canvas>
        </div>
    `;
    
    // 点击卡片可以展开详情或跳转到第一个异常帧
    card.addEventListener('click', () => {
        jumpToFirstAbnormalFrame(metricName);
    });
    
    return card;
}

// 更新当前帧的指标显示
function updateMetricsForFrame(frameNumber) {
    if (!analysisData || !analysisData.data) return;
    
    const frameData = analysisData.data.find(d => d['帧序号'] === frameNumber);
    if (!frameData) return;
    
    const cards = document.querySelectorAll('.metric-card');
    cards.forEach(card => {
        const metricName = card.dataset.metric;
        const value = frameData[metricName];
        const judgment = frameData[`${metricName}__审判_0标准1轻微2异常`];
        
        // 更新数值
        const valueNumber = card.querySelector('.value-number');
        if (value !== undefined && value !== null) {
            valueNumber.textContent = typeof value === 'number' ? value.toFixed(2) : value;
        }
        
        // 更新状态
        const statusElement = card.querySelector('.metric-status');
        let status = 'standard';
        let statusText = '标准';
        
        if (judgment === 2) {
            status = 'abnormal';
            statusText = '异常';
            card.classList.add('abnormal');
            card.classList.remove('minor');
        } else if (judgment === 1) {
            status = 'minor';
            statusText = '轻微偏差';
            card.classList.add('minor');
            card.classList.remove('abnormal');
        } else {
            card.classList.remove('abnormal', 'minor');
        }
        
        statusElement.dataset.status = status;
        statusElement.textContent = statusText;
    });
}

// 跳转到指标的第一个异常帧
function jumpToFirstAbnormalFrame(metricName) {
    if (!analysisData || !analysisData.data) return;
    
    const abnormalFrame = analysisData.data.find(d => 
        d[`${metricName}__审判_0标准1轻微2异常`] === 2
    );
    
    if (abnormalFrame) {
        const frameNumber = abnormalFrame['帧序号'];
        player.seekToFrame(frameNumber);
        player.pause();
        
        // 高亮该卡片
        const card = document.querySelector(`.metric-card[data-metric="${metricName}"]`);
        if (card) {
            card.classList.add('highlight');
            setTimeout(() => card.classList.remove('highlight'), 2000);
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    } else {
        alert(`该指标在所有帧中均无异常`);
    }
}

// 渲染关键帧导航栏
function renderKeyframeNavigation() {
    const keyframesInfo = analysisData?.keyframes;
    
    if (!keyframesInfo || !keyframesInfo.events) {
        console.log('未找到关键帧events数据');
        return;
    }
    
    const timeline = document.getElementById('keyframesTimeline');
    if (!timeline) return;
    
    timeline.innerHTML = '';
    
    const events = keyframesInfo.events || [];
    const eventNames = ['准备', '起摆', '上杆', '顶点', '下杆', '击球瞬间', '送杆', '收杆'];
    
    events.forEach((frame, index) => {
        const keyframeDiv = document.createElement('div');
        keyframeDiv.className = 'keyframe-nav-item';
        keyframeDiv.innerHTML = `
            <div class="keyframe-nav-label">${eventNames[index] || `关键帧${index}`}</div>
            <div class="keyframe-nav-frame">帧 ${frame}</div>
        `;
        
        keyframeDiv.addEventListener('click', () => {
            player.seekToFrame(frame);
            player.pause();
            
            // 高亮当前选中
            document.querySelectorAll('.keyframe-nav-item').forEach(item => item.classList.remove('active'));
            keyframeDiv.classList.add('active');
        });
        
        timeline.appendChild(keyframeDiv);
    });
}


// 渲染视频汇总
function renderVideoSummary(summary) {
    const container = document.getElementById('summaryContainer');
    
    const judgment = summary['视频判定'] || '未评定';
    const totalFrames = summary['总帧数'] || 0;
    const excellentRate = (summary['优秀帧占比'] * 100).toFixed(1) || 0;
    const standardRate = (summary['标准帧占比'] * 100).toFixed(1) || 0;
    const basicRate = (summary['基本标准帧占比'] * 100).toFixed(1) || 0;
    // 修复：使用正确的字段名 '不标准帧占比_连续过滤后'
    const abnormalRate = ((summary['不标准帧占比_连续过滤后'] || summary['不标准帧占比'] || 0) * 100).toFixed(1);
    const maxAbnormalContinuous = summary['最长异常连续帧数'] || 0;
    const topIssues = summary['Top问题指标(按异常占比)'] || '无';
    
    container.innerHTML = `
        <div class="summary-header">
            <h2>视频整体评估 (正面)</h2>
            <div class="overall-judgment ${judgment.replace(/\s/g, '-')}">
                ${judgment}
            </div>
        </div>
        
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-label">总帧数</div>
                <div class="stat-value">${totalFrames}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">优秀帧占比</div>
                <div class="stat-value">${excellentRate}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">标准帧占比</div>
                <div class="stat-value">${standardRate}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">不标准帧占比</div>
                <div class="stat-value abnormal">${abnormalRate}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">最长异常连续帧</div>
                <div class="stat-value">${maxAbnormalContinuous}</div>
            </div>
        </div>
        
        <div class="top-issues">
            <h3>主要问题指标</h3>
            <div class="issue-list">${topIssues}</div>
        </div>
    `;
}

// 标签切换
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // 切换激活状态
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`${tabName}Tab`).classList.add('active');
        });
    });
}

// 辅助函数
function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'processing': '分析中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}
