/**
 * Internationalization (i18n) support
 */

// 主翻译资源
const translations = {
    'zh': {
        // Common
        'app_title': '高尔夫挥杆分析系统',
        'header_title': '🏌️ 高尔夫挥杆动作缺陷检测与分析系统',
        'header_subtitle': 'Golf Swing Defect Detection & Analysis System',
        'loading': '加载中...',
        'processing': '⏳ 处理中...',
        'uploading': '上传中...',
        'back': '← 返回',
        
        // Index Page
        'upload_video': '上传视频',
        'select_video': '选择视频文件',
        'supported_formats': '支持格式: MP4, AVI, MOV, MKV | 最大500MB',
        'view_angle': '视角类型',
        'angle_side': '侧面',
        'angle_front': '正面',
        'start_upload': '开始上传并分析',
        'alert_select_file': '请选择视频文件',
        'alert_file_too_large': '文件过大，请选择小于500MB的视频',
        'upload_success': '上传成功，正在分析...',
        'upload_failed': '上传失败',
        'analysis_complete': '分析完成',
        'view_report': '查看报告',
        'video_list': '历史记录',
        'no_videos': '暂无分析记录',
        'delete': '删除',
        'delete_selected': '删除选中',
        'delete_failed': '删除失败',
        'delete_partial_error': '部分删除失败',
        'confirm_delete': '确定要删除选中的 {count} 个视频吗？',
        'file_no_selected': '未选择文件',
        'browse': '浏览...',
        'upload_time': '上传时间',
        'total_frames': '总帧数',
        'error_load_failed': '加载失败',
        'manage': '管理',
        'refresh': '刷新',
        
        // Analysis Page
        'analysis_results': '视频分析结果',
        'analysis_results_front': '视频分析结果 (正面)',
        'video_id': '视频ID',
        'status': '状态',
        'original_video': '原始视频',
        'skeleton_video': '关键点骨架视频',
        'play': '▶ 播放',
        'pause': '⏸ 暂停',
        'step_back': '⏮ 后退',
        'step_fwd': '⏭ 前进',
        'slower': '🐌 减速',
        'faster': '🐇 加速',
        'frame': '帧',
        
        // Tabs
        'tab_frame': '逐帧分析',
        'tab_keyframe': '关键帧分析',
        'tab_summary': '视频汇总',
        
        // Status
        'status_pending': '等待中',
        'status_processing': '处理中',
        'status_completed': '已完成',
        'status_failed': '失败',

        // Analysis Content
        'current_value': '当前值',
        'standard_range': '标准范围',
        'defect_detected': '发现缺陷',
        'normal': '正常',
        'unknown': '未知',
        'score': '得分',
        'suggestion': '建议',
        'keyframe_event': '关键帧事件',
        
        // Keyframe Events
        'event_setup': '准备',
        'event_takeaway': '起摆',
        'event_backswing': '上杆',
        'event_top': '顶点',
        'event_downswing': '下杆',
        'event_impact': '击球瞬间',
        'event_follow_through': '送杆',
        'event_finish': '收杆',

        // Metrics Categories
        'cat_kinematic': '运动学指标',
        'cat_rotation': '旋转指标',
        'cat_posture': '姿态指标',
        'cat_displacement': '位移指标',
        'cat_energy': '能量指标',
        'cat_other': '其他指标',

        // Metric Status
        'status_severe_insufficient': '严重不足',
        'status_slight_exceed': '略微超标',
        'status_minor_deviation': '轻微偏差',
        'status_abnormal': '异常',
        'status_standard': '标准',

        // Summary
        'summary_overall': '视频整体评估',
        'summary_total_frames': '总帧数',
        'summary_excellent_rate': '优秀帧占比',
        'summary_standard_rate': '标准帧占比',
        'summary_abnormal_rate': '不标准帧占比',
        'summary_max_continuous': '最长异常连续帧',
        'summary_top_issues': '主要问题指标',
        'summary_ai_feedback': '优化建议和分析',
        'summary_view_front': '正面视角',
        'summary_view_side': '侧面视角',
        'summary_no_ai': '暂无 AI 建议',

        // Metric Names
        'metric_shoulder_rot': '肩线旋转(相对)',
        'metric_hip_rot': '髋线旋转(相对)',
        'metric_body_tilt': '身体前倾角',
        'metric_hip_dx': '髋部X位移',
        'metric_shoulder_dx': '肩部中心X位移',
        'metric_left_hand_dx': '左手X位移',
        'metric_energy_index': '能量指数(X-Factor)',
        'metric_trunk_dy': '躯干中心Y位移',
        'metric_shoulder_tilt': '肩线倾斜角',
        'metric_hip_tilt': '髋线倾斜角',
        
        // Frame-by-Frame Metrics
        'metric_left_hip_dx': '左髋X轴位移',
        'metric_abnormal_count': '异常指标数(帧级)',
        'metric_minor_count': '轻微偏差指标数(帧级)',
        'metric_shoulder_z_angle': '肩线与Z轴夹角',
        'metric_hip_z_angle': '髋线与Z轴夹角',
        'metric_shoulder_hip_diff': '肩线旋转减髋线旋转',
        'metric_body_y_angle': '身体平面与Y轴夹角',
        'metric_head_dx': '头部X轴位移',
        'metric_head_dy': '头部Y轴位移',
        'metric_spine_angle': '脊柱倾角',
        'metric_left_head_dx': '左脑X轴位移',
        'metric_right_head_dx': '右脑X轴位移',

        'alert_no_abnormal': '该指标在所有帧中均无异常',
        'no_data': '暂无数据',
        'none': '无',
        
        // Additional Metrics - Side View
        'metric_右髋X轴位移': '右髋X轴位移',
        'metric_左手X轴位移': '左手X轴位移',
        'metric_左髋X轴位移': '左髋X轴位移',
        'metric_右脑X轴位移': '右脑X轴位移',
        'metric_肩线与Z轴夹角_左正右负_近端终点_XZ平面': '肩线与Z轴夹角',
        'metric_肩线与Z轴夹角_度_左正右负_近端终点_XZ平面': '肩线与Z轴夹角',
        'metric_髋线与Z轴夹角_度_左正右负_近端终点_XZ平面': '髋线与Z轴夹角',
        'metric_肩线中心X轴位移': '肩线中心X轴位移',
        'metric_肩线旋转减髋线旋转_度': '肩线旋转减髋线旋转',
        'metric_身体平面与Y轴夹角_X轴为0向上为正_0到180': '身体平面与Y轴夹角',
        'metric_身体平面与Y轴夹角_度_X轴为0向上为正_0到180': '身体平面与Y轴夹角',
        'metric_头部X轴位移': '头部X轴位移',
        'metric_头部Y轴位移': '头部Y轴位移',
        'metric_脊柱倾角': '脊柱倾角',
        'metric_异常指标数_帧级': '异常指标数(帧级)',
        'metric_轻微偏差指标数_帧级': '轻微偏差指标数(帧级)',
        
        // Front View Metrics
        'metric_右髋X轴位移_正面': '右髋X轴位移',
        'metric_左髋X轴位移_正面': '左髋X轴位移',
        'metric_肩线中心X轴位移_正面': '肩线中心X轴位移',
        'metric_躯干中点Y轴位移_正面': '躯干中点Y轴位移',
        'metric_肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面': '肩线旋转角',
        'metric_髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面': '髋线旋转角',
        'metric_左手X轴位移_正面': '左手X轴位移',
        'metric_右脑X轴位移_正面': '右脑X轴位移',
        'metric_左脑X轴位移_正面': '左脑X轴位移',
        'metric_头部X轴位移_正面': '头部X轴位移',
        'metric_头部Y轴位移_正面': '头部Y轴位移',
        
        // Verdict Results
        'verdict_优秀': '优秀',
        'verdict_标准': '标准',
        'verdict_基本标准': '基本标准',
        'verdict_不标准': '不标准',
        'verdict_严重不标准': '严重不标准',
        
        // Frame Conclusions
        'conclusion_优秀': '优秀',
        'conclusion_标准': '标准',
        'conclusion_基本标准': '基本标准',
        'conclusion_不标准': '不标准',
        'conclusion_连续不标准': '连续不标准',
        
        // Label Types
        'label_normal': '正常',
        'label_slight_exceed': '略微超标',
        'label_severe_insufficient': '严重不足',
        
        // Error Messages
        'error_video_not_found': '视频未找到',
        'error_analysis_not_complete': '分析尚未完成',
        'error_load_failed': '加载失败',
        'error_network': '网络错误',
        
        // UI Elements
        'btn_refresh': '刷新',
        'btn_delete': '删除',
        'btn_reanalyze': '重新分析',
        'confirm_title': '确认操作',
        'upload_time': '上传时间',
        'total_frames': '总帧数',
        'video_not_supported': '您的浏览器不支持视频播放',
        'playback_error': '视频播放错误',
        'loading_video': '加载中...',
        'ai_feedback_label': 'AI分析内容（原始语言）',
        'ai_feedback_en': 'AI分析内容（英文翻译）',
        'select_all': '全选',
        'deselect_all': '取消全选',
    },
    'en': {
        // Common
        'app_title': 'Golf Swing Analysis System',
        'header_title': '🏌️ Golf Swing Defect Detection & Analysis System',
        'header_subtitle': 'Golf Swing Defect Detection & Analysis System',
        'loading': 'Loading...',
        'processing': '⏳ Processing...',
        'uploading': 'Uploading...',
        'back': '← Back',
        
        // Index Page
        'upload_video': 'Upload Video',
        'select_video': 'Select Video File',
        'supported_formats': 'Supported formats: MP4, AVI, MOV, MKV | Max 500MB',
        'view_angle': 'View Angle',
        'angle_side': 'Down the Line (Side)',
        'angle_front': 'Face On (Front)',
        'start_upload': 'Start Upload & Analysis',
        'alert_select_file': 'Please select a video file',
        'alert_file_too_large': 'File too large, please select a video smaller than 500MB',
        'upload_success': 'Upload successful, analyzing...',
        'upload_failed': 'Upload failed',
        'analysis_complete': 'Analysis Complete',
        'view_report': 'View Report',
        'video_list': 'History',
        'no_videos': 'No analysis history',
        'delete': 'Delete',
        'delete_selected': 'Delete Selected',
        'delete_failed': 'Delete Failed',
        'delete_partial_error': 'Partial Delete Failed',
        'confirm_delete': 'Are you sure you want to delete {count} selected videos?',
        'file_no_selected': 'No file selected',
        'browse': 'Browse...',
        'upload_time': 'Upload Time',
        'total_frames': 'Total Frames',
        'error_load_failed': 'Load Failed',
        'manage': 'Manage',
        'refresh': 'Refresh',
        'select_all': 'Select All',
        'deselect_all': 'Deselect All',
        
        // Analysis Page
        'analysis_results': 'Video Analysis Results',
        'analysis_results_front': 'Video Analysis Results (Front)',
        'video_id': 'Video ID',
        'status': 'Status',
        'original_video': 'Original Video',
        'skeleton_video': 'Skeleton Video',
        'play': '▶ Play',
        'pause': '⏸ Pause',
        'step_back': '⏮ Back',
        'step_fwd': '⏭ Fwd',
        'slower': '🐌 Slower',
        'faster': '🐇 Faster',
        'frame': 'Frame',
        
        // Tabs
        'tab_frame': 'Frame-by-Frame',
        'tab_keyframe': 'Keyframe Analysis',
        'tab_summary': 'Summary',
        
        // Status
        'status_pending': 'Pending',
        'status_processing': 'Processing',
        'status_completed': 'Completed',
        'status_failed': 'Failed',

        // Analysis Content
        'current_value': 'Current Value',
        'standard_range': 'Standard Range',
        'defect_detected': 'Defect Detected',
        'normal': 'Normal',
        'unknown': 'Unknown',
        'score': 'Score',
        'suggestion': 'Suggestion',
        'keyframe_event': 'Keyframe Event',

        // Keyframe Events
        'event_setup': 'Setup',
        'event_takeaway': 'Takeaway',
        'event_backswing': 'Backswing',
        'event_top': 'Top',
        'event_downswing': 'Downswing',
        'event_impact': 'Impact',
        'event_follow_through': 'Follow Through',
        'event_finish': 'Finish',

        // Metrics Categories
        'cat_kinematic': 'Kinematic Metrics',
        'cat_rotation': 'Rotation Metrics',
        'cat_posture': 'Posture Metrics',
        'cat_displacement': 'Displacement Metrics',
        'cat_energy': 'Energy Metrics',
        'cat_other': 'Other Metrics',

        // Metric Status
        'status_severe_insufficient': 'Severely Insufficient',
        'status_slight_exceed': 'Slightly Exceeded',
        'status_minor_deviation': 'Minor Deviation',
        'status_abnormal': 'Abnormal',
        'status_standard': 'Standard',

        // Summary
        'summary_overall': 'Overall Assessment',
        'summary_total_frames': 'Total Frames',
        'summary_excellent_rate': 'Excellent Rate',
        'summary_standard_rate': 'Standard Rate',
        'summary_abnormal_rate': 'Non-Standard Rate',
        'summary_max_continuous': 'Max Continuous Abnormal Frames',
        'summary_top_issues': 'Top Issues',
        'summary_ai_feedback': 'Optimization Suggestions & Analysis',
        'summary_view_front': 'Front View',
        'summary_view_side': 'Side View',
        'summary_no_ai': 'No AI Suggestions',

        // Metric Names
        'metric_shoulder_rot': 'Shoulder Rotation (Rel)',
        'metric_hip_rot': 'Hip Rotation (Rel)',
        'metric_body_tilt': 'Body Tilt',
        'metric_hip_dx': 'Hip X Displacement',
        'metric_shoulder_dx': 'Shoulder Center X Displacement',
        'metric_left_hand_dx': 'Left Hand X Displacement',
        'metric_energy_index': 'Energy Index (X-Factor)',
        'metric_trunk_dy': 'Trunk Center Y Displacement',
        'metric_shoulder_tilt': 'Shoulder Tilt',
        'metric_hip_tilt': 'Hip Tilt',
        
        // Frame-by-Frame Metrics
        'metric_left_hip_dx': 'Left Hip X Displacement',
        'metric_abnormal_count': 'Abnormal Metrics Count (Frame)',
        'metric_minor_count': 'Minor Deviation Count (Frame)',
        'metric_shoulder_z_angle': 'Shoulder-Z Angle',
        'metric_hip_z_angle': 'Hip-Z Angle',
        'metric_shoulder_hip_diff': 'Shoulder-Hip Rotation Diff',
        'metric_body_y_angle': 'Body Plane-Y Angle',
        'metric_head_dx': 'Head X Displacement',
        'metric_head_dy': 'Head Y Displacement',
        'metric_spine_angle': 'Spine Angle',
        'metric_left_head_dx': 'Left Head X Displacement',
        'metric_right_head_dx': 'Right Head X Displacement',

        'alert_no_abnormal': 'No abnormalities found for this metric in any frame',
        'no_data': 'No Data',
        'none': 'None',
        
        // Additional Metrics - Side View
        'metric_右髋X轴位移': 'Right Hip X Displacement',
        'metric_左手X轴位移': 'Left Hand X Displacement',
        'metric_左髋X轴位移': 'Left Hip X Displacement',
        'metric_右脑X轴位移': 'Right Head X Displacement',
        'metric_肩线与Z轴夹角_左正右负_近端终点_XZ平面': 'Shoulder-Z Angle',
        'metric_肩线与Z轴夹角_度_左正右负_近端终点_XZ平面': 'Shoulder-Z Angle',
        'metric_髋线与Z轴夹角_度_左正右负_近端终点_XZ平面': 'Hip-Z Angle',
        'metric_肩线中心X轴位移': 'Shoulder Center X Displacement',
        'metric_肩线旋转减髋线旋转_度': 'Shoulder-Hip Rotation Diff',
        'metric_身体平面与Y轴夹角_X轴为0向上为正_0到180': 'Body Plane-Y Angle',
        'metric_身体平面与Y轴夹角_度_X轴为0向上为正_0到180': 'Body Plane-Y Angle',
        'metric_头部X轴位移': 'Head X Displacement',
        'metric_头部Y轴位移': 'Head Y Displacement',
        'metric_脊柱倾角': 'Spine Angle',
        'metric_异常指标数_帧级': 'Abnormal Metrics Count',
        'metric_轻微偏差指标数_帧级': 'Minor Deviation Count',
        
        // Front View Metrics
        'metric_右髋X轴位移_正面': 'Right Hip X Displacement (Front)',
        'metric_左髋X轴位移_正面': 'Left Hip X Displacement (Front)',
        'metric_肩线中心X轴位移_正面': 'Shoulder Center X Displacement (Front)',
        'metric_躯干中点Y轴位移_正面': 'Trunk Center Y Displacement (Front)',
        'metric_肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面': 'Shoulder Rotation Angle (Front)',
        'metric_髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面': 'Hip Rotation Angle (Front)',
        'metric_左手X轴位移_正面': 'Left Hand X Displacement (Front)',
        'metric_右脑X轴位移_正面': 'Right Head X Displacement (Front)',
        'metric_左脑X轴位移_正面': 'Left Head X Displacement (Front)',
        'metric_头部X轴位移_正面': 'Head X Displacement (Front)',
        'metric_头部Y轴位移_正面': 'Head Y Displacement (Front)',
        
        // Verdict Results
        'verdict_优秀': 'Excellent',
        'verdict_标准': 'Standard',
        'verdict_基本标准': 'Basic Standard',
        'verdict_不标准': 'Non-Standard',
        'verdict_严重不标准': 'Severely Non-Standard',
        
        // Frame Conclusions
        'conclusion_优秀': 'Excellent',
        'conclusion_标准': 'Standard',
        'conclusion_基本标准': 'Basic Standard',
        'conclusion_不标准': 'Non-Standard',
        'conclusion_连续不标准': 'Continuous Non-Standard',
        
        // Label Types
        'label_normal': 'Normal',
        'label_slight_exceed': 'Slightly Exceeded',
        'label_severe_insufficient': 'Severely Insufficient',
        
        // Error Messages
        'error_video_not_found': 'Video not found',
        'error_analysis_not_complete': 'Analysis not complete',
        'error_load_failed': 'Load failed',
        'error_network': 'Network error',
        
        // UI Elements
        'btn_refresh': 'Refresh',
        'btn_delete': 'Delete',
        'btn_reanalyze': 'Re-analyze',
        'confirm_title': 'Confirm Action',
        'upload_time': 'Upload Time',
        'total_frames': 'Total Frames',
        'video_not_supported': 'Your browser does not support video playback',
        'playback_error': 'Video playback error',
        'loading_video': 'Loading...',
        'file_no_selected': 'File not selected',
        'file_selected': 'File selected',
        'browse': 'Browse...',
        'ai_feedback_label': 'AI Analysis Content (Original Language)',
        'ai_feedback_en': 'AI Analysis Content (English Translation)',
    }
};

// 反向翻译映射（用于从中文查找翻译键）
const reverseTranslations = {
    'zh': {},  // 中文不需要反向映射
    'en': {}   // 英文不需要反向映射
};

// 初始化反向翻译映射
function initReverseTranslations() {
    for (const lang of ['zh', 'en']) {
        reverseTranslations[lang] = {};
        for (const [key, value] of Object.entries(translations[lang])) {
            reverseTranslations[lang][value] = key;
        }
    }
}

initReverseTranslations();

let currentLang = localStorage.getItem('app_language') || 'zh';

function getTranslationKey(chineseText, lang = 'en') {
    if (!chineseText || typeof chineseText !== 'string') return null;
    return reverseTranslations[lang][chineseText] || null;
}

function translateApiResponse(data, type = 'metrics') {
    if (!data || typeof data !== 'object') return data;
    
    const translated = Array.isArray(data) ? [] : {};
    
    for (const [key, value] of Object.entries(data)) {
        if (typeof value === 'string') {
            const translatedKey = t(key);
            translated[translatedKey] = value;
        } else if (typeof value === 'object' && value !== null) {
            translated[key] = translateApiResponse(value, type);
        } else {
            translated[key] = value;
        }
    }
    
    return translated;
}

function translateMetricsObject(obj) {
    if (!obj || typeof obj !== 'object') return obj;
    
    const translated = {};
    for (const [key, value] of Object.entries(obj)) {
        const translatedKey = t(key);
        translated[translatedKey] = value;
    }
    return translated;
}

function translateVerdict(verdict) {
    if (!verdict) return verdict;
    const key = verdict.startsWith('verdict_') ? verdict : `verdict_${verdict}`;
    return t(key) || verdict;
}

function translateConclusion(conclusion) {
    if (!conclusion) return conclusion;
    const key = conclusion.startsWith('conclusion_') ? conclusion : `conclusion_${conclusion}`;
    return t(key) || conclusion;
}

function translateLabel(label) {
    if (!label) return label;
    const key = label.startsWith('label_') ? label : `label_${label}`;
    return t(key) || label;
}

function batchTranslate(data, fields) {
    if (!data || !fields || !Array.isArray(fields)) return data;
    
    const translated = { ...data };
    for (const field of fields) {
        if (translated[field] !== undefined) {
            const translatedValue = t(translated[field]);
            if (translatedValue !== translated[field]) {
                translated[field] = translatedValue;
            }
        }
    }
    return translated;
}

function translateFieldValue(value, prefix = '') {
    if (!value) return value;
    if (typeof value !== 'string') return value;
    
    const key = prefix ? `${prefix}_${value}` : value;
    const translated = t(key);
    return translated !== key ? translated : value;
}

function updateDynamicContent(container) {
    if (!container) return;
    
    const elements = container.querySelectorAll('[data-i18n-dynamic]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n-dynamic');
        el.textContent = t(key);
    });
}

class TranslationHelper {
    static translateMetrics(data) {
        return translateMetricsObject(data);
    }
    
    static translateSummary(data) {
        if (!data) return data;
        return {
            ...data,
            verdict: translateVerdict(data.verdict),
            topIssues: this.translateIssues(data.top_issues || data.topIssues),
        };
    }
    
    static translateIssues(issues) {
        if (!issues) return issues;
        if (typeof issues === 'string') {
            const translated = t(issues);
            return translated !== issues ? translated : issues;
        }
        if (Array.isArray(issues)) {
            return issues.map(issue => {
                const translated = t(issue);
                return translated !== issue ? translated : issue;
            });
        }
        return issues;
    }
    
    static translateKeyframes(data) {
        if (!data || !data.events) return data;
        return {
            ...data,
            events: data.events.map(event => ({
                ...event,
                label: t(event.label) || event.label
            }))
        };
    }
    
    static translateAnalysisData(data, analysisType = 'frame_by_frame') {
        if (!data) return data;
        
        const translated = { ...data };
        
        if (translated.video_summary) {
            translated.video_summary = this.translateSummary(translated.video_summary);
        }
        
        if (translated.data && Array.isArray(translated.data)) {
            translated.data = translated.data.map(row => {
                const newRow = { ...row };
                for (const [key, value] of Object.entries(row)) {
                    if (key.includes('__审判') || key.includes('__label')) {
                        const baseKey = key.split('__')[0];
                        const suffix = key.split('__')[1];
                        const translatedBase = t(baseKey);
                        if (translatedBase !== baseKey) {
                            delete newRow[key];
                            newRow[`${translatedBase}__${suffix}`] = value;
                        }
                    }
                }
                return newRow;
            });
        }
        
        return translated;
    }
    
    static translateStatus(status) {
        const statusMap = {
            'pending': 'status_pending',
            'processing': 'status_processing',
            'completed': 'status_completed',
            'failed': 'status_failed'
        };
        return t(statusMap[status] || status) || status;
    }
    
    static translateViewAngle(angle) {
        const angleMap = {
            '侧面': 'angle_side',
            '正面': 'angle_front',
            'side': 'angle_side',
            'front': 'angle_front'
        };
        return t(angleMap[angle] || angle) || angle;
    }
    
    static applyToElement(element, translations) {
        if (!element || !translations) return;
        
        for (const [key, value] of Object.entries(translations)) {
            const target = element.querySelector(`[data-i18n="${key}"]`);
            if (target) {
                target.textContent = value;
            }
        }
    }
}

function setLanguage(lang) {
    if (!translations[lang]) return;
    currentLang = lang;
    localStorage.setItem('app_language', lang);
    
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            // Handle inputs/placeholders if necessary, but mostly textContent
            if (element.tagName === 'INPUT' && element.getAttribute('type') === 'submit') {
                element.value = translations[lang][key];
            } else if (element.tagName === 'OPTION') {
                element.text = translations[lang][key];
            } else {
                // Check if there are child elements that shouldn't be overwritten (like spinners)
                // For now, simple text replacement. If complex structure, might need spans.
                // Special case for buttons with icons/spans
                if (element.children.length > 0 && !element.hasAttribute('data-i18n-text-only')) {
                     // If it has children, we might need to target a specific child or just replace text nodes
                     // For simplicity, let's assume we wrap text in spans in HTML if mixed
                     // Or we just replace the text content if the structure allows
                }
                
                // If the element has a specific structure like the upload button:
                // <span class="btn-text">...</span>
                // We should put data-i18n on the span, not the button.
                
                element.textContent = translations[lang][key];
            }
        }
    });

    // Update HTML lang attribute
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    
    // Dispatch event for other scripts to react
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
    
    updateSwitcherUI();
}

function t(key, params = {}) {
    let text = translations[currentLang][key] || key;
    if (params) {
        for (const [param, value] of Object.entries(params)) {
            text = text.replace(`{${param}}`, value);
        }
    }
    return text;
}

function updateSwitcherUI() {
    const btn = document.getElementById('langSwitcherBtn');
    if (btn) {
        // Show the target language to switch to, with a globe icon
        btn.innerHTML = currentLang === 'zh' ? '🌐 English' : '🌐 中文';
    }
}

function toggleLanguage() {
    const newLang = currentLang === 'zh' ? 'en' : 'zh';
    setLanguage(newLang);
    // 刷新页面以确保所有组件正确更新
    window.location.reload();
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    // Create switcher if not exists
    if (!document.getElementById('langSwitcher')) {
        const switcher = document.createElement('div');
        switcher.id = 'langSwitcher';
        switcher.style.position = 'fixed';
        switcher.style.bottom = '20px';
        switcher.style.right = '20px';
        switcher.style.zIndex = '9999';
        
        const btn = document.createElement('button');
        btn.id = 'langSwitcherBtn';
        btn.className = 'btn-secondary'; // Reuse existing class or style inline
        btn.style.padding = '8px 16px';
        btn.style.borderRadius = '20px';
        btn.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        btn.style.cursor = 'pointer';
        btn.style.backgroundColor = '#fff';
        btn.style.color = '#333'; // Ensure text is visible
        btn.style.border = '1px solid #ddd';
        btn.style.display = 'flex';
        btn.style.alignItems = 'center';
        btn.style.gap = '5px';
        btn.style.fontSize = '14px';
        btn.style.fontWeight = '500';
        btn.onclick = toggleLanguage;
        
        switcher.appendChild(btn);
        document.body.appendChild(switcher);
    }
    
    setLanguage(currentLang);
});

// Sync language across tabs
window.addEventListener('storage', (e) => {
    if (e.key === 'app_language') {
        const newLang = e.newValue;
        if (newLang && newLang !== currentLang) {
            setLanguage(newLang);
        }
    }
});
