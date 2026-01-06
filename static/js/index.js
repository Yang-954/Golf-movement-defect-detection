/**
 * 首页逻辑 - 视频上传和列表
 */

// 全局配置变量
let systemConfig = {
    max_videos_retained: 10,
    max_uploads_per_hour: 5
};

document.addEventListener('DOMContentLoaded', () => {
    loadSystemConfig();
    initUploadForm();
    initFileInput();
    loadVideos();
    
    // 监听语言切换事件，重新加载列表以更新文本
    window.addEventListener('languageChanged', () => {
        loadVideos();
        updateConfigDisplay();
    });
    
    // 启动视频状态轮询
    startVideoStatusPolling();
});

// 加载系统配置
async function loadSystemConfig() {
    try {
        const response = await fetch('/config');
        const config = await response.json();
        systemConfig = config;
        updateConfigDisplay();
        // 初始化上传次数显示
        updateRemainingUploads(config.max_uploads_per_hour);
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

// 更新配置显示
function updateConfigDisplay() {
    const maxVideosElement = document.getElementById('maxVideosRetained');
    const maxUploadsElement = document.getElementById('maxUploads');
    
    if (maxVideosElement) {
        maxVideosElement.textContent = systemConfig.max_videos_retained;
    }
    if (maxUploadsElement) {
        maxUploadsElement.textContent = systemConfig.max_uploads_per_hour;
    }
}

// 更新剩余上传次数
function updateRemainingUploads(remaining) {
    const remainingElement = document.getElementById('remainingUploads');
    if (remainingElement) {
        remainingElement.textContent = remaining;
        // 根据剩余次数改变颜色
        if (remaining <= 0) {
            remainingElement.style.color = '#f44336'; // 红色
        } else if (remaining <= 2) {
            remainingElement.style.color = '#ff9800'; // 橙色
        } else {
            remainingElement.style.color = '#4CAF50'; // 绿色
        }
    }
}

// 视频状态轮询
let videoStatusPollInterval = null;
let previousVideosState = {}; // Store previous state: { video_id: status }

function startVideoStatusPolling() {
    if (videoStatusPollInterval) return;
    
    videoStatusPollInterval = setInterval(async () => {
        try {
            const response = await fetch('/videos');
            const videos = await response.json();
            
            let shouldRefresh = false;
            let hasProcessing = false;
            const currentVideosState = {};
            
            // Check if this is the first poll (previous state is empty)
            const isFirstPoll = Object.keys(previousVideosState).length === 0;

            // Check for count changes (new videos added/deleted)
            if (!isFirstPoll && videos.length !== Object.keys(previousVideosState).length) {
                shouldRefresh = true;
            }

            for (const v of videos) {
                currentVideosState[v.video_id] = v.status;
                
                if (v.status === 'processing') {
                    hasProcessing = true;
                }

                // If status changed from what we knew
                if (!isFirstPoll && previousVideosState[v.video_id] && previousVideosState[v.video_id] !== v.status) {
                    shouldRefresh = true;
                }
            }

            // Update state
            previousVideosState = currentVideosState;
            
            if (shouldRefresh) {
                console.log('视频状态发生变化，刷新列表...');
                loadVideos();
            }

            if (!hasProcessing && videoStatusPollInterval) {
                // 如果没有正在处理的视频，停止轮询
                clearInterval(videoStatusPollInterval);
                videoStatusPollInterval = null;
            }
        } catch (error) {
            console.error('状态检查失败:', error);
        }
    }, 2000); // Check every 2 seconds for better responsiveness
}

// 初始化文件输入显示
function initFileInput() {
    const fileInput = document.getElementById('videoFile');
    const fileName = document.getElementById('fileName');
    
    if (fileInput && fileName) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                fileName.textContent = file.name;
            } else {
                fileName.textContent = t('file_no_selected');
            }
        });
    }
}

// 初始化上传表单
function initUploadForm() {
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('videoFile');
    const uploadBtn = document.getElementById('uploadBtn');
    const progressContainer = document.getElementById('uploadProgress');
    const resultDiv = document.getElementById('uploadResult');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            alert(t('alert_select_file'));
            return;
        }
        
        // 检查文件大小
        const maxSize = 500 * 1024 * 1024; // 500MB
        if (file.size > maxSize) {
            alert(t('alert_file_too_large'));
            return;
        }
        
        const formData = new FormData(form);
        
        // 显示上传进度
        uploadBtn.disabled = true;
        uploadBtn.querySelector('.btn-text').style.display = 'none';
        uploadBtn.querySelector('.spinner').style.display = 'inline';
        progressContainer.style.display = 'block';
        resultDiv.innerHTML = '';
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // 更新剩余上传次数
                if (data.remaining_uploads !== undefined) {
                    updateRemainingUploads(data.remaining_uploads);
                }
                
                resultDiv.innerHTML = `
                    <div class="success-message">
                        <strong>✓ ${t('upload_success')}</strong><br>
                        ${t('video_id')}: ${data.video_id}<br>
                    </div>
                `;
                
                // 重置表单
                form.reset();
                const fileName = document.getElementById('fileName');
                if (fileName) {
                    fileName.textContent = t('file_no_selected');
                }
                
                // 启动状态轮询
                startVideoStatusPolling();
            } else {
                throw new Error(data.error || t('upload_failed'));
            }
        } catch (error) {
            resultDiv.innerHTML = `
                <div class="error-message">
                    <strong>✗ ${t('upload_failed')}</strong><br>
                    ${error.message}
                </div>
            `;
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.querySelector('.btn-text').style.display = 'inline';
            uploadBtn.querySelector('.spinner').style.display = 'none';
            progressContainer.style.display = 'none';
        }
    });
}

// 加载视频列表
async function loadVideos() {
    const container = document.getElementById('videoList');
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    if (deleteBtn) deleteBtn.style.display = 'none'; // Reset delete button
    
    container.innerHTML = `<div class="loading">${t('loading')}</div>`;
    
    try {
        const response = await fetch('/videos');
        const videos = await response.json();
        
        if (videos.length === 0) {
            container.innerHTML = `<div class="empty-state">${t('no_videos')}</div>`;
            return;
        }
        
        container.innerHTML = '';
        videos.forEach(video => {
            const card = createVideoCard(video);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('加载视频列表失败:', error);
        container.innerHTML = `<div class="error-message">${t('error_load_failed')}</div>`;
    }
}

let isManagementMode = false;

function toggleManagementMode() {
    isManagementMode = !isManagementMode;
    const container = document.getElementById('videoList');
    const manageBtn = document.getElementById('manageBtn');
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    
    if (isManagementMode) {
        container.classList.add('management-mode');
        if (manageBtn) manageBtn.classList.add('active');
        if (selectAllBtn) selectAllBtn.style.display = 'inline-block';
        updateSelectAllButtonState(); // Initialize state
    } else {
        container.classList.remove('management-mode');
        if (manageBtn) manageBtn.classList.remove('active');
        
        // 取消所有选中
        const checkboxes = document.querySelectorAll('.video-checkbox');
        checkboxes.forEach(cb => cb.checked = false);
        
        // 隐藏按钮
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (selectAllBtn) selectAllBtn.style.display = 'none';
    }
}

function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.video-checkbox');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const isAllSelected = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(cb => cb.checked = !isAllSelected);
    updateDeleteButtonState();
}

function updateSelectAllButtonState() {
    const checkboxes = document.querySelectorAll('.video-checkbox');
    const selectAllBtn = document.getElementById('selectAllBtn');
    if (!selectAllBtn || checkboxes.length === 0) return;
    
    const isAllSelected = Array.from(checkboxes).every(cb => cb.checked);
    const span = selectAllBtn.querySelector('span');
    
    if (isAllSelected) {
        if (span) span.textContent = t('deselect_all');
        selectAllBtn.setAttribute('data-state', 'deselect');
    } else {
        if (span) span.textContent = t('select_all');
        selectAllBtn.setAttribute('data-state', 'select');
    }
}

// 创建视频卡片
function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-card';
    
    const statusClass = video.status === 'completed' ? 'status-completed' : 
                       video.status === 'processing' ? 'status-processing' : 
                       video.status === 'failed' ? 'status-failed' : 'status-pending';
    
    const statusText = getStatusText(video.status);
    const uploadTime = new Date(video.upload_time).toLocaleString(currentLang === 'zh' ? 'zh-CN' : 'en-US');
    
    const viewAngleTranslated = TranslationHelper.translateViewAngle(video.view_angle);

    // 缩略图处理
    let thumbnailHtml = `
        <div class="thumbnail-placeholder">
            🎥
        </div>
    `;
    
    if (video.thumbnail_path) {
        thumbnailHtml = `<img src="${video.thumbnail_path}" alt="${video.original_filename}" class="video-thumb-img">`;
    }

    card.innerHTML = `
        <div class="video-select">
            <input type="checkbox" class="video-checkbox" value="${video.video_id}" onchange="updateDeleteButtonState()">
        </div>
        <div class="video-thumbnail">
            ${thumbnailHtml}
            <span class="status-badge ${statusClass}">${statusText}</span>
        </div>
        <div class="video-info">
            <h3 title="${video.original_filename}">${video.original_filename}</h3>
            <div class="video-meta">
                <span><strong>${t('video_id')}:</strong> ${video.video_id}</span>
                <span><strong>${t('view_angle')}:</strong> ${viewAngleTranslated}</span>
                <span><strong>${t('upload_time')}:</strong> ${uploadTime}</span>
                ${video.total_frames ? `<span><strong>${t('total_frames')}:</strong> ${video.total_frames}</span>` : ''}
            </div>
        </div>
        <div class="video-actions">
            ${video.status === 'completed' ? 
                `<button class="btn-primary" onclick="viewAnalysis('${video.video_id}')">${t('view_report')}</button>` :
                `<button class="btn-secondary" disabled>${statusText}</button>`
            }
        </div>
    `;
    
    return card;
}

// 更新删除按钮状态
function updateDeleteButtonState() {
    const checkboxes = document.querySelectorAll('.video-checkbox:checked');
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    
    updateSelectAllButtonState(); // Update select all button state as well
    
    if (deleteBtn) {
        deleteBtn.style.display = checkboxes.length > 0 ? 'inline-block' : 'none';
        // 更新按钮文本显示选中数量
        const textSpan = deleteBtn.querySelector('span');
        if (textSpan) {
            textSpan.textContent = checkboxes.length > 0 ? `${t('delete_selected')} (${checkboxes.length})` : t('delete_selected');
        }
    }
}

// 删除选中的视频
async function deleteSelectedVideos() {
    const checkboxes = document.querySelectorAll('.video-checkbox:checked');
    const videoIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (videoIds.length === 0) return;
    
    if (!confirm(t('confirm_delete', {count: videoIds.length}))) {
        return;
    }
    
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = '...';
    
    try {
        const response = await fetch('/videos/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ video_ids: videoIds })
        });
        
        const result = await response.json();
        
        if (response.ok || response.status === 207) {
            // 刷新列表
            loadVideos();
            if (result.errors && result.errors.length > 0) {
                alert(t('delete_partial_error') + '\n' + result.errors.join('\n'));
            }
        } else {
            alert(t('delete_failed') + ': ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert(t('delete_failed'));
    } finally {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
    }
}

// 查看分析结果
function viewAnalysis(videoId) {
    window.location.href = `/analysis_page/${videoId}`;
}

// 辅助函数
function getStatusText(status) {
    const statusMap = {
        'pending': t('status_pending'),
        'processing': t('status_processing'),
        'completed': t('status_completed'),
        'failed': t('status_failed')
    };
    return statusMap[status] || status;
}
