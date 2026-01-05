import os
from pathlib import Path

# ================== 基础路径配置 ==================
# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent

# ================== Flask 应用配置 ==================
APP_CONFIG = {
    'SECRET_KEY': 'golf-swing-analysis-2025',
    'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,  # 500MB
    'UPLOAD_FOLDER': str(ROOT_DIR / 'uploads'),
    'DATABASE': str(ROOT_DIR / 'golf_analysis.db'),
    'ALLOWED_EXTENSIONS': {'mp4', 'avi', 'mov', 'mkv'}
}

# ================== 关键帧提取配置 (Extract_key_frames) ==================
KEYFRAME_CONFIG = {
    # 模型权重路径 - 请根据实际情况修改
    'WEIGHTS_PATH': "Extract_key_frames/swingnet_2000.pth.tar",
    'SEQ_LENGTH': 64,
    'NUM_EVENTS': 8,  # 关键帧数量 (8个事件)
    'DECODE_METHOD': 'ordered', # 解码方式: 'ordered' 或 'independent'
    'INPUT_SIZE': (224, 224), # (height, width)
    'OUTPUT_DIR': str(ROOT_DIR / 'Extract_key_frames/output')
}

# ================== 关键点检测配置 (Keypoint_detection) ==================
KEYPOINT_CONFIG = {
    'OUTPUT_DIR': str(ROOT_DIR / 'Keypoint_detection/output_single'),
    'SCALE_FACTOR': 1.0, # 图像缩放比例
    'MODEL_COMPLEXITY': 1, # MediaPipe模型复杂度: 0, 1, 2
}

# ================== 运动分析配置 (analyze) ==================
ANALYSIS_CONFIG = {
    'OUTPUT_DIR': str(ROOT_DIR / 'analyze/output'),
    # 标准范围文件路径
    'STD_SIDE_PATH': str(ROOT_DIR / 'analyze/侧面标准范围.csv'),
    'STD_FRONT_PATH': str(ROOT_DIR / 'analyze/正面标准范围.csv'),
}

# ================== 关键帧分析配置 (Keyframe_analysis) ==================
KEYFRAME_ANALYSIS_CONFIG = {
    'OUTPUT_DIR': str(ROOT_DIR / 'Keyframe_analysis/output'),
    'STD_SIDE_PATH': str(ROOT_DIR / 'Keyframe_analysis/侧面normal_ranges_down_the_line_60_20_20.csv'),
    'STD_FRONT_PATH': str(ROOT_DIR / 'Keyframe_analysis/正面normal_ranges_face_on_60_20_20.csv'),
}

# ================== 可视化配置 (visualization) ==================
VISUALIZATION_CONFIG = {
    'OUTPUT_DIR': str(ROOT_DIR / 'visualization/output'),
    'PANEL_WIDTH': 400, # 可视化面板宽度
    'ENABLE_VIZ': True, # 是否生成可视化视频
    'GENERATE_SKELETON': True, # 是否生成骨架视频
}
