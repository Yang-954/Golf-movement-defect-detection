"""
高尔夫挥杆分析 - Flask Web应用
提供视频上传、分析处理、结果可视化展示功能
"""
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
import subprocess
import threading
from video_utils import convert_video_to_compatible_format
import config
import importlib.util
import importlib.machinery
import traceback
import html
import re
import cv2
import shutil
import tempfile

# 初始化Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = config.APP_CONFIG['SECRET_KEY']
app.config['MAX_CONTENT_LENGTH'] = config.APP_CONFIG['MAX_CONTENT_LENGTH']
app.config['UPLOAD_FOLDER'] = config.APP_CONFIG['UPLOAD_FOLDER']
app.config['DATABASE'] = config.APP_CONFIG['DATABASE']

# 允许的视频格式
ALLOWED_EXTENSIONS = config.APP_CONFIG['ALLOWED_EXTENSIONS']

# 缩略图目录
THUMBNAIL_FOLDER = os.path.join(app.static_folder, 'thumbnails')
Path(THUMBNAIL_FOLDER).mkdir(exist_ok=True)

# 确保必要目录存在
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)


# 添加CORS支持
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range'
    return response


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # 创建视频表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            original_filename TEXT NOT NULL,
            renamed_filename TEXT NOT NULL,
            video_path TEXT NOT NULL,
            view_angle TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            total_frames INTEGER,
            fps REAL,
            duration REAL,
            thumbnail_path TEXT
        )
    ''')
    
    # 检查是否需要添加 thumbnail_path 列
    try:
        cursor.execute("PRAGMA table_info(videos)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'thumbnail_path' not in cols:
            cursor.execute('ALTER TABLE videos ADD COLUMN thumbnail_path TEXT')
    except Exception:
        pass
    
    # 创建分析结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            view_angle TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            csv_path TEXT,
            visualization_path TEXT,
            skeleton_video_path TEXT,
            keyframes_json TEXT,
            video_summary_json TEXT,
            ai_feedback_html_zh TEXT,
            ai_feedback_html_en TEXT,
            created_time TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')
    # 确保旧表包含 ai_feedback_html 列（兼容迁移）
    try:
        cursor.execute("PRAGMA table_info(analysis_results)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'ai_feedback_html' in cols:
            cursor.execute('ALTER TABLE analysis_results RENAME COLUMN ai_feedback_html TO ai_feedback_html_zh')
        if 'ai_feedback_html_zh' not in cols:
            cursor.execute('ALTER TABLE analysis_results ADD COLUMN ai_feedback_html_zh TEXT')
        if 'ai_feedback_html_en' not in cols:
            cursor.execute('ALTER TABLE analysis_results ADD COLUMN ai_feedback_html_en TEXT')
    except Exception:
        pass
    
    # 创建指标标准表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metric_standards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            view_angle TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            judge_method TEXT,
            lower_limit REAL,
            upper_limit REAL,
            weight REAL,
            unit TEXT,
            category TEXT
        )
    ''')
    
    # 创建详细分析数据表 (JSON存储以适应动态指标) - 侧面
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS frame_analysis_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            frame_index INTEGER NOT NULL,
            metrics_json TEXT,
            judgments_json TEXT,
            frame_score REAL,
            frame_verdict TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')
    
    # 创建详细分析数据表 (JSON存储以适应动态指标) - 正面
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS frame_analysis_details_front (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            frame_index INTEGER NOT NULL,
            metrics_json TEXT,
            judgments_json TEXT,
            frame_score REAL,
            frame_verdict TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_frame_analysis_video_id ON frame_analysis_details(video_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_frame_analysis_front_video_id ON frame_analysis_details_front(video_id)
    ''')

    # 创建视频级汇总表 - 侧面
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_analysis_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            total_score REAL,
            verdict TEXT,
            top_issues_json TEXT,
            metrics_summary_json TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')

    # 创建视频级汇总表 - 正面
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_analysis_summary_front (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            total_score REAL,
            verdict TEXT,
            top_issues_json TEXT,
            metrics_summary_json TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')

    # 创建关键帧分析详情表 - 侧面
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keyframe_analysis_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            frame_index INTEGER NOT NULL,
            event_name TEXT,
            metrics_json TEXT,
            judgments_json TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')

    # 创建关键帧分析详情表 - 正面
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keyframe_analysis_details_front (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            frame_index INTEGER NOT NULL,
            event_name TEXT,
            metrics_json TEXT,
            judgments_json TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')

    # 创建关键点数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keypoints_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            frame_index INTEGER NOT NULL,
            landmarks_json TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_keypoints_video_id ON keypoints_data(video_id)
    ''')
    
    conn.commit()
    conn.close()


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def generate_ai_feedback_for_video(video_id, view_cn, lang='zh'):
    """为指定视频与视角生成 AI 反馈（返回 HTML-safe 字符串或 None）。"""
    try:
        ai_path = os.path.join(os.path.dirname(__file__), 'ai反馈.py')
        spec = importlib.util.spec_from_file_location('ai_feedback_module', ai_path)
        ai_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ai_mod)
    except Exception as e:
        print(f"[AI] 加载 ai模块失败: {e}")
        return None

    kf_summary = os.path.join(config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR'], f"{view_cn}_关键帧分析_视频汇总.csv")
    if not os.path.exists(kf_summary):
        return None

    try:
        try:
            kf_df = pd.read_csv(kf_summary, encoding='utf-8-sig')
        except Exception:
            kf_df = pd.read_csv(kf_summary, encoding='gbk')
    except Exception as e:
        print(f"[AI] 读取关键帧汇总失败: {e}")
        return None

    row = None
    if 'video_id' in kf_df.columns:
        sel = kf_df[kf_df['video_id'] == video_id]
        if not sel.empty:
            row = sel.iloc[0].to_dict()
    elif '视频ID' in kf_df.columns:
        sel = kf_df[kf_df['视频ID'] == video_id]
        if not sel.empty:
            row = sel.iloc[0].to_dict()

    if not row:
        return None

    # if lang == 'en':
    #     user_prompt = (
    #         f"As a golf sports health and biomechanics expert, generate an 'Optimization Suggestions & Analysis' section based on the following video-level keyframe summary data (View: {view_cn}). "
    #         "The output must include:\n1. Conclusion Summary\n2. Key Evidence (key metrics/numbers)\n3. Actionable optimization suggestions and training points\n4. Retesting and tracking suggestions.\n"
    #         "Return ONLY the section text, no extra explanations.\n\nData: " + json.dumps(row, ensure_ascii=False)
    #     )
    # else:
    #     user_prompt = (
    #         f"请作为高尔夫运动健康与生物力学专家，根据下列视频级关键帧汇总数据（视角：{view_cn}）生成一个\"优化建议和分析\"栏目。"
    #         " 输出须包含：\n1. 结论摘要\n2. 主要证据（关键指标/数值）\n3. 可执行的优化建议与训练要点\n4. 复测与跟踪建议。\n"
    #         "仅返回该栏目文本，不要多余说明。\n\n数据：" + json.dumps(row, ensure_ascii=False)
    #     )
    if lang == 'en':
        user_prompt = (
            f"As a **golf sports health and biomechanics expert**, generate a professional "
            f"'Optimization Suggestions & Analysis' section based on the following video-level "
            f"keyframe summary data (View: {view_cn}).\n\n"
            "Analysis requirements:\n"
            "1. Clearly determine whether movement deficiencies are present and summarize the overall risk level.\n"
            "2. For each metric labeled as abnormal (e.g., severe_insufficient, slight_exceed), provide a metric-specific analysis "
            "explaining its biomechanical meaning.\n"
            "3. For critical deficiencies (such as insufficient shoulder/hip relative rotation or excessive lateral shift), explain:\n"
            "   - Its role in the golf swing kinetic chain\n"
            "   - Potential long-term consequences on performance and injury risk "
            "(e.g., increased stress on the lower back, shoulders, or hips)\n"
            "4. Provide actionable optimization and training recommendations, including:\n"
            "   - Training objectives (what ability is being improved)\n"
            "   - Recommended training methods or drill types "
            "(e.g., mobility training, stability training, separation training)\n"
            "   - Key technical points and precautions during training\n"
            "5. Include retesting and tracking suggestions, specifying which metrics should be monitored "
            "to evaluate training effectiveness.\n\n"
            "Required output structure (must be strictly followed):\n"
            "1. Conclusion Summary\n"
            "2. Key Evidence (key metrics, current values, reference ranges, and labels)\n"
            "3. Actionable Optimization Suggestions & Training Points (organized by metric)\n"
            "4. Retesting & Progress Tracking Suggestions\n\n"
            "Return ONLY the section text. Do NOT include any additional explanations.\n\n"
            "Data: " + json.dumps(row, ensure_ascii=False)
        )
    else:
        user_prompt = (
            f"请作为【高尔夫运动健康与生物力学专家】，基于以下视频级关键帧汇总数据（视角：{view_cn}），"
            "生成一个专业、可用于训练指导的《优化建议与分析》栏目。\n\n"
            "分析要求：\n"
            "1. 明确指出是否存在动作缺陷，并说明整体风险等级。\n"
            "2. 对所有被标记为异常的指标（如 severe_insufficient、slight_exceed 等）进行逐项分析，"
            "说明其生物力学含义。\n"
            "3. 对于关键缺陷（如肩部/髋部相对旋转不足、侧移超限等），需说明：\n"
            "   - 该问题在挥杆动力链中的作用\n"
            "   - 长期存在可能带来的运动表现下降或伤害风险（如腰背、肩关节、髋关节压力）\n"
            "4. 给出可执行的训练与优化建议，包括：\n"
            "   - 训练目标（改善什么能力）\n"
            "   - 建议的训练方式或动作类型（如活动度训练、稳定性训练、分离度训练等）\n"
            "   - 训练时需要注意的关键点\n"
            "5. 提供复测与跟踪建议，说明应重点关注哪些指标的变化来评估训练效果。\n\n"
            "输出格式要求（必须严格遵守）：\n"
            "1. 结论摘要\n"
            "2. 主要证据（列出关键指标、当前值、参考区间与判定标签）\n"
            "3. 优化建议与训练要点（按指标分条说明）\n"
            "4. 复测与跟踪建议\n\n"
            "仅返回上述栏目文本，不要添加任何额外说明或解释。\n\n"
            "数据：" + json.dumps(row, ensure_ascii=False)
        )

    messages = []
    messages = ai_mod.add_message(messages, 'system', ai_mod.SYSTEM_PROMPT)
    messages = ai_mod.add_message(messages, 'user', user_prompt)

    try:
        print(f"[AI] 生成反馈: video={video_id}, view={view_cn}, lang={lang}")
        answer = ai_mod.spark_chat_stream(messages)
        if not answer:
            return None
        
        # 格式化处理：先转义HTML，再处理Markdown加粗，最后处理换行
        safe = html.escape(answer)
        safe = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', safe)
        safe = safe.replace('\n', '<br>')
        
        return safe
    except Exception as e:
        print(f"[AI] 调用失败: {e}")
        return None


def generate_ai_feedback_bilingual(video_id, view_cn, kf_analysis_dir=None):
    """为指定视频与视角生成中英文双语 AI 反馈（返回包含中英文的字典）。"""
    try:
        ai_path = os.path.join(os.path.dirname(__file__), 'ai反馈.py')
        spec = importlib.util.spec_from_file_location('ai_feedback_module', ai_path)
        ai_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ai_mod)
    except Exception as e:
        print(f"[AI] 加载 ai模块失败: {e}")
        return {'zh': None, 'en': None}

    # Use provided directory or fall back to config
    kf_analysis_base = kf_analysis_dir if kf_analysis_dir else config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR']
    kf_summary = os.path.join(kf_analysis_base, f"{view_cn}_关键帧分析_视频汇总.csv")
    
    if not os.path.exists(kf_summary):
        print(f"[AI] 关键帧汇总文件不存在: {kf_summary}")
        return {'zh': None, 'en': None}

    try:
        try:
            kf_df = pd.read_csv(kf_summary, encoding='utf-8-sig')
        except Exception:
            kf_df = pd.read_csv(kf_summary, encoding='gbk')
    except Exception as e:
        print(f"[AI] 读取关键帧汇总失败: {e}")
        return {'zh': None, 'en': None}

    row = None
    if 'video_id' in kf_df.columns:
        sel = kf_df[kf_df['video_id'] == video_id]
        if not sel.empty:
            row = sel.iloc[0].to_dict()
    elif '视频ID' in kf_df.columns:
        sel = kf_df[kf_df['视频ID'] == video_id]
        if not sel.empty:
            row = sel.iloc[0].to_dict()

    if not row:
        print(f"[AI] 在汇总文件中未找到视频ID: {video_id}")
        return {'zh': None, 'en': None}

    messages = []
    messages = ai_mod.add_message(messages, 'system', ai_mod.SYSTEM_PROMPT)

    # 1. 生成中文版本
    # zh_prompt = (
    #     f"请作为高尔夫运动健康与生物力学专家，根据下列视频级关键帧汇总数据（视角：{view_cn}）生成一个\"优化建议和分析\"栏目。"
    #     " 输出须包含：\n1. 结论摘要\n2. 主要证据（关键指标/数值）\n3. 可执行的优化建议与训练要点\n4. 复测与跟踪建议。\n"
    #     "仅返回该栏目文本，不要多余说明。\n\n数据：" + json.dumps(row, ensure_ascii=False)
    # )
    zh_prompt = (
            f"请作为【高尔夫运动健康与生物力学专家】，基于以下视频级关键帧汇总数据（视角：{view_cn}），"
            "生成一个专业、可用于训练指导的《优化建议与分析》栏目。\n\n"
            "分析要求：\n"
            "1. 明确指出是否存在动作缺陷，并说明整体风险等级。\n"
            "2. 对所有被标记为异常的指标（如 severe_insufficient、slight_exceed 等）进行逐项分析，"
            "说明其生物力学含义。\n"
            "3. 对于关键缺陷（如肩部/髋部相对旋转不足、侧移超限等），需说明：\n"
            "   - 该问题在挥杆动力链中的作用\n"
            "   - 长期存在可能带来的运动表现下降或伤害风险（如腰背、肩关节、髋关节压力）\n"
            "4. 给出可执行的训练与优化建议，包括：\n"
            "   - 训练目标（改善什么能力）\n"
            "   - 建议的训练方式或动作类型（如活动度训练、稳定性训练、分离度训练等）\n"
            "   - 训练时需要注意的关键点\n"
            "5. 提供复测与跟踪建议，说明应重点关注哪些指标的变化来评估训练效果。\n\n"
            "输出格式要求（必须严格遵守）：\n"
            "1. 结论摘要\n"
            "2. 主要证据（列出关键指标、当前值、参考区间与判定标签）\n"
            "3. 优化建议与训练要点（按指标分条说明）\n"
            "4. 复测与跟踪建议\n\n"
            "仅返回上述栏目文本，不要添加任何额外说明或解释。\n\n"
            "数据：" + json.dumps(row, ensure_ascii=False)
        )
    
    zh_messages = messages.copy()
    zh_messages = ai_mod.add_message(zh_messages, 'user', zh_prompt)
    
    try:
        print(f"[AI] 生成中文反馈: video={video_id}, view={view_cn}")
        zh_answer = ai_mod.spark_chat_stream(zh_messages)
        if not zh_answer:
            raise Exception("中文回答为空")
        
        # 格式化处理：先转义HTML，再处理Markdown加粗，最后处理换行
        zh_html = html.escape(zh_answer)
        zh_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', zh_html)
        zh_html = zh_html.replace('\n', '<br>')
        
        print(f"[AI] 中文反馈生成成功: {len(zh_answer)} 字符")
    except Exception as e:
        print(f"[AI] 中文反馈生成失败: {e}")
        return {'zh': None, 'en': None}

    # 2. 生成英文版本 - 使用更详细的翻译指南
    # en_prompt = (
    #     f"请将以下高尔夫挥杆分析报告完整翻译成英文。必须严格遵守以下规则：\n\n"
    #     f"1. 章节标题翻译对照：\n"
    #     f"   - 结论摘要 -> Conclusion Summary\n"
    #     f"   - 主要证据 -> Key Evidence\n"
    #     f"   - 可执行的优化建议与训练要点 -> Actionable Optimization Suggestions & Training Points\n"
    #     f"   - 复测与跟踪建议 -> Retesting & Tracking Suggestions\n\n"
    #     f"2. 所有正文内容必须翻译成英文，不要保留任何中文字符\n"
    #     f"3. 保持HTML换行标签<br>格式不变\n"
    #     f"4. 保持项目符号编号格式（如1. 2. 3. 或 - ）\n"
    #     f"5. 技术指标名称保留英文，但解释内容翻译\n"
    #     f"6. 数字和单位保持不变\n\n"
    #     f"原文：\n{zh_answer}"
    # )
    en_prompt = (
        f"Please translate the following **golf swing analysis report** into professional, "
        f"publication-ready English. The translation must strictly comply with ALL rules below:\n\n"

        f"1. Section title mapping (must be translated exactly as specified):\n"
        f"   - 结论摘要 -> Conclusion Summary\n"
        f"   - 主要证据 -> Key Evidence\n"
        f"   - 可执行的优化建议与训练要点 -> Actionable Optimization Suggestions & Training Points\n"
        f"   - 复测与跟踪建议 -> Retesting & Tracking Suggestions\n\n"

        f"2. All body text must be fully translated into English. "
        f"Do NOT retain any Chinese characters.\n"
        f"3. Preserve all HTML line break tags (<br>) exactly as they appear.\n"
        f"4. Preserve original list and numbering formats "
        f"(e.g., '1. 2. 3.' or '-' bullet points).\n"
        f"5. Technical metric names, variable names, and labels "
        f"(e.g., shoulder_rot_rel_deg, severe_insufficient) must remain in English, "
        f"but their explanatory descriptions must be translated.\n"
        f"6. All numeric values, symbols, ranges, and units must remain unchanged.\n"
        f"7. Use precise sports biomechanics and golf training terminology. "
        f"Avoid literal or awkward translations.\n"
        f"8. Maintain a formal, objective, expert-level tone suitable for "
        f"sports performance analysis and injury-risk assessment reports.\n\n"

        f"Original text:\n{zh_answer}"
    )

    en_messages = messages.copy()
    en_messages = ai_mod.add_message(en_messages, 'user', en_prompt)
    
    try:
        print(f"[AI] 生成英文反馈: video={video_id}, view={view_cn}")
        en_answer = ai_mod.spark_chat_stream(en_messages)
        if not en_answer:
            raise Exception("英文翻译为空")
        
        # 格式化处理：先转义HTML，再处理Markdown加粗，最后处理换行
        en_html = html.escape(en_answer)
        en_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', en_html)
        en_html = en_html.replace('\n', '<br>')
        
        print(f"[AI] 英文反馈生成成功: {len(en_answer)} 字符")
    except Exception as e:
        print(f"[AI] 英文反馈生成失败: {e}")
        # 即使英文失败，也返回中文版本
        return {'zh': zh_html, 'en': None}

    return {'zh': zh_html, 'en': en_html}


def load_metric_standards():
    """加载指标标准到数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 强制重新加载：先清空表
    cursor.execute('DELETE FROM metric_standards')
    
    # 加载各个标准CSV文件
    standard_files = [
        (config.ANALYSIS_CONFIG['STD_SIDE_PATH'], '侧面', 'frame_by_frame'),
        (config.ANALYSIS_CONFIG['STD_FRONT_PATH'], '正面', 'frame_by_frame'),
        (config.KEYFRAME_ANALYSIS_CONFIG['STD_SIDE_PATH'], '侧面', 'keyframe'),
        (config.KEYFRAME_ANALYSIS_CONFIG['STD_FRONT_PATH'], '正面', 'keyframe'),
    ]
    
    count = 0
    for csv_file, view_angle, analysis_type in standard_files:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                print(f"[初始化] 加载标准文件: {csv_file}, {len(df)} 条记录")
                for _, row in df.iterrows():
                    # Determine column mapping based on available columns
                    if '指标' in row:
                        metric_name = row['指标']
                        judge_method = row.get('判定方式', '')
                        lower_limit = row.get('下限', None)
                        upper_limit = row.get('上限', None)
                        weight = row.get('权重', 1.0)
                    elif 'metric' in row:
                        metric_name = row['metric']
                        if 'event_index' in row:
                             metric_name = f"{metric_name}_event_{row['event_index']}"
                        judge_method = ''
                        lower_limit = row.get('low_th_q20', None)
                        upper_limit = row.get('high_th_q80', None)
                        weight = 1.0
                    else:
                        continue

                    cursor.execute('''
                        INSERT INTO metric_standards 
                        (view_angle, analysis_type, metric_name, judge_method, lower_limit, upper_limit, weight)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        view_angle,
                        analysis_type,
                        metric_name,
                        judge_method,
                        lower_limit,
                        upper_limit,
                        weight
                    ))
                    count += 1
            except Exception as e:
                print(f"[错误] 加载标准文件失败 {csv_file}: {e}")
        else:
            print(f"[警告] 标准文件不存在: {csv_file}")
    
    conn.commit()
    conn.close()
    print(f"[初始化] 指标标准加载完成，共 {count} 条")


def generate_thumbnail(video_path, video_id):
    """生成视频缩略图"""
    temp_video_path = None
    try:
        # 尝试直接打开
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            # 如果直接打开失败（可能是中文路径问题），尝试复制到临时文件
            print(f"[警告] 无法直接打开视频 {video_path}，尝试使用临时文件...")
            fd, temp_video_path = tempfile.mkstemp(suffix=os.path.splitext(video_path)[1])
            os.close(fd)
            shutil.copy2(video_path, temp_video_path)
            cap = cv2.VideoCapture(temp_video_path)
            
            if not cap.isOpened():
                print(f"[错误] 无法打开视频文件: {video_path}")
                if temp_video_path and os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                return None
        
        ret, frame = cap.read()
        cap.release()
        
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        
        if not ret or frame is None:
            print(f"[错误] 无法读取视频帧: {video_path}")
            return None
            
        # 调整大小以减小文件体积
        height, width = frame.shape[:2]
        max_dim = 400
        if width > max_dim or height > max_dim:
            scale = max_dim / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
            
        filename = f"{video_id}.jpg"
        save_path = os.path.join(THUMBNAIL_FOLDER, filename)
        
        # 确保保存路径目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存图片（处理中文路径问题）
        # cv2.imwrite 不支持中文路径，使用 imencode + tofile
        is_success, im_buf = cv2.imencode(".jpg", frame)
        if is_success:
            im_buf.tofile(save_path)
        else:
            print(f"[错误] 图片编码失败")
            return None
        
        # 返回相对路径供前端使用
        return f"/static/thumbnails/{filename}"
    except Exception as e:
        print(f"[错误] 生成缩略图失败: {e}")
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except:
                pass
        return None


@app.route('/')
def index():
    """主页 - 视频上传和列表"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_video():
    """上传视频并触发分析"""
    if 'video' not in request.files:
        return jsonify({'error': '未找到视频文件'}), 400
    
    file = request.files['video']
    view_angle = request.form.get('view_angle', '侧面')
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'不支持的文件格式，仅支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # 保存上传的视频
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 获取下一个序号
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM videos')
    count = cursor.fetchone()['count']
    
    # 生成新的视频ID和重命名文件名
    video_id = f"{count}_{timestamp}"
    ext = os.path.splitext(original_filename)[1]
    if not ext:
        ext = '.mp4'
    renamed_filename = f"{video_id}{ext}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], renamed_filename)
    
    # 保存文件
    file.save(video_path)
    print(f"[上传] 原始文件名: {original_filename}")
    print(f"[上传] 重命名为: {renamed_filename}")
    print(f"[上传] 视频ID: {video_id}")
    
    # 生成缩略图
    thumbnail_path = generate_thumbnail(video_path, video_id)
    
    # 保存到数据库
    cursor.execute('''
        INSERT INTO videos (video_id, original_filename, renamed_filename, video_path, view_angle, upload_time, status, thumbnail_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (video_id, original_filename, renamed_filename, video_path, view_angle, datetime.now().isoformat(), 'processing', thumbnail_path))
    conn.commit()
    conn.close()
    
    # 启动后台分析任务
    thread = threading.Thread(target=run_analysis, args=(video_id, video_path, view_angle))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'video_id': video_id,
        'message': '视频上传成功，正在后台分析...',
        'status': 'processing'
    })


def run_analysis(video_id, video_path, view_angle):
    """运行完整分析流程（后台任务）"""
    try:
        # Define unique output directories
        analysis_out_dir = os.path.join(config.ANALYSIS_CONFIG['OUTPUT_DIR'], video_id)
        kf_analysis_out_dir = os.path.join(config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR'], video_id)
        kp_out_dir = os.path.join(config.KEYPOINT_CONFIG['OUTPUT_DIR'], video_id)
        
        # Ensure directories exist
        os.makedirs(analysis_out_dir, exist_ok=True)
        os.makedirs(kf_analysis_out_dir, exist_ok=True)
        os.makedirs(kp_out_dir, exist_ok=True)

        # 1. 尝试转码原视频，确保浏览器可播放
        print(f"[分析] 正在检查视频兼容性: {video_path}")
        compatible_path = convert_video_to_compatible_format(video_path)
        
        final_video_path = video_path
        if compatible_path and compatible_path != video_path:
            print(f"[分析] 视频已转码为兼容格式: {compatible_path}")
            final_video_path = compatible_path
            
            # 更新数据库中的视频路径
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('UPDATE videos SET video_path = ? WHERE video_id = ?', (final_video_path, video_id))
                conn.commit()
                conn.close()
            except Exception as db_e:
                print(f"[警告] 更新数据库视频路径失败: {db_e}")
        
        # 2. 调用run_full_analysis.py
        cmd = [
            'python', 'run_full_analysis.py',
            '--video_path', final_video_path,
            '--view_angle', view_angle,
            '--video_id', video_id,
            '--analysis_out_dir', analysis_out_dir,
            '--keyframe_analysis_out_dir', kf_analysis_out_dir,
            '--kp_output_dir', kp_out_dir
        ]
        
        # Windows系统需要使用gbk编码或忽略编码错误
        import sys
        encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding=encoding,
            errors='replace'  # 替换无法解码的字符
        )
        
        if result.returncode == 0:
            # 分析成功，收集结果文件
            collect_analysis_results(video_id, view_angle, analysis_out_dir, kf_analysis_out_dir, kp_out_dir)
            update_video_status(video_id, 'completed')
        else:
            print(f"分析失败: {result.stderr}")
            update_video_status(video_id, 'failed')
    
    except Exception as e:
        print(f"分析过程出错: {str(e)}")
        update_video_status(video_id, 'failed')


def ingest_analysis_data(conn, video_id, view_angle_cn, kp_dir=None, analysis_dir=None, kf_analysis_dir=None):
    """将CSV数据导入数据库表"""
    cursor = conn.cursor()
    
    # Use provided directories or fall back to config
    kp_base = kp_dir if kp_dir else config.KEYPOINT_CONFIG['OUTPUT_DIR']
    analysis_base = analysis_dir if analysis_dir else config.ANALYSIS_CONFIG['OUTPUT_DIR']
    kf_analysis_base = kf_analysis_dir if kf_analysis_dir else config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR']

    # 1. 导入关键点数据
    kp_csv = os.path.join(kp_base, "单视频_缺陷分析数据.csv")
    if os.path.exists(kp_csv):
        try:
            df = pd.read_csv(kp_csv)
            if 'video_id' in df.columns:
                df = df[df['video_id'] == video_id]
            
            cursor.execute("DELETE FROM keypoints_data WHERE video_id = ?", (video_id,))
            
            for _, row in df.iterrows():
                frame_idx = int(row.get('frame_index', row.get('frame_序号', 0)))
                landmarks = []
                for i in range(33):
                    lm_str = row.get(f'landmark_{i}', '')
                    landmarks.append(lm_str)
                
                cursor.execute('''
                    INSERT INTO keypoints_data (video_id, frame_index, landmarks_json)
                    VALUES (?, ?, ?)
                ''', (video_id, frame_idx, json.dumps(landmarks)))
            print(f"[入库] 关键点数据: {len(df)} 条")
        except Exception as e:
            print(f"[错误] 导入关键点数据失败: {e}")

    # 2. 导入逐帧分析详情
    frame_csv = os.path.join(analysis_base, f"{view_angle_cn}_逐帧审判结果.csv")
    if os.path.exists(frame_csv):
        try:
            df = pd.read_csv(frame_csv, encoding='utf-8-sig')
            if '视频ID' in df.columns:
                df = df[df['视频ID'] == video_id]
            
            # 根据视角选择表名
            table_name = "frame_analysis_details_front" if view_angle_cn == "正面" else "frame_analysis_details"
            
            cursor.execute(f"DELETE FROM {table_name} WHERE video_id = ?", (video_id,))
            
            for _, row in df.iterrows():
                frame_idx = int(row.get('帧序号', 0))
                metrics = {}
                judgments = {}
                
                for col in df.columns:
                    if col in ['视频ID', '帧序号', '帧级加权偏差', '帧级评分_0到100', '帧级结论', '帧级异常_连续过滤后', '帧级结论_连续过滤后']:
                        continue
                    
                    if '__' in col:
                        # 判定结果
                        metric_name, suffix = col.split('__', 1)
                        if metric_name not in judgments:
                            judgments[metric_name] = {}
                        judgments[metric_name][suffix] = row[col]
                    else:
                        # 指标数值
                        metrics[col] = row[col]
                
                cursor.execute(f'''
                    INSERT INTO {table_name} 
                    (video_id, frame_index, metrics_json, judgments_json, frame_score, frame_verdict)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    video_id, 
                    frame_idx, 
                    json.dumps(metrics, ensure_ascii=False), 
                    json.dumps(judgments, ensure_ascii=False),
                    row.get('帧级评分_0到100', 0),
                    row.get('帧级结论_连续过滤后', row.get('帧级结论', ''))
                ))
            print(f"[入库] 逐帧分析数据: {len(df)} 条")
        except Exception as e:
            print(f"[错误] 导入逐帧分析数据失败: {e}")

    # 3. 导入视频级汇总
    summary_csv = os.path.join(analysis_base, f"{view_angle_cn}_视频级审判汇总.csv")
    if os.path.exists(summary_csv):
        try:
            df = pd.read_csv(summary_csv, encoding='utf-8-sig')
            if '视频ID' in df.columns:
                df = df[df['视频ID'] == video_id]
            
            # 根据视角选择表名
            table_name = "video_analysis_summary_front" if view_angle_cn == "正面" else "video_analysis_summary"
            
            cursor.execute(f"DELETE FROM {table_name} WHERE video_id = ?", (video_id,))
            
            if not df.empty:
                row = df.iloc[0]
                # 提取Top问题
                top_issues = row.get('Top问题指标(按异常占比)', '')
                # 提取指标汇总统计
                metrics_summary = {}
                for col in df.columns:
                    if '__' in col:
                        metric_name, suffix = col.split('__', 1)
                        if metric_name not in metrics_summary:
                            metrics_summary[metric_name] = {}
                        metrics_summary[metric_name][suffix] = row[col]
                
                cursor.execute(f'''
                    INSERT INTO {table_name} 
                    (video_id, total_score, verdict, top_issues_json, metrics_summary_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    row.get('优秀帧占比', 0) * 100, 
                    row.get('视频判定', ''),
                    json.dumps(top_issues, ensure_ascii=False),
                    json.dumps(metrics_summary, ensure_ascii=False)
                ))
            print(f"[入库] 视频汇总数据")
        except Exception as e:
            print(f"[错误] 导入视频汇总数据失败: {e}")

    # 4. 导入关键帧分析详情
    kf_csv = os.path.join(kf_analysis_base, f"{view_angle_cn}_关键帧分析_逐帧详情.csv")
    if os.path.exists(kf_csv):
        try:
            df = pd.read_csv(kf_csv, encoding='utf-8-sig')
            if '视频ID' in df.columns:
                df = df[df['视频ID'] == video_id]
            
            # 根据视角选择表名
            table_name = "keyframe_analysis_details_front" if view_angle_cn == "正面" else "keyframe_analysis_details"
            
            cursor.execute(f"DELETE FROM {table_name} WHERE video_id = ?", (video_id,))
            
            for _, row in df.iterrows():
                frame_idx = int(row.get('帧序号', 0))
                event_name = row.get('关键帧名称', '')
                metrics = {}
                judgments = {}
                
                for col in df.columns:
                    if col in ['视频ID', '帧序号', '关键帧名称', '关键帧索引']:
                        continue
                    if '__' in col:
                        metric_name, suffix = col.split('__', 1)
                        if metric_name not in judgments:
                            judgments[metric_name] = {}
                        judgments[metric_name][suffix] = row[col]
                    else:
                        metrics[col] = row[col]
                
                cursor.execute(f'''
                    INSERT INTO {table_name} 
                    (video_id, frame_index, event_name, metrics_json, judgments_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    frame_idx,
                    event_name,
                    json.dumps(metrics, ensure_ascii=False),
                    json.dumps(judgments, ensure_ascii=False)
                ))
            print(f"[入库] 关键帧分析数据: {len(df)} 条")
        except Exception as e:
            print(f"[错误] 导入关键帧分析数据失败: {e}")
            
    conn.commit()


def collect_analysis_results(video_id, view_angle, analysis_dir=None, kf_analysis_dir=None, kp_dir=None):
    """收集并存储分析结果到数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 确保view_angle是中文（侧面/正面）
    view_mapping = {"side": "侧面", "front": "正面", "侧面": "侧面", "正面": "正面"}
    view_angle_cn = view_mapping.get(view_angle, view_angle)
    
    # 调用数据入库函数
    ingest_analysis_data(conn, video_id, view_angle_cn, kp_dir, analysis_dir, kf_analysis_dir)
    
    # Use provided directories or fall back to config
    analysis_base = analysis_dir if analysis_dir else config.ANALYSIS_CONFIG['OUTPUT_DIR']
    kf_analysis_base = kf_analysis_dir if kf_analysis_dir else config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR']

    # 逐帧分析结果
    frame_csv = os.path.join(analysis_base, f"{view_angle_cn}_逐帧审判结果.csv")
    video_summary_csv = os.path.join(analysis_base, f"{view_angle_cn}_视频级审判汇总.csv")
    
    # 关键帧分析结果
    keyframe_csv = os.path.join(kf_analysis_base, f"{view_angle_cn}_关键帧分析_逐帧详情.csv")
    keyframe_summary_csv = os.path.join(kf_analysis_base, f"{view_angle_cn}_关键帧分析_视频汇总.csv")
    
    # 可视化视频 (检查多种扩展名)
    vis_video = None
    for ext in ['.mp4', '.webm']:
        path = os.path.join(config.VISUALIZATION_CONFIG['OUTPUT_DIR'], f"{video_id}_{view_angle_cn}_可视化{ext}")
        if os.path.exists(path):
            vis_video = path
            break
            
    skeleton_video = None
    for ext in ['.mp4', '.webm']:
        path = os.path.join(config.VISUALIZATION_CONFIG['OUTPUT_DIR'], f"{video_id}_{view_angle_cn}_skeleton{ext}")
        if os.path.exists(path):
            skeleton_video = path
            break
    
    # 关键帧图片目录
    keyframe_dir = None
    for root, dirs, files in os.walk(config.KEYFRAME_CONFIG['OUTPUT_DIR']):
        if video_id in root or any(video_id in f for f in files):
            keyframe_dir = root
            break
    
    # 如果找不到，查找最新的目录
    if not keyframe_dir:
        output_dirs = list(Path(config.KEYFRAME_CONFIG['OUTPUT_DIR']).glob('*'))
        if output_dirs:
            keyframe_dir = str(max(output_dirs, key=lambda p: p.stat().st_mtime))
    
    # 读取关键帧索引
    keyframes_json = None
    if keyframe_dir:
        events_file = os.path.join(keyframe_dir, 'events.json')
        if os.path.exists(events_file):
            with open(events_file, 'r', encoding='utf-8') as f:
                keyframes_json = f.read()
            print(f"[收集结果] 找到关键帧数据: {events_file}")
        else:
            print(f"[收集结果] 未找到events.json: {events_file}")
    
    # 读取视频级汇总
    video_summary_json = None
    if os.path.exists(video_summary_csv):
        df = pd.read_csv(video_summary_csv, encoding='utf-8-sig')
        video_row = df[df['视频ID'] == video_id]
        if not video_row.empty:
            video_summary_json = video_row.iloc[0].to_json(force_ascii=False)
    
    # 生成并保存 AI 反馈（双语版本）
    ai_feedback = {'zh': None, 'en': None}
    try:
        print(f"[AI] 开始生成双语反馈: video={video_id}, view={view_angle_cn}")
        ai_feedback = generate_ai_feedback_bilingual(video_id, view_angle_cn, kf_analysis_dir)
        if ai_feedback['zh']:
            print(f"[AI] 双语反馈生成成功 - 中文: {len(ai_feedback['zh'])} 字符, 英文: {len(ai_feedback['en'] or 'N/A')} 字符")
        else:
            print(f"[AI] 双语反馈生成失败")
    except Exception as e:
        print(f"[AI] 生成反馈时出错: {e}")

    # 插入逐帧分析结果
    cursor.execute('''
        INSERT INTO analysis_results 
        (video_id, view_angle, analysis_type, csv_path, visualization_path, 
         skeleton_video_path, keyframes_json, video_summary_json, ai_feedback_html_zh, ai_feedback_html_en, created_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        video_id, view_angle_cn, 'frame_by_frame',
        frame_csv if os.path.exists(frame_csv) else None,
        vis_video if os.path.exists(vis_video) else None,
        skeleton_video if os.path.exists(skeleton_video) else None,
        keyframes_json,
        video_summary_json,
        ai_feedback['zh'],
        ai_feedback['en'],
        datetime.now().isoformat()
    ))
    
    # 插入关键帧分析结果
    if os.path.exists(keyframe_csv):
        cursor.execute('''
            INSERT INTO analysis_results 
            (video_id, view_angle, analysis_type, csv_path, keyframes_json, ai_feedback_html_zh, ai_feedback_html_en, created_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (video_id, view_angle_cn, 'keyframe', keyframe_csv, keyframes_json, ai_feedback['zh'], ai_feedback['en'], datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def update_video_status(video_id, status):
    """更新视频处理状态"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE videos SET status = ? WHERE video_id = ?', (status, video_id))
    conn.commit()
    conn.close()


@app.route('/videos')
def list_videos():
    """获取所有视频列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT video_id, original_filename, renamed_filename, view_angle, upload_time, status, total_frames, thumbnail_path
        FROM videos ORDER BY upload_time DESC
    ''')
    videos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(videos)


@app.route('/videos/delete', methods=['POST'])
def delete_videos():
    """删除视频及相关数据"""
    data = request.get_json()
    video_ids = data.get('video_ids', [])
    
    if not video_ids:
        return jsonify({'error': '未指定要删除的视频'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    deleted_count = 0
    errors = []
    
    for video_id in video_ids:
        try:
            # 1. 获取视频信息以找到文件路径
            cursor.execute('SELECT renamed_filename, thumbnail_path FROM videos WHERE video_id = ?', (video_id,))
            video = cursor.fetchone()
            
            if not video:
                continue
                
            # 2. 删除物理文件
            # 删除视频文件
            if video['renamed_filename']:
                video_path = os.path.join(app.config['UPLOAD_FOLDER'], video['renamed_filename'])
                if os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except Exception as e:
                        print(f"删除视频文件失败: {e}")
                
            # 删除缩略图
            if video['thumbnail_path']:
                # thumbnail_path 是相对路径 /static/thumbnails/xxx.jpg
                # 需要转换为绝对路径
                thumb_rel_path = video['thumbnail_path'].lstrip('/')
                # 处理可能的路径分隔符差异
                thumb_rel_path = thumb_rel_path.replace('/', os.sep).replace('\\', os.sep)
                thumb_path = os.path.join(app.root_path, thumb_rel_path)
                if os.path.exists(thumb_path):
                    try:
                        os.remove(thumb_path)
                    except Exception as e:
                        print(f"删除缩略图失败: {e}")
            
            # 3. 删除数据库记录
            # 删除所有相关表中的记录
            tables_to_clean = [
                'frame_analysis_details',
                'frame_analysis_details_front',
                'video_analysis_summary',
                'video_analysis_summary_front',
                'keyframe_analysis_details',
                'keyframe_analysis_details_front',
                'keypoints_data',
                'analysis_results',
                'videos'
            ]
            
            for table in tables_to_clean:
                try:
                    cursor.execute(f'DELETE FROM {table} WHERE video_id = ?', (video_id,))
                except sqlite3.OperationalError:
                    # 忽略表不存在的错误
                    pass
            
            deleted_count += 1
            
        except Exception as e:
            errors.append(f"删除视频 {video_id} 失败: {str(e)}")
            print(f"删除过程出错: {e}")
            
    conn.commit()
    conn.close()
    
    if errors:
        return jsonify({'message': f'成功删除 {deleted_count} 个视频，但有错误发生', 'errors': errors}), 207
    
    return jsonify({'message': f'成功删除 {deleted_count} 个视频'})


@app.route('/videos/<video_id>')
def get_video_info(video_id):
    """获取视频详细信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,))
    video = cursor.fetchone()
    
    if not video:
        conn.close()
        return jsonify({'error': '视频不存在'}), 404
    
    # 获取分析结果
    cursor.execute('SELECT * FROM analysis_results WHERE video_id = ?', (video_id,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'video': dict(video),
        'analysis_results': results
    })


@app.route('/analysis/<video_id>')
def get_analysis_data(video_id):
    """获取分析数据（逐帧和关键帧）"""
    analysis_type = request.args.get('type', 'frame_by_frame')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取视频视角
    cursor.execute('SELECT view_angle FROM videos WHERE video_id = ?', (video_id,))
    video_row = cursor.fetchone()
    view_angle = video_row['view_angle'] if video_row else '侧面'
    view_mapping = {"side": "侧面", "front": "正面", "侧面": "侧面", "正面": "正面"}
    view_angle_cn = view_mapping.get(view_angle, view_angle)
    
    cursor.execute('''
        SELECT * FROM analysis_results 
        WHERE video_id = ? AND analysis_type = ?
    ''', (video_id, analysis_type))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': '未找到分析记录'}), 404

    # 获取中英文 AI 反馈
    try:
        ai_feedback = {
            'zh': result['ai_feedback_html_zh'] if 'ai_feedback_html_zh' in result.keys() else None,
            'en': result['ai_feedback_html_en'] if 'ai_feedback_html_en' in result.keys() else None
        }
    except (KeyError, TypeError):
        ai_feedback = {'zh': None, 'en': None}
    
    if not result['csv_path']:
        return jsonify({'error': 'CSV路径未设置'}), 404
        
    if not os.path.exists(result['csv_path']):
        return jsonify({'error': f'CSV文件不存在: {result["csv_path"]}'}), 404
    
    # 读取CSV数据
    try:
        df = pd.read_csv(result['csv_path'], encoding='utf-8-sig')
        # print(f"[调试] 加载CSV成功: {result['csv_path']}, 行数: {len(df)}, 列: {list(df.columns)}")
    except Exception as e:
        return jsonify({'error': f'读取CSV失败: {str(e)}'}), 500
    
    # 筛选该视频的数据（如果有视频ID列）
    if '视频ID' in df.columns:
        original_len = len(df)
        df = df[df['视频ID'] == video_id]
        # print(f"[调试] 筛选后行数: {len(df)} (原始: {original_len})")
        if len(df) == 0:
            print(f"[警告] 筛选后数据为空，视频ID不匹配: {video_id}")
    
    # 如果是关键帧分析，需要进行透视转换 (Long -> Wide) 并补充帧号
    if analysis_type == 'keyframe':
        # 1. 获取关键帧帧号
        # 优先从当前记录获取，如果没有则尝试从 frame_by_frame 记录获取
        keyframes = []
        kf_json_str = result['keyframes_json']
        
        if not kf_json_str:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT keyframes_json FROM analysis_results 
                WHERE video_id = ? AND analysis_type = 'frame_by_frame'
            ''', (video_id,))
            fbf_row = cursor.fetchone()
            conn.close()
            if fbf_row:
                kf_json_str = fbf_row['keyframes_json']
        
        if kf_json_str:
            try:
                kf_data = json.loads(kf_json_str)
                # 兼容不同格式: {"events": [...]} 或 [...]
                if isinstance(kf_data, dict) and 'events' in kf_data:
                    keyframes = kf_data['events']
                elif isinstance(kf_data, list):
                    keyframes = kf_data
            except:
                pass
        
        # 2. 透视数据
        # 假设列: video_id, event_index, metric, value, low_th_q20, high_th_q80, label
        wide_data = []
        if not df.empty and 'event_index' in df.columns:
            grouped = df.groupby('event_index')
            for event_idx, group in grouped:
                row = {
                    'video_id': video_id,
                    'event_index': int(event_idx),
                    'abs_frame': keyframes[int(event_idx)-1] if (0 <= int(event_idx)-1 < len(keyframes)) else None
                }
                
                defect_count = 0
                worst_label_rank = 0 # 0:normal, 1:slight, 2:severe
                worst_label = 'normal'
                
                for _, item in group.iterrows():
                    metric = item['metric']
                    row[metric] = item['value']
                    
                    # 处理 label，确保不是 NaN
                    label = item.get('label')
                    if pd.isna(label) or str(label).lower() == 'nan':
                        label = 'normal'
                    row[f"{metric}__label"] = label
                    
                    row[f"{metric}__low_q20"] = item.get('low_th_q20')
                    row[f"{metric}__high_q80"] = item.get('high_th_q80')
                    
                    # 统计缺陷
                    if label != 'normal':
                        defect_count += 1
                        rank = 2 if label == 'severe_insufficient' else 1
                        if rank > worst_label_rank:
                            worst_label_rank = rank
                            worst_label = label
                
                row['defect_count'] = defect_count
                row['worst_label'] = worst_label
                wide_data.append(row)
        
        data = wide_data
    else:
        # 逐帧分析保持原样
        data = df.to_dict(orient='records')
    
    # 尝试从数据库获取更详细的汇总信息（如果CSV中没有）
    video_summary = json.loads(result['video_summary_json']) if result['video_summary_json'] else None
    
    # 如果是正面视角，尝试从正面汇总表获取
    if not video_summary and view_angle_cn == '正面':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM video_analysis_summary_front WHERE video_id = ?', (video_id,))
        summary_row = cursor.fetchone()
        conn.close()
        if summary_row:
            video_summary = {
                'total_score': summary_row['total_score'],
                'verdict': summary_row['verdict'],
                'top_issues': json.loads(summary_row['top_issues_json']) if summary_row['top_issues_json'] else [],
                'metrics_summary': json.loads(summary_row['metrics_summary_json']) if summary_row['metrics_summary_json'] else {}
            }

    return jsonify({
        'video_id': video_id,
        'analysis_type': analysis_type,
        'data': data,
        'columns': list(df.columns),
        'total_frames': len(data),
        'keyframes': json.loads(result['keyframes_json']) if result['keyframes_json'] else None,
        'video_summary': video_summary
        , 'ai_feedback': ai_feedback
    })


@app.route('/keyframe_csv/<video_id>')
def get_keyframe_csv(video_id):
    """直接读取 Keyframe_analysis 输出的逐帧详情 CSV（宽格式返回），用于前端回退或调试"""
    view = request.args.get('view', None)
    view_mapping = {"side": "侧面", "front": "正面", "侧面": "侧面", "正面": "正面"}
    view_cn = view_mapping.get(view, None)

    # 如果未指定 view，尝试从 videos 表中查
    conn = get_db()
    cursor = conn.cursor()
    if not view_cn:
        cursor.execute('SELECT view_angle FROM videos WHERE video_id = ?', (video_id,))
        row = cursor.fetchone()
        view_cn = view_mapping.get(row['view_angle'], '侧面') if row else '侧面'

    kf_csv = os.path.join(config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR'], f"{view_cn}_关键帧分析_逐帧详情.csv")
    if not os.path.exists(kf_csv):
        conn.close()
        return jsonify({'error': f'Keyframe CSV not found: {kf_csv}'}), 404

    try:
        df = pd.read_csv(kf_csv, encoding='utf-8-sig')
    except Exception as e:
        conn.close()
        return jsonify({'error': f'读取Keyframe CSV失败: {str(e)}'}), 500

    # 筛选视频
    if 'video_id' in df.columns:
        df = df[df['video_id'] == video_id]

    # 如果为空，返回空列表
    if df.empty:
        conn.close()
        return jsonify({'video_id': video_id, 'data': [], 'events': []})

    # 透视成长格式（每个 event_index 一行，包含指标列）
    wide_data = []
    if 'event_index' in df.columns:
        grouped = df.groupby('event_index')
        for event_idx, group in grouped:
            row = {'video_id': video_id, 'event_index': int(event_idx)}
            # 如果 CSV 中有 abs_frame/real_frame 字段，优先使用
            if 'abs_frame' in group.columns:
                row['abs_frame'] = int(group['abs_frame'].dropna().iloc[0]) if not group['abs_frame'].dropna().empty else None
            elif 'real_frame' in group.columns:
                row['real_frame'] = int(group['real_frame'].dropna().iloc[0]) if not group['real_frame'].dropna().empty else None

            for _, item in group.iterrows():
                metric = item['metric'] if 'metric' in item else None
                if metric:
                    row[metric] = item.get('value')
                    row[f"{metric}__low_q20"] = item.get('low_th_q20')
                    row[f"{metric}__high_q80"] = item.get('high_th_q80')
                    lab = item.get('label')
                    row[f"{metric}__label"] = lab
            # 统计缺陷数与最严重标签
            defect_count = 0
            worst_rank = 0
            worst_label = 'normal'
            for k, v in list(row.items()):
                if k.endswith('__label'):
                    lbl = row.get(k)
                    if lbl and lbl != 'normal' and str(lbl).lower() != 'nan':
                        defect_count += 1
                        rank = 2 if lbl == 'severe_insufficient' else 1
                        if rank > worst_rank:
                            worst_rank = rank
                            worst_label = lbl
            row['defect_count'] = defect_count
            row['worst_label'] = worst_label
            wide_data.append(row)
    else:
        # 如果已经是宽格式则直接返回记录
        wide_data = df.to_dict(orient='records')

    # 生成 events 列表（abs_frame 列）
    events = [r.get('abs_frame') for r in sorted(wide_data, key=lambda x: x.get('event_index', 0))]
    conn.close()
    return jsonify({'video_id': video_id, 'data': wide_data, 'events': events})


@app.route('/metrics')
def get_metrics():
    """获取所有指标及标准范围"""
    view_angle = request.args.get('view_angle', '侧面')
    analysis_type = request.args.get('type', 'frame_by_frame')
    
    # 映射视图角度到中文
    view_mapping = {"side": "侧面", "front": "正面", "侧面": "侧面", "正面": "正面"}
    view_angle_cn = view_mapping.get(view_angle, view_angle)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM metric_standards 
        WHERE view_angle = ? AND analysis_type = ?
    ''', (view_angle_cn, analysis_type))
    metrics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    print(f"[调试] 获取指标标准: 视角={view_angle_cn}, 类型={analysis_type}, 数量={len(metrics)}")
    return jsonify(metrics)


@app.route('/video_file/<video_id>/<video_type>')
def serve_video(video_id, video_type):
    """提供视频文件流"""
    # print(f"[serve_video] 请求视频 - ID: {video_id}, 类型: {video_type}")
    
    conn = get_db()
    cursor = conn.cursor()
    video_path = None
    
    try:
        if video_type == 'original':
            cursor.execute('SELECT video_path FROM videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            video_path = row['video_path'] if row else None
            # print(f"[serve_video] 原始视频路径: {video_path}")
            
        elif video_type == 'visualization':
            cursor.execute('''
                SELECT visualization_path FROM analysis_results 
                WHERE video_id = ? AND analysis_type = "frame_by_frame"
                ORDER BY created_time DESC LIMIT 1
            ''', (video_id,))
            row = cursor.fetchone()
            video_path = row['visualization_path'] if row else None
            # print(f"[serve_video] 可视化视频路径: {video_path}")
            
        elif video_type == 'skeleton':
            # 先尝试从analysis_results查询
            cursor.execute('''
                SELECT skeleton_video_path FROM analysis_results 
                WHERE video_id = ? AND analysis_type = "frame_by_frame"
                ORDER BY created_time DESC LIMIT 1
            ''', (video_id,))
            row = cursor.fetchone()
            video_path = row['skeleton_video_path'] if row else None
            # print(f"[serve_video] 骨架视频查询结果: {video_path}")
            
            # 如果路径为None或空，尝试根据video_id和view_angle构造路径
            if not video_path:
                cursor.execute('SELECT view_angle FROM videos WHERE video_id = ?', (video_id,))
                video_row = cursor.fetchone()
                if video_row:
                    view_angle = video_row['view_angle']
                    # 映射到中文
                    view_mapping = {"side": "侧面", "front": "正面", "侧面": "侧面", "正面": "正面"}
                    view_angle_cn = view_mapping.get(view_angle, view_angle)
                    
                    # 尝试多种扩展名
                    for ext in ['.mp4', '.webm']:
                        constructed_path = os.path.join(config.VISUALIZATION_CONFIG['OUTPUT_DIR'], f"{video_id}_{view_angle_cn}_skeleton{ext}")
                        # print(f"[serve_video] 尝试构造路径: {constructed_path}")
                        if os.path.exists(constructed_path):
                            video_path = constructed_path
                            # print(f"[serve_video] 使用构造的路径: {video_path}")
                            break
        else:
            conn.close()
            return jsonify({'error': '无效的视频类型'}), 400
        
        conn.close()
        
        if not video_path:
            # print(f"[serve_video] 错误: 数据库中未找到视频路径")
            return jsonify({'error': '视频路径未找到，可能分析尚未完成'}), 404
            
        if not os.path.exists(video_path):
            # print(f"[serve_video] 错误: 视频文件不存在 - {video_path}")
            return jsonify({'error': f'视频文件不存在: {os.path.basename(video_path)}'}), 404
        
        # print(f"[serve_video] 发送视频文件: {video_path} (大小: {os.path.getsize(video_path)} bytes)")
        
        # 确定MIME类型
        mimetype = 'video/mp4'
        if video_path.lower().endswith('.webm'):
            mimetype = 'video/webm'
        
        # 创建响应，支持Range请求和CORS
        response = send_file(
            video_path, 
            mimetype=mimetype,
            as_attachment=False,
            conditional=True  # 启用条件请求支持（Range）
        )
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        print(f"[serve_video] 异常: {str(e)}")
        if conn:
            conn.close()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/analysis_page/<video_id>')
def analysis_page(video_id):
    """分析结果展示页面"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT view_angle FROM videos WHERE video_id = ?', (video_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row['view_angle'] == '正面':
        return render_template('analysis_front.html', video_id=video_id)
    
    return render_template('analysis.html', video_id=video_id)


@app.route('/test_video')
def test_video():
    """视频加载测试页面"""
    return render_template('test_video.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)


if __name__ == '__main__':
    # 初始化数据库
    init_db()
    load_metric_standards()
    
    print("=" * 60)
    print("高尔夫挥杆分析系统启动")
    print("访问地址: http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
