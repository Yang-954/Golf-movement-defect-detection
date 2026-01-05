/**
 * 分析页面逻辑
 * 加载分析数据、渲染指标卡片、处理交互
 */

let analysisData = null;
let keyframeData = null;
let metricsStandards = null;
let videoInfo = null;

// 关键帧指标定义映射
const KEYFRAME_METRIC_DEFINITIONS = {
    "shoulder_rot_rel_deg": { name: "metric_shoulder_rot", unit: "°", category: "cat_rotation" },
    "hip_rot_rel_deg": { name: "metric_hip_rot", unit: "°", category: "cat_rotation" },
    "body_tilt_yz_deg": { name: "metric_body_tilt", unit: "°", category: "cat_posture" },
    "hip_dx": { name: "metric_hip_dx", unit: "m", category: "cat_displacement" },
    "shoulder_center_dx": { name: "metric_shoulder_dx", unit: "m", category: "cat_displacement" },
    "left_hand_dx": { name: "metric_left_hand_dx", unit: "m", category: "cat_displacement" },
    "energy_index": { name: "metric_energy_index", unit: "°", category: "cat_energy" },
    "trunk_mid_dy": { name: "metric_trunk_dy", unit: "m", category: "cat_displacement" },
    "shoulder_tilt_deg": { name: "metric_shoulder_tilt", unit: "°", category: "cat_posture" },
    "hip_tilt_deg": { name: "metric_hip_tilt", unit: "°", category: "cat_posture" }
};

// 类别映射
const CATEGORY_MAP = {
    '运动学指标': 'cat_kinematic',
    '旋转指标': 'cat_rotation',
    '姿态指标': 'cat_posture',
    '位移指标': 'cat_displacement',
    '能量指标': 'cat_energy',
    '其他指标': 'cat_other'
};

// 逐帧指标名称映射 (中文 -> 翻译键)
const FRAME_METRIC_MAPPING = {
    "右髋X轴位移": "metric_hip_dx",
    "左手X轴位移": "metric_left_hand_dx",
    "左髋X轴位移": "metric_left_hip_dx",
    "异常指标数_帧级": "metric_abnormal_count",
    "轻微偏差指标数_帧级": "metric_minor_count",
    "肩线与Z轴夹角_左正右负_近端终点_XZ平面": "metric_shoulder_z_angle",
    "肩线与Z轴夹角_度_左正右负_近端终点_XZ平面": "metric_shoulder_z_angle",
    "髋线与Z轴夹角_度_左正右负_近端终点_XZ平面": "metric_hip_z_angle",
    "肩线中心X轴位移": "metric_shoulder_dx",
    "肩线旋转减髋线旋转": "metric_shoulder_hip_diff",
    "肩线旋转减髋线旋转_度": "metric_shoulder_hip_diff",
    "身体平面与Y轴夹角_X轴为0向上为正_0到180": "metric_body_y_angle",
    "身体平面与Y轴夹角_度_X轴为0向上为正_0到180": "metric_body_y_angle",
    "头部X轴位移": "metric_head_dx",
    "头部Y轴位移": "metric_head_dy",
    "脊柱倾角": "metric_spine_angle",
    "左脑X轴位移": "metric_left_head_dx",
    "右脑X轴位移": "metric_right_head_dx",
    // Top Issues中的完整字段名
    "肩线与Z轴夹角": "metric_shoulder_z_angle",
    "髋线与Z轴夹角": "metric_hip_z_angle",
    "肩线旋转减髋线旋转": "metric_shoulder_hip_diff",
    
    // 正面视角指标
    "右髋X轴位移_正面": "metric_右髋X轴位移_正面",
    "左髋X轴位移_正面": "metric_左髋X轴位移_正面",
    "肩线中心X轴位移_正面": "metric_肩线中心X轴位移_正面",
    "躯干中点Y轴位移_正面": "metric_躯干中点Y轴位移_正面",
    "肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面": "metric_肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面",
    "髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面": "metric_髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面",
    "左手X轴位移_正面": "metric_左手X轴位移_正面",
    "右脑X轴位移_正面": "metric_右脑X轴位移_正面",
    "左脑X轴位移_正面": "metric_左脑X轴位移_正面",
    "头部X轴位移_正面": "metric_头部X轴位移_正面",
    "头部Y轴位移_正面": "metric_头部Y轴位移_正面"
};

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

    // 监听语言切换事件
    window.addEventListener('languageChanged', () => {
        // 重新渲染所有视图
        if (analysisData) {
            renderFrameByFrameMetrics();
            if (analysisData.video_summary) {
                renderVideoSummary(analysisData.video_summary, analysisData.ai_feedback);
            }
            // 重新渲染关键帧导航（如果存在）
            if (analysisData.keyframes) {
                renderKeyframeNavigation();
            }
        }
        if (keyframeData) {
            renderKeyframeAnalysis(keyframeData);
        }
        // 更新视频信息区域
        if (videoInfo) {
             document.getElementById('videoInfo').innerHTML = `
                <span><strong>${t('video_id')}:</strong> ${videoInfo.video_id}</span>
                <span><strong>${t('view_angle')}:</strong> ${TranslationHelper.translateViewAngle(videoInfo.view_angle)}</span>
                <span><strong>${t('status')}:</strong> <span class="status-${videoInfo.status}">${TranslationHelper.translateStatus(videoInfo.status)}</span></span>
            `;
        }
    });
    
    // 启动状态检查轮询（无论当前状态如何，都会先检查一次）
    startStatusPolling();
});

// 状态轮询
let statusPollInterval = null;

function startStatusPolling() {
    if (statusPollInterval) return;
    
    // 初始检查，如果已经是 completed 或 failed，则不需要轮询
    fetch(`/videos/${VIDEO_ID}`)
        .then(res => res.json())
        .then(data => {
            const status = data.video.status;
            if (status === 'completed' || status === 'failed') {
                console.log(`当前状态为 ${status}，无需轮询`);
                return;
            }
            
            // 只有在非终态（如 processing, pending）时才启动轮询
            statusPollInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/videos/${VIDEO_ID}`);
                    const data = await response.json();
                    const newStatus = data.video.status;
                    
                    // 更新全局videoInfo
                    if (!videoInfo) {
                        videoInfo = data.video;
                    } else {
                        videoInfo.status = newStatus;
                    }
                    
                    // 更新状态显示
                    if (videoInfo) {
                        document.getElementById('videoInfo').innerHTML = `
                            <span><strong>${t('video_id')}:</strong> ${videoInfo.video_id}</span>
                            <span><strong>${t('view_angle')}:</strong> ${TranslationHelper.translateViewAngle(videoInfo.view_angle)}</span>
                            <span><strong>${t('status')}:</strong> <span class="status-${videoInfo.status}">${TranslationHelper.translateStatus(videoInfo.status)}</span></span>
                        `;
                    }
                    
                    // 如果分析完成，停止轮询并刷新页面
                    if (newStatus === 'completed') {
                        console.log('分析完成，自动刷新页面');
                        clearInterval(statusPollInterval);
                        statusPollInterval = null;
                        window.location.reload();
                    } else if (newStatus === 'failed') {
                        console.log('分析失败，停止轮询');
                        clearInterval(statusPollInterval);
                        statusPollInterval = null;
                    }
                } catch (error) {
                    console.error('状态检查失败:', error);
                }
            }, 3000); // 每3秒检查一次
        })
        .catch(err => console.error('初始状态检查失败:', err));
}

// 加载视频信息
async function loadVideoInfo() {
    try {
        const response = await fetch(`/videos/${VIDEO_ID}`);
        const data = await response.json();
        videoInfo = data.video;
        
        const viewAngleKey = videoInfo.view_angle === '侧面' ? 'angle_side' : 
                           videoInfo.view_angle === '正面' ? 'angle_front' : videoInfo.view_angle;
        
        document.getElementById('videoInfo').innerHTML = `
            <span><strong>${t('video_id')}:</strong> ${videoInfo.video_id}</span>
            <span><strong>${t('view_angle')}:</strong> ${t(viewAngleKey)}</span>
            <span><strong>${t('status')}:</strong> <span class="status-${videoInfo.status}">${TranslationHelper.translateStatus(videoInfo.status)}</span></span>
        `;
        
        player.loadVideos(VIDEO_ID);
        
    } catch (error) {
        console.error('加载视频信息失败:', error);
        alert(t('error_load_failed'));
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
            player.setTotalFrames(frameData.total_frames);
        }
        
        // 添加关键帧标记
        if (frameData.keyframes && frameData.keyframes.events) {
            const events = frameData.keyframes.events;
            const eventNameKeys = ['event_setup', 'event_takeaway', 'event_backswing', 'event_top', 'event_downswing', 'event_impact', 'event_follow_through', 'event_finish'];
            events.forEach((frame, index) => {
                const eventName = t(eventNameKeys[index]) || `${t('keyframe_event')} ${index + 1}`;
                player.addKeyframeMarker(frame, eventName, '#4CAF50');
            });
        }
        
        // 渲染逐帧指标
        renderFrameByFrameMetrics();
        
        // 渲染关键帧导航
        if (frameData.keyframes) {
            renderKeyframeNavigation();
        }
        
        // 渲染视频汇总（同时传入 ai_feedback）
        if (frameData.video_summary) {
            renderVideoSummary(frameData.video_summary, frameData.ai_feedback);
        }

        // 加载关键帧分析数据（优先从 keyframe CSV 获取；若不存在则回退使用 frame_by_frame 提取的 events）
        try {
            const kfResponse = await fetch(`/analysis/${VIDEO_ID}?type=keyframe`);
            if (kfResponse.ok) {
                const kfData = await kfResponse.json();
                keyframeData = kfData;
                renderKeyframeAnalysis(kfData);
            } else {
                console.log('未找到关键帧分析数据，尝试通过后端 keyframe_csv 接口回退获取');
                // 优先尝试直接请求后端导出的 Keyframe_analysis CSV
                try {
                    const viewArg = videoInfo ? videoInfo.view_angle : '侧面';
                    const rawResp = await fetch(`/keyframe_csv/${VIDEO_ID}?view=${encodeURIComponent(viewArg)}`);
                    if (rawResp.ok) {
                        const rawData = await rawResp.json();
                        keyframeData = { data: rawData.data, keyframes: { events: rawData.events } };
                        renderKeyframeAnalysis(keyframeData);
                        return;
                    }
                } catch (e) {
                    console.warn('尝试通过 /keyframe_csv 获取数据失败:', e);
                }
                // 回退：如果 frameData.keyframes 存在，则基于 events 与逐帧数据构建最小 kfData
                if (frameData.keyframes && frameData.keyframes.events) {
                    const events = frameData.keyframes.events;
                    const fallback = { data: [], events: events };

                    // 尝试从逐帧数据中提取与关键帧对应的指标（若逐帧数据包含 event_index 或 帧序号匹配）
                    if (analysisData && analysisData.data && analysisData.data.length > 0) {
                        const grouped = {};
                        analysisData.data.forEach(r => {
                            // 支持两种来源：event_index 或 帧序号
                            const ei = r.event_index || r['event_index'] || null;
                            const abs = r.abs_frame || r['abs_frame'] || r['帧序号'] || r['frame_index'] || null;
                            if (ei != null) {
                                grouped[ei] = grouped[ei] || [];
                                grouped[ei].push(r);
                            } else if (abs != null && events.includes(abs)) {
                                const idx = events.indexOf(abs) + 1; // event_index 从1开始
                                grouped[idx] = grouped[idx] || [];
                                grouped[idx].push(r);
                            }
                        });

                        // 构建宽格式数据（每个事件一行）
                        events.forEach((absFrame, idx) => {
                            const ei = idx + 1;
                            const rows = grouped[ei] || [];
                            const row = { video_id: VIDEO_ID, event_index: ei, abs_frame: absFrame, real_frame: null };
                            if (rows.length > 0) {
                                // 合并第一条记录的字段作为示例值（非严格）
                                const sample = rows[0];
                                Object.keys(sample).forEach(k => {
                                    if (!['video_id','event_index','abs_frame','real_frame'].includes(k)) {
                                        row[k] = sample[k];
                                    }
                                });
                            }
                            fallback.data.push(row);
                        });
                    } else {
                        // 只生成事件列表，指标留空
                        events.forEach((absFrame, idx) => {
                            fallback.data.push({ video_id: VIDEO_ID, event_index: idx+1, abs_frame: absFrame, real_frame: null });
                        });
                    }

                    keyframeData = fallback;
                    renderKeyframeAnalysis(fallback);
                } else {
                    const container = document.getElementById('kfMetricsGrid');
                    if (container) container.innerHTML = '<div class="no-data">暂无关键帧分析数据</div>';
                }
            }
        } catch (e) {
            console.warn('加载关键帧分析数据失败:', e);
            // 同样尝试回退渲染
            if (frameData.keyframes && frameData.keyframes.events) {
                const events = frameData.keyframes.events;
                const fallback = { data: [], events: events };
                events.forEach((absFrame, idx) => {
                    fallback.data.push({ video_id: VIDEO_ID, event_index: idx+1, abs_frame: absFrame, real_frame: null });
                });
                keyframeData = fallback;
                renderKeyframeAnalysis(fallback);
            } else {
                const container = document.getElementById('kfMetricsGrid');
                if (container) container.innerHTML = `<div class="no-data">${t('error_load_failed')}</div>`;
            }
        }
        
    } catch (error) {
        console.error('加载分析数据失败:', error);
        alert(`${t('error_load_failed')}: ${error.message}\n\n${t('error_analysis_not_complete')}`);
    }
}

// 加载指标标准
async function loadMetrics() {
    try {
        const viewAngle = videoInfo ? videoInfo.view_angle : '侧面';
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
            '帧级结论', '帧级异常指标数', '帧级轻微指标数', '帧级结论_连续过滤后', '帧级异常_连续过滤后',
            '异常指标数_帧级', '轻微偏差指标数_帧级'].includes(key)) {
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
    
    // 尝试从 KEYFRAME_METRIC_DEFINITIONS 获取翻译键
    let def = KEYFRAME_METRIC_DEFINITIONS[metricName];
    let translatedName = metricName;

    if (def) {
        translatedName = t(def.name);
    } else {
        // 尝试从 FRAME_METRIC_MAPPING 获取
        const mappingKey = FRAME_METRIC_MAPPING[metricName];
        if (mappingKey) {
            translatedName = t(mappingKey);
        } else {
            // 如果都没有，尝试直接翻译 metricName (虽然不太可能直接匹配)
            translatedName = t(metricName);
        }
    }
    
    // 处理类别翻译
    let category = standard?.category || 'cat_kinematic';
    if (CATEGORY_MAP[category]) {
        category = t(CATEGORY_MAP[category]);
    } else if (category.startsWith('cat_')) {
        category = t(category);
    } else {
        // Fallback for unknown categories
        category = t(category);
    }
    
    const unit = standard?.unit || (def ? def.unit : '');
    const lowerLimit = (standard && standard.lower_limit != null) ? standard.lower_limit.toFixed(2) : '-';
    const upperLimit = (standard && standard.upper_limit != null) ? standard.upper_limit.toFixed(2) : '-';
    
    card.innerHTML = `
        <div class="metric-header">
            <span class="metric-category">${category}</span>
            <span class="metric-status" data-status="standard">${t('status_standard')}</span>
        </div>
        <h4 class="metric-name">${translatedName}</h4>
        <div class="metric-value">
            <span class="value-number">--</span>
            <span class="value-unit">${unit}</span>
        </div>
        <div class="metric-range">
            ${t('standard_range')}: ${lowerLimit} ~ ${upperLimit}
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
    
    // 仅更新逐帧分析的卡片
    const cards = document.querySelectorAll('#metricsGrid .metric-card');
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
        let statusText = t('status_standard');
        
        if (judgment === 2) {
            status = 'abnormal';
            statusText = t('status_abnormal');
            card.classList.add('abnormal');
            card.classList.remove('minor');
        } else if (judgment === 1) {
            status = 'minor';
            statusText = t('status_minor_deviation');
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
        alert(t('alert_no_abnormal'));
    }
}

// 渲染关键帧导航栏
function renderKeyframeNavigation() {
    // 优先使用已加载的 keyframeData（宽格式），否则回退到 analysisData.keyframes.events
    const timeline = document.getElementById('keyframesTimeline');
    if (!timeline) return;
    timeline.innerHTML = '';

    const eventNames = ['event_setup', 'event_takeaway', 'event_backswing', 'event_top', 'event_downswing', 'event_impact', 'event_follow_through', 'event_finish'];

    // 构建用于渲染的项数组：期望项包含 { event_index, abs_frame, defect_count, worst_label }
    let items = [];
    if (keyframeData && keyframeData.data && keyframeData.data.length) {
        items = keyframeData.data.map(r => ({
            event_index: r.event_index || r['event_index'] || null,
            abs_frame: r.abs_frame || r['abs_frame'] || r['帧序号'] || null,
            defect_count: r.defect_count || r['defect_count'] || 0,
            worst_label: r.worst_label || r['worst_label'] || 'normal'
        }));
    } else if (analysisData && analysisData.keyframes && analysisData.keyframes.events) {
        items = analysisData.keyframes.events.map((f, idx) => ({
            event_index: idx + 1,
            abs_frame: f,
            defect_count: 0,
            worst_label: 'normal'
        }));
    } else {
        console.log('未找到关键帧events数据');
        return;
    }

    items.forEach((it, idx) => {
        const eventKey = eventNames[(it.event_index || (idx+1)) - 1];
        const eventName = eventKey ? t(eventKey) : `${t('keyframe_event')} ${it.event_index || (idx+1)}`;
        const absFrame = it.abs_frame;
        const defectCount = it.defect_count || 0;
        const worstLabel = it.worst_label || 'normal';

        let statusClass = 'status-normal';
        if (worstLabel === 'severe_insufficient') statusClass = 'status-severe';
        else if (worstLabel === 'slight_exceed') statusClass = 'status-warning';
        else if (defectCount > 0) statusClass = 'status-warning';

        const navItem = document.createElement('div');
        navItem.className = `keyframe-nav-item ${statusClass}`;
        if (idx === 0) navItem.classList.add('active');

        navItem.innerHTML = `
            <div class="keyframe-nav-label">${eventName}</div>
            <div class="keyframe-nav-frame">${t('frame')} ${absFrame}</div>
            ${defectCount > 0 ? `<div class="keyframe-defect-badge">${defectCount}</div>` : ''}
        `;

        navItem.addEventListener('click', () => {
            // 切换激活样式
            document.querySelectorAll('#keyframesTimeline .keyframe-nav-item').forEach(item => item.classList.remove('active'));
            navItem.classList.add('active');

            // 跳转视频
            if (absFrame != null) {
                player.seekToFrame(absFrame);
                player.pause();
            }

            // 如果加载了 keyframeData，则更新关键帧指标面板
            if (keyframeData && keyframeData.data && keyframeData.data.length) {
                const row = keyframeData.data.find(r => (r.event_index || r['event_index']) == (it.event_index || (idx+1)));
                if (row) updateKeyframeMetrics(row);
            }
        });

        timeline.appendChild(navItem);
    });
}


// 渲染视频汇总
function renderVideoSummary(summary, ai_feedback) {
    const container = document.getElementById('summaryContainer');
    
    const judgment = translateVerdict(summary['视频判定']) || t('unknown');
    const totalFrames = summary['总帧数'] || 0;
    const excellentRate = (summary['优秀帧占比'] * 100).toFixed(1) || 0;
    const standardRate = (summary['标准帧占比'] * 100).toFixed(1) || 0;
    const basicRate = (summary['基本标准帧占比'] * 100).toFixed(1) || 0;
    const abnormalRate = ((summary['不标准帧占比_连续过滤后'] || summary['不标准帧占比'] || 0) * 100).toFixed(1);
    const maxAbnormalContinuous = summary['最长异常连续帧数'] || 0;
    
    // 处理 Top 问题指标的翻译（格式: "指标名称: 数值; 指标名称: 数值"）
    let topIssues = summary['Top问题指标(按异常占比)'] || t('none');
    if (topIssues && topIssues !== t('none') && typeof topIssues === 'string') {
        // 按分号分割，每个部分是 "指标名称: 数值"
        const issues = topIssues.split(/[;；]/).map(s => s.trim()).filter(s => s);
        const translatedIssues = issues.map(issue => {
            // 分离指标名称和数值
            const colonIndex = issue.indexOf(':');
            if (colonIndex > 0) {
                const metricName = issue.substring(0, colonIndex).trim();
                const metricValue = issue.substring(colonIndex + 1).trim();
                
                // 翻译指标名称
                let translatedName = metricName;
                
                // 1. 尝试从 FRAME_METRIC_MAPPING 查找
                if (FRAME_METRIC_MAPPING[metricName]) {
                    translatedName = t(FRAME_METRIC_MAPPING[metricName]);
                } 
                // 2. 尝试反向查找翻译
                else if (typeof translations !== 'undefined' && translations['zh']) {
                    for (const [key, value] of Object.entries(translations['zh'])) {
                        if (value === metricName) {
                            translatedName = t(key);
                            break;
                        }
                    }
                }
                // 3. 尝试通过 FRAME_METRIC_MAPPING 的值来匹配
                else {
                    for (const [cnKey, enKey] of Object.entries(FRAME_METRIC_MAPPING)) {
                        if (cnKey.includes(metricName) || metricName.includes(cnKey)) {
                            translatedName = t(enKey);
                            break;
                        }
                        // 也检查翻译后的值
                        const zhValue = translations['zh']?.[enKey];
                        if (zhValue && (zhValue === metricName || metricName.includes(zhValue))) {
                            translatedName = t(enKey);
                            break;
                        }
                    }
                }
                
                return `${translatedName}: ${metricValue}`;
            }
            // 如果没有冒号，尝试直接翻译
            if (FRAME_METRIC_MAPPING[issue]) {
                return t(FRAME_METRIC_MAPPING[issue]);
            }
            return t(issue);
        });
        topIssues = translatedIssues.join('; ');
    }
    
    const viewAngle = (window.videoInfo && window.videoInfo.view_angle) ? window.videoInfo.view_angle : (videoInfo ? videoInfo.view_angle : '侧面');
    const viewTitleKey = viewAngle === '正面' ? 'summary_view_front' : 'summary_view_side';
    
    container.innerHTML = `
        <div class="summary-header">
            <h2>${t('summary_overall')}</h2>
            <div class="overall-judgment ${(summary['视频判定'] || '').replace(/\s/g, '-')}">
                ${judgment}
            </div>
        </div>
        
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-label">${t('summary_total_frames')}</div>
                <div class="stat-value">${totalFrames}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">${t('summary_excellent_rate')}</div>
                <div class="stat-value">${excellentRate}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">${t('summary_standard_rate')}</div>
                <div class="stat-value">${standardRate}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">${t('summary_abnormal_rate')}</div>
                <div class="stat-value abnormal">${abnormalRate}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">${t('summary_max_continuous')}</div>
                <div class="stat-value">${maxAbnormalContinuous}</div>
            </div>
        </div>
        
        <div class="top-issues">
            <h3>${t('summary_top_issues')}</h3>
            <div class="issue-list">${topIssues}</div>
        </div>

        <div class="ai-feedback-section">
            <h3>${t('summary_ai_feedback')}</h3>
            <div class="ai-feedback-container">
                <div class="ai-feedback-pane">
                    <h4>${t(viewTitleKey)}</h4>
                    <div class="ai-feedback-text" id="aiFeedback${viewAngle === '正面' ? 'Front' : 'Side'}">
                        ${renderAIFeedback(ai_feedback, viewAngle)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderAIFeedback(ai_feedback, viewAngle) {
    if (!ai_feedback || (typeof ai_feedback === 'object' && Object.keys(ai_feedback).length === 0)) {
        return `<div class="no-data">${t('summary_no_ai')}</div>`;
    }
    
    const lang = currentLang || 'zh';
    const content = ai_feedback[lang] || ai_feedback['zh'] || ai_feedback['en'];
    
    if (!content || (typeof content === 'string' && content.trim() === '')) {
        return `<div class="no-data">${t('summary_no_ai')}</div>`;
    }
    
    return content;
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
    return TranslationHelper.translateStatus(status);
}

// 渲染关键帧分析 (滑块状)
function renderKeyframeAnalysis(kfData) {
    const timelineContainer = document.getElementById('kfAnalysisTimeline');
    const metricsContainer = document.getElementById('kfMetricsGrid');
    
    if (!kfData || !kfData.data || kfData.data.length === 0) {
        metricsContainer.innerHTML = `<div class="no-data">${t('no_data')}</div>`;
        return;
    }
    // 如果传入的是长格式（每行一个 metric），则先 pivot 为每个 event 一行的宽格式
    let wideData = [];
    const sampleRow = kfData.data[0];
    const isLongFormat = sampleRow && (sampleRow.metric !== undefined || sampleRow['metric'] !== undefined);

    if (isLongFormat) {
        const grouped = {};
        kfData.data.forEach(r => {
            const ei = r.event_index || r['event_index'] || null;
            if (ei == null) return;
            grouped[ei] = grouped[ei] || { video_id: r.video_id || VIDEO_ID, event_index: ei, abs_frame: r.abs_frame || r['abs_frame'] || null, defect_count: 0, worst_label: 'normal' };
            const metric = r.metric || r['metric'];
            const val = r.value !== undefined ? r.value : r['value'];
            const label = r.label || r['label'] || 'normal';
            const low = r.low_th_q20 || r['low_th_q20'] || r.low_q20 || r['low_q20'];
            const high = r.high_th_q80 || r['high_th_q80'] || r.high_q80 || r['high_q80'];

            grouped[ei][metric] = val;
            grouped[ei][metric + '__label'] = label;
            if (low !== undefined) grouped[ei][metric + '__low_q20'] = low;
            if (high !== undefined) grouped[ei][metric + '__high_q80'] = high;

            // 更新 defect_count 与 worst_label
            if (label === 'severe_insufficient') {
                grouped[ei].worst_label = 'severe_insufficient';
                grouped[ei].defect_count = (grouped[ei].defect_count || 0) + 1;
            } else if (label === 'slight_exceed') {
                if (grouped[ei].worst_label !== 'severe_insufficient') grouped[ei].worst_label = 'slight_exceed';
                grouped[ei].defect_count = (grouped[ei].defect_count || 0) + 1;
            } else if (label !== 'normal') {
                grouped[ei].defect_count = (grouped[ei].defect_count || 0) + 1;
            }
        });

        // 转为数组并按 event_index 排序
        wideData = Object.keys(grouped).map(k => grouped[k]).sort((a, b) => a.event_index - b.event_index);

        // 如果没有 abs_frame 信息，尝试从 kfData.keyframes.events 填充（后端可能单独返回 events 列表）
        if ((!wideData || wideData.length > 0) && kfData.keyframes && Array.isArray(kfData.keyframes.events)) {
            wideData.forEach(w => {
                if (!w.abs_frame) {
                    const ei = w.event_index;
                    const ev = kfData.keyframes.events[ei - 1];
                    if (ev !== undefined) w.abs_frame = ev;
                }
            });
        }
    } else {
        // 已经是宽格式
        wideData = kfData.data.slice().sort((a, b) => (a.event_index || 0) - (b.event_index || 0));
    }

    timelineContainer.innerHTML = '';
    metricsContainer.innerHTML = '';

    const sortedData = wideData;
    const eventNames = ['event_setup', 'event_takeaway', 'event_backswing', 'event_top', 'event_downswing', 'event_impact', 'event_follow_through', 'event_finish'];

    // 1. 渲染时间轴/导航栏
    sortedData.forEach((row, index) => {
        const eventIdx = row.event_index;
        const eventKey = eventNames[eventIdx - 1];
        const eventName = eventKey ? t(eventKey) : `${t('keyframe_event')} ${eventIdx}`;
        const absFrame = row.abs_frame || row['abs_frame'] || row['帧序号'] || null;
        const defectCount = row.defect_count || row['defect_count'] || 0;
        const worstLabel = row.worst_label || row['worst_label'] || 'normal';

        // 状态样式
        let statusClass = 'status-normal';
        if (worstLabel === 'severe_insufficient') statusClass = 'status-severe';
        else if (worstLabel === 'slight_exceed') statusClass = 'status-warning';
        else if (defectCount > 0) statusClass = 'status-warning';

        const navItem = document.createElement('div');
        navItem.className = `keyframe-nav-item ${statusClass}`;
        if (index === 0) navItem.classList.add('active'); // 默认选中第一个

        navItem.innerHTML = `
            <div class="keyframe-nav-label">${eventName}</div>
            <div class="keyframe-nav-frame">${t('frame')} ${absFrame}</div>
            ${defectCount > 0 ? `<div class="keyframe-defect-badge">${defectCount}</div>` : ''}
        `;

        navItem.addEventListener('click', () => {
            // 切换选中状态
            document.querySelectorAll('#kfAnalysisTimeline .keyframe-nav-item').forEach(item => item.classList.remove('active'));
            navItem.classList.add('active');

            // 跳转视频
            player.seekToFrame(absFrame);
            player.pause();

            // 更新指标显示
            updateKeyframeMetrics(row);
        });

        timelineContainer.appendChild(navItem);
    });

    // 如果意外接收到未透视的长格式行（含 metric/value 字段），再做一次后备透视
    if (sortedData.length > 0) {
        const firstKeys = Object.keys(sortedData[0] || {});
        if (firstKeys.includes('metric') || firstKeys.includes('value') || firstKeys.includes('label')) {
            // 后备聚合（与上面透视逻辑重复，容忍不同字段名）
            const grouped2 = {};
            kfData.data.forEach(r => {
                const ei = r.event_index || r['event_index'] || null;
                if (ei == null) return;
                grouped2[ei] = grouped2[ei] || { video_id: r.video_id || VIDEO_ID, event_index: ei, abs_frame: r.abs_frame || r['abs_frame'] || null, defect_count: 0, worst_label: 'normal' };
                const metric = r.metric || r['metric'];
                const val = r.value !== undefined ? r.value : r['value'];
                const label = r.label || r['label'] || 'normal';
                const low = r.low_th_q20 || r['low_th_q20'] || r.low_q20 || r['low_q20'];
                const high = r.high_th_q80 || r['high_th_q80'] || r.high_q80 || r['high_q80'];

                grouped2[ei][metric] = val;
                grouped2[ei][metric + '__label'] = label;
                if (low !== undefined) grouped2[ei][metric + '__low_q20'] = low;
                if (high !== undefined) grouped2[ei][metric + '__high_q80'] = high;

                if (label === 'severe_insufficient') {
                    grouped2[ei].worst_label = 'severe_insufficient';
                    grouped2[ei].defect_count = (grouped2[ei].defect_count || 0) + 1;
                } else if (label === 'slight_exceed') {
                    if (grouped2[ei].worst_label !== 'severe_insufficient') grouped2[ei].worst_label = 'slight_exceed';
                    grouped2[ei].defect_count = (grouped2[ei].defect_count || 0) + 1;
                } else if (label !== 'normal') {
                    grouped2[ei].defect_count = (grouped2[ei].defect_count || 0) + 1;
                }
            });

            let fallbackWide = Object.keys(grouped2).map(k => grouped2[k]).sort((a, b) => a.event_index - b.event_index);
            if ((!fallbackWide || fallbackWide.length > 0) && kfData.keyframes && Array.isArray(kfData.keyframes.events)) {
                fallbackWide.forEach(w => {
                    if (!w.abs_frame) {
                        const ei = w.event_index;
                        const ev = kfData.keyframes.events[ei - 1];
                        if (ev !== undefined) w.abs_frame = ev;
                    }
                });
            }
            // 替换为透视后的数据
            sortedData.length = 0;
            fallbackWide.forEach(x => sortedData.push(x));
        }
        updateKeyframeMetrics(sortedData[0]);
    }
}

// 更新关键帧指标显示
function updateKeyframeMetrics(row) {
    const container = document.getElementById('kfMetricsGrid');
    container.innerHTML = '';

    // 排除非指标列
    const excludeCols = ['video_id', 'event_index', 'abs_frame', 'real_frame', 'defect_count', 'has_defect', 'worst_label', '关键帧名称', '关键帧索引'];
    
    // 提取指标名 (过滤掉 __label 等后缀)
    const metrics = Object.keys(row).filter(k => !k.includes('__') && !excludeCols.includes(k));

    if (metrics.length === 0) {
        container.innerHTML = `<div class="no-data">${t('no_data') || 'No Data'}</div>`;
        return;
    }

    metrics.forEach(metric => {
        const value = row[metric];
        if (value === null || value === undefined || value === 'nan') return;

        const label = row[`${metric}__label`] || 'normal';
        const low = row[`${metric}__low_q20`];
        const high = row[`${metric}__high_q80`];

        // 获取指标定义（中文名、单位、分类）
        const def = KEYFRAME_METRIC_DEFINITIONS[metric] || { name: metric, unit: '', category: 'cat_other' };

        // 状态判定
        let status = 'standard';
        let statusText = t('status_standard');
        let cardClass = '';

        if (label === 'severe_insufficient') {
            status = 'abnormal';
            statusText = t('status_severe_insufficient');
            cardClass = 'abnormal';
        } else if (label === 'slight_exceed') {
            status = 'minor';
            statusText = t('status_slight_exceed');
            cardClass = 'minor';
        }

        // 格式化数值
        const valStr = typeof value === 'number' ? value.toFixed(2) : value;
        const lowStr = (low !== undefined && low !== null) ? Number(low).toFixed(2) : '-';
        const highStr = (high !== undefined && high !== null) ? Number(high).toFixed(2) : '-';

        // 创建卡片
        const card = document.createElement('div');
        card.className = `metric-card ${cardClass}`;
        
        card.innerHTML = `
            <div class="metric-header">
                <span class="metric-category">${t(def.category)}</span>
                <span class="metric-status" data-status="${status}">${statusText}</span>
            </div>
            <h4 class="metric-name">${t(def.name)}</h4>
            <div class="metric-value">
                <span class="value-number">${valStr}</span>
                <span class="value-unit">${def.unit}</span>
            </div>
            <div class="metric-range">
                ${t('standard_range')}: ${lowStr} ~ ${highStr}
            </div>
        `;
        
        container.appendChild(card);
    });
}
