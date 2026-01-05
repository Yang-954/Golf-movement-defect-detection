"""
可视化视频生成模块
功能：
1. 在原视频上绘制关键点和骨架
2. 在左侧添加画布显示每帧的参数指标
3. 显示每个指标的评判结果（标准/轻微/异常）
"""

import os
import cv2
import numpy as np
import pandas as pd
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# MediaPipe骨架连接定义 (33个关键点)
POSE_CONNECTIONS = [
    # 面部
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    # 躯干
    (9, 10), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    # 左臂
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    # 右臂
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    # 左腿
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    # 右腿
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
]


def parse_landmark(landmark_str):
    """解析关键点字符串 "(x, y, z)" 为numpy数组"""
    try:
        return np.array(ast.literal_eval(landmark_str))
    except:
        return np.array([np.nan, np.nan, np.nan])


def draw_pose_landmarks(frame, landmarks_2d, connections=POSE_CONNECTIONS):
    """
    在帧上绘制关键点和骨架连接
    landmarks_2d: shape (33, 2) 的像素坐标数组
    """
    h, w = frame.shape[:2]
    
    # 绘制骨架连接线
    for connection in connections:
        start_idx, end_idx = connection
        if start_idx < len(landmarks_2d) and end_idx < len(landmarks_2d):
            start_point = landmarks_2d[start_idx]
            end_point = landmarks_2d[end_idx]
            
            # 检查有效性
            if not (np.isnan(start_point).any() or np.isnan(end_point).any()):
                cv2.line(
                    frame,
                    tuple(start_point.astype(int)),
                    tuple(end_point.astype(int)),
                    color=(0, 255, 0),  # 绿色连接线
                    thickness=2
                )
    
    # 绘制关键点
    for i, point in enumerate(landmarks_2d):
        if not np.isnan(point).any():
            x, y = point.astype(int)
            # 不同部位使用不同颜色
            if i <= 10:  # 面部和头部
                color = (255, 0, 0)  # 蓝色
            elif i <= 16:  # 上身和手臂
                color = (0, 255, 255)  # 黄色
            else:  # 下身和腿部
                color = (255, 0, 255)  # 粉色
            
            cv2.circle(frame, (x, y), 4, color, -1)
            cv2.circle(frame, (x, y), 4, (255, 255, 255), 1)
    
    return frame


def create_info_panel(
    width: int,
    height: int,
    metrics: Dict[str, float],
    judgments: Dict[str, int],
    frame_idx: int,
    frame_conclusion: str = "优秀",
    frame_score: float = 100.0
) -> np.ndarray:
    """
    创建左侧信息面板
    width, height: 面板尺寸
    metrics: 指标值字典 {指标名: 值}
    judgments: 判断结果字典 {指标名: 0=标准, 1=轻微, 2=异常}
    frame_idx: 当前帧序号
    frame_conclusion: 帧级结论
    frame_score: 帧级评分
    """
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    panel[:] = (40, 40, 40)  # 深灰色背景
    
    # 标题
    cv2.putText(
        panel, f"Frame: {frame_idx}", (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
    )
    
    # 帧级评分和结论
    score_color = (0, 255, 0) if frame_score >= 90 else (0, 255, 255) if frame_score >= 70 else (0, 0, 255)
    cv2.putText(
        panel, f"Score: {frame_score:.1f}", (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2
    )
    cv2.putText(
        panel, f"Result: {frame_conclusion}", (10, 85),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, score_color, 1
    )
    
    # 分隔线
    cv2.line(panel, (10, 95), (width - 10, 95), (100, 100, 100), 1)
    
    # 显示各项指标（只显示前10个主要指标，避免过于拥挤）
    y_offset = 115
    line_height = 40
    font_scale = 0.4
    
    # 定义判断结果的颜色和文字
    judgment_info = {
        0: ("Standard", (0, 255, 0)),      # 绿色 - 标准
        1: ("Minor", (0, 255, 255)),       # 黄色 - 轻微
        2: ("Abnormal", (0, 0, 255)),      # 红色 - 异常
    }
    
    count = 0
    max_display = 12  # 最多显示12个指标
    
    for metric_name, value in metrics.items():
        if count >= max_display:
            break
        
        # 缩短指标名称以适应面板宽度
        short_name = metric_name[:30] + "..." if len(metric_name) > 30 else metric_name
        
        # 显示指标名称
        cv2.putText(
            panel, short_name, (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), 1
        )
        
        # 显示指标值
        value_str = f"{value:.2f}" if isinstance(value, (int, float)) and not np.isnan(value) else "N/A"
        cv2.putText(
            panel, value_str, (10, y_offset + 15),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1
        )
        
        # 显示判断结果
        judgment = judgments.get(metric_name, 0)
        judgment_text, judgment_color = judgment_info.get(judgment, ("Unknown", (128, 128, 128)))
        cv2.putText(
            panel, judgment_text, (10, y_offset + 30),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, judgment_color, 1
        )
        
        y_offset += line_height
        count += 1
    
    return panel


def generate_visualization_video(
    video_path: str,
    keypoints_csv: str,
    analysis_csv: str,
    output_path: str,
    panel_width: int = 400,
    fps: Optional[float] = None
):
    """
    生成可视化视频
    
    参数:
        video_path: 原始视频路径
        keypoints_csv: 关键点CSV文件路径
        analysis_csv: 分析结果CSV文件路径
        output_path: 输出视频路径
        panel_width: 左侧信息面板宽度
        fps: 输出视频帧率（None则使用原视频帧率）
    """
    print(f"[可视化] 开始生成可视化视频...")
    print(f"  - 原视频: {video_path}")
    print(f"  - 关键点数据: {keypoints_csv}")
    print(f"  - 分析数据: {analysis_csv}")
    
    # 读取数据
    try:
        keypoints_df = pd.read_csv(keypoints_csv)
        analysis_df = pd.read_csv(analysis_csv)
    except Exception as e:
        print(f"[错误] 读取CSV文件失败: {e}")
        return None
    
    print(f"  - 关键点数据: {len(keypoints_df)} 帧")
    print(f"  - 分析数据: {len(analysis_df)} 帧")
    
    # 打开原视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[错误] 无法打开视频文件: {video_path}")
        return None
    
    # 获取视频属性
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    output_fps = fps if fps is not None else original_fps
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"  - 原视频尺寸: {frame_width}x{frame_height}")
    print(f"  - 原视频帧率: {original_fps:.2f} fps")
    print(f"  - 总帧数: {total_frames}")
    
    # 创建输出视频
    output_width = panel_width + frame_width
    output_height = frame_height
    
    # 尝试不同的编码策略
    strategies = [
        {'codec': 'avc1', 'ext': '.mp4', 'name': 'H.264'},
        {'codec': 'vp80', 'ext': '.webm', 'name': 'VP8'},
        {'codec': 'mp4v', 'ext': '.mp4', 'name': 'MPEG-4'}
    ]
    
    out = None
    final_output_path = output_path
    
    for strategy in strategies:
        try:
            # 如果扩展名不匹配，修改输出路径
            current_ext = os.path.splitext(output_path)[1].lower()
            if current_ext != strategy['ext']:
                temp_path = os.path.splitext(output_path)[0] + strategy['ext']
            else:
                temp_path = output_path
                
            print(f"[尝试] 使用 {strategy['name']} ({strategy['codec']}) 输出到 {os.path.basename(temp_path)}")
            
            fourcc = cv2.VideoWriter_fourcc(*strategy['codec'])
            temp_out = cv2.VideoWriter(temp_path, fourcc, output_fps, (output_width, output_height))
            
            if temp_out.isOpened():
                out = temp_out
                final_output_path = temp_path
                print(f"[成功] 编码器初始化成功")
                break
            else:
                print(f"[失败] 无法初始化编码器")
        except Exception as e:
            print(f"[失败] 发生异常: {e}")
            continue
    
    if out is None or not out.isOpened():
        print(f"[错误] 无法创建输出视频，所有编码策略均失败")
        cap.release()
        return None
    
    # 如果最终路径与请求路径不同，打印提示
    if final_output_path != output_path:
        print(f"[提示] 输出文件路径已更改为: {final_output_path}")
        # 尝试删除旧扩展名的文件（如果存在）
        if os.path.exists(output_path) and output_path != final_output_path:
            try:
                os.remove(output_path)
            except:
                pass
    
    print(f"  - 输出视频尺寸: {output_width}x{output_height}")
    print(f"  - 输出帧率: {output_fps:.2f} fps")
    
    # 获取所有指标列名（用于显示）
    metric_columns = []
    judgment_columns = []
    
    for col in analysis_df.columns:
        if col.endswith("__审判_0标准1轻微2异常"):
            base_name = col.replace("__审判_0标准1轻微2异常", "")
            if base_name in analysis_df.columns:
                metric_columns.append(base_name)
                judgment_columns.append(col)
    
    print(f"  - 检测到 {len(metric_columns)} 个指标")
    
    # 逐帧处理
    frame_idx = 0
    processed_frames = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 获取当前帧的关键点数据
        if frame_idx < len(keypoints_df):
            kp_row = keypoints_df.iloc[frame_idx]
            
            # 提取关键点坐标
            landmarks_2d = []
            for i in range(33):
                col_name = f'landmark_{i}'
                if col_name in kp_row:
                    landmark_3d = parse_landmark(kp_row[col_name])
                    # 转换为像素坐标
                    x = landmark_3d[0] * frame_width
                    y = landmark_3d[1] * frame_height
                    landmarks_2d.append([x, y])
                else:
                    landmarks_2d.append([np.nan, np.nan])
            
            landmarks_2d = np.array(landmarks_2d)
            
            # 在视频帧上绘制关键点
            frame = draw_pose_landmarks(frame, landmarks_2d)
        
        # 获取当前帧的分析数据
        metrics = {}
        judgments = {}
        frame_conclusion = "优秀"
        frame_score = 100.0
        
        if frame_idx < len(analysis_df):
            analysis_row = analysis_df.iloc[frame_idx]
            
            # 提取指标和判断结果
            for metric_col, judgment_col in zip(metric_columns, judgment_columns):
                if metric_col in analysis_row and judgment_col in analysis_row:
                    metrics[metric_col] = analysis_row[metric_col]
                    judgments[metric_col] = int(analysis_row[judgment_col]) if not pd.isna(analysis_row[judgment_col]) else 0
            
            # 提取帧级结论和评分
            if "帧级结论_连续过滤后" in analysis_row:
                frame_conclusion = str(analysis_row["帧级结论_连续过滤后"])
            elif "帧级结论" in analysis_row:
                frame_conclusion = str(analysis_row["帧级结论"])
            
            if "帧级评分_0到100" in analysis_row:
                frame_score = float(analysis_row["帧级评分_0到100"])
        
        # 创建信息面板
        info_panel = create_info_panel(
            panel_width, frame_height,
            metrics, judgments,
            frame_idx, frame_conclusion, frame_score
        )
        
        # 合并信息面板和视频帧
        combined_frame = np.hstack([info_panel, frame])
        
        # 写入输出视频
        out.write(combined_frame)
        
        frame_idx += 1
        processed_frames += 1
        
        # 显示进度 (减少输出频率，每100帧或10%输出一次)
        if processed_frames % 100 == 0:
            progress = (processed_frames / total_frames) * 100 if total_frames > 0 else 0
            print(f"  - 处理进度: {processed_frames}/{total_frames} ({progress:.1f}%)")
    
    # 释放资源
    cap.release()
    out.release()
    
    print(f"[完成] 可视化视频已保存至: {final_output_path}")
    print(f"  - 共处理 {processed_frames} 帧")
    
    return final_output_path


def main():
    """命令行接口"""
    import argparse
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    import config
    
    parser = argparse.ArgumentParser(description="生成带关键点和参数指标的可视化视频")
    parser.add_argument("--video", type=str, required=True, help="原始视频路径")
    parser.add_argument("--keypoints", type=str, required=True, help="关键点CSV文件路径")
    parser.add_argument("--analysis", type=str, required=True, help="分析结果CSV文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出视频路径")
    parser.add_argument("--panel_width", type=int, default=config.VISUALIZATION_CONFIG['PANEL_WIDTH'], help="左侧面板宽度")
    parser.add_argument("--fps", type=float, default=None, help="输出视频帧率（默认使用原视频帧率）")
    
    args = parser.parse_args()
    
    generate_visualization_video(
        video_path=args.video,
        keypoints_csv=args.keypoints,
        analysis_csv=args.analysis,
        output_path=args.output,
        panel_width=args.panel_width,
        fps=args.fps
    )


def generate_skeleton_only_video(
    keypoints_csv: str,
    output_path: str,
    video_width: int = 1280,
    video_height: int = 720,
    fps: float = 30.0,
    background_color: Tuple[int, int, int] = (255, 255, 255)
):
    """
    生成纯骨架视频（白色背景）
    
    参数:
        keypoints_csv: 关键点CSV文件路径
        output_path: 输出视频路径
        video_width: 视频宽度
        video_height: 视频高度
        fps: 视频帧率
        background_color: 背景颜色 (B, G, R)，默认白色
    """
    print(f"[骨架视频] 开始生成纯骨架视频...")
    print(f"  - 关键点数据: {keypoints_csv}")
    print(f"  - 输出路径: {output_path}")
    
    # 读取关键点数据
    try:
        keypoints_df = pd.read_csv(keypoints_csv)
    except Exception as e:
        print(f"[错误] 读取CSV文件失败: {e}")
        return None
    
    print(f"  - 总帧数: {len(keypoints_df)}")
    
    # 创建输出视频
    # 尝试不同的编码策略
    # 1. H.264 (avc1) -> .mp4 (最通用)
    # 2. VP8 (vp80) -> .webm (浏览器友好)
    # 3. MPEG-4 (mp4v) -> .mp4 (兼容性一般)
    
    strategies = [
        {'codec': 'avc1', 'ext': '.mp4', 'name': 'H.264'},
        {'codec': 'vp80', 'ext': '.webm', 'name': 'VP8'},
        {'codec': 'mp4v', 'ext': '.mp4', 'name': 'MPEG-4'}
    ]
    
    out = None
    final_output_path = output_path
    
    for strategy in strategies:
        try:
            # 如果扩展名不匹配，修改输出路径
            current_ext = os.path.splitext(output_path)[1].lower()
            if current_ext != strategy['ext']:
                temp_path = os.path.splitext(output_path)[0] + strategy['ext']
            else:
                temp_path = output_path
                
            print(f"[尝试] 使用 {strategy['name']} ({strategy['codec']}) 输出到 {os.path.basename(temp_path)}")
            
            fourcc = cv2.VideoWriter_fourcc(*strategy['codec'])
            temp_out = cv2.VideoWriter(temp_path, fourcc, fps, (video_width, video_height))
            
            if temp_out.isOpened():
                out = temp_out
                final_output_path = temp_path
                print(f"[成功] 编码器初始化成功")
                break
            else:
                print(f"[失败] 无法初始化编码器")
        except Exception as e:
            print(f"[失败] 发生异常: {e}")
            continue
    
    if out is None or not out.isOpened():
        print(f"[错误] 无法创建输出视频，所有编码策略均失败")
        return None
    
    # 如果最终路径与请求路径不同，打印提示
    if final_output_path != output_path:
        print(f"[提示] 输出文件路径已更改为: {final_output_path}")
        # 尝试删除旧扩展名的文件（如果存在），避免混淆
        if os.path.exists(output_path) and output_path != final_output_path:
            try:
                os.remove(output_path)
            except:
                pass
    
    # 定义左右侧不同颜色
    left_color = (0, 0, 255)    # 红色 - 左侧
    right_color = (255, 0, 0)   # 蓝色 - 右侧
    center_color = (0, 255, 0)  # 绿色 - 中心
    
    # 定义左右侧关键点（MediaPipe编号）
    left_indices = {13, 15, 17, 19, 21, 23, 25, 27, 29, 31}  # 左侧关键点
    right_indices = {14, 16, 18, 20, 22, 24, 26, 28, 30, 32}  # 右侧关键点
    
    # 定义连接关系及其所属侧
    connections_with_side = []
    for start_idx, end_idx in POSE_CONNECTIONS:
        if start_idx in left_indices and end_idx in left_indices:
            side = 'left'
        elif start_idx in right_indices and end_idx in right_indices:
            side = 'right'
        else:
            side = 'center'
        connections_with_side.append((start_idx, end_idx, side))
    
    # 逐帧生成
    for frame_idx in range(len(keypoints_df)):
        # 创建白色背景
        frame = np.ones((video_height, video_width, 3), dtype=np.uint8) * np.array(background_color, dtype=np.uint8)
        
        # 获取当前帧的关键点数据
        kp_row = keypoints_df.iloc[frame_idx]
        
        # 提取关键点坐标
        landmarks_2d = []
        for i in range(33):
            col_name = f'landmark_{i}'
            if col_name in kp_row:
                landmark_3d = parse_landmark(kp_row[col_name])
                # 归一化坐标转换为像素坐标
                x = landmark_3d[0] * video_width
                y = landmark_3d[1] * video_height
                landmarks_2d.append([x, y])
            else:
                landmarks_2d.append([np.nan, np.nan])
        
        landmarks_2d = np.array(landmarks_2d)
        
        # 绘制骨架连接线（根据左右侧使用不同颜色）
        for start_idx, end_idx, side in connections_with_side:
            if start_idx < len(landmarks_2d) and end_idx < len(landmarks_2d):
                start_point = landmarks_2d[start_idx]
                end_point = landmarks_2d[end_idx]
                
                # 检查有效性
                if not (np.isnan(start_point).any() or np.isnan(end_point).any()):
                    if side == 'left':
                        color = left_color
                    elif side == 'right':
                        color = right_color
                    else:
                        color = center_color
                    
                    cv2.line(
                        frame,
                        tuple(start_point.astype(int)),
                        tuple(end_point.astype(int)),
                        color=color,
                        thickness=3
                    )
        
        # 绘制关键点（根据左右侧使用不同颜色）
        for i, point in enumerate(landmarks_2d):
            if not np.isnan(point).any():
                x, y = point.astype(int)
                
                # 判断关键点属于哪一侧
                if i in left_indices:
                    color = left_color
                elif i in right_indices:
                    color = right_color
                else:
                    color = center_color
                
                # 绘制实心圆
                cv2.circle(frame, (x, y), 6, color, -1)
                # 白色边框
                cv2.circle(frame, (x, y), 6, (0, 0, 0), 1)
        
        # 全部放在右上角
        margin = 20
        font = cv2.FONT_HERSHEY_SIMPLEX

        # 帧号（靠右）
        frame_text = f"Frame: {frame_idx}"
        ft_scale, ft_thick = 1.0, 2
        (ft_w, ft_h), _ = cv2.getTextSize(frame_text, font, ft_scale, ft_thick)
        ft_x = int(video_width - margin - ft_w)
        ft_y = int(margin + ft_h)
        cv2.putText(frame, frame_text, (ft_x, ft_y), font, ft_scale, (0, 0, 0), ft_thick)

        # 图例（垂直排列，靠右）
        legend_scale, legend_thick = 0.6, 1
        circle_r = 8
        legend_start_y = ft_y + 18
        line_spacing = 32

        legends = [("Left", left_color), ("Right", right_color), ("Center", center_color)]
        for i, (label, color) in enumerate(legends):
            cy = int(legend_start_y + i * line_spacing)
            cx = int(video_width - margin - circle_r)

            # 先绘制圆，再绘制文字（文字左对齐于圆的左侧）
            cv2.circle(frame, (cx, cy), circle_r, color, -1)
            cv2.circle(frame, (cx, cy), circle_r, (0, 0, 0), 1)

            (lbl_w, lbl_h), _ = cv2.getTextSize(label, font, legend_scale, legend_thick)
            lbl_x = int(cx - 8 - lbl_w)
            lbl_y = int(cy + lbl_h // 2)
            cv2.putText(frame, label, (lbl_x, lbl_y), font, legend_scale, (0, 0, 0), legend_thick)
        
        # 写入输出视频
        out.write(frame)
        
        # 显示进度
        if (frame_idx + 1) % 100 == 0:
            progress = ((frame_idx + 1) / len(keypoints_df)) * 100
            print(f"  - 处理进度: {frame_idx + 1}/{len(keypoints_df)} ({progress:.1f}%)")
    
    # 释放资源
    out.release()
    
    print(f"[完成] 骨架视频已保存至: {final_output_path}")
    print(f"  - 共生成 {len(keypoints_df)} 帧")
    
    return final_output_path


if __name__ == "__main__":
    main()
