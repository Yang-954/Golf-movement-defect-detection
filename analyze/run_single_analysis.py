import pandas as pd
import numpy as np
import os
import ast
import sys
import argparse

# Add current directory to path to import the judgment scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import 侧向标准判断 as side_judge
import 正面标准判断 as front_judge

def parse_landmark(s):
    try:
        # The string is like "(0.1, 0.2, 0.3)"
        return np.array(ast.literal_eval(s))
    except:
        return np.array([np.nan, np.nan, np.nan])

def calculate_metrics(df):
    lms = {}
    # We need landmarks 0-32
    for i in range(33):
        col = f'landmark_{i}'
        if col in df.columns:
            lms[i] = df[col].apply(parse_landmark)
            lms[i] = np.vstack(lms[i].values)
        else:
            lms[i] = np.zeros((len(df), 3))

    def vec(i, j):
        return lms[i] - lms[j]
    
    def mid(i, j):
        return (lms[i] + lms[j]) / 2

    # --- Side View Metrics ---
    # 1. 肩线与Z轴夹角 (Shoulder Line vs Z Axis)
    # Vector L(11) - R(12)
    shoulder_vec = vec(11, 12)
    # Angle with Z axis. Using atan2(x, z) gives angle from Z axis.
    side_shoulder_angle = np.degrees(np.arctan2(shoulder_vec[:, 0], shoulder_vec[:, 2]))
    
    # 2. 髋线与Z轴夹角 (Hip Line vs Z Axis)
    hip_vec = vec(23, 24)
    side_hip_angle = np.degrees(np.arctan2(hip_vec[:, 0], hip_vec[:, 2]))
    
    # 3. 身体平面与Y轴夹角 (Body Plane vs Y Axis)
    # Spine: MidHip to MidShoulder (Upwards)
    spine_vec = mid(11, 12) - mid(23, 24) 
    norm_spine = np.linalg.norm(spine_vec, axis=1)
    # Y axis is (0, 1, 0) in image coords (downwards).
    # We want angle with vertical.
    dot_y = spine_vec[:, 1] 
    # Angle with Y axis (0,1,0). 
    # If standing straight (spine up: 0, -1, 0), dot is -1, angle 180.
    body_plane_angle = np.degrees(np.arccos(np.clip(dot_y / (norm_spine + 1e-9), -1, 1)))
    
    # 4. Displacements (Side)
    # Relative to frame 0
    lh_x_disp = lms[23][:, 0] - lms[23][0, 0]
    rh_x_disp = lms[24][:, 0] - lms[24][0, 0]
    sc_x = mid(11, 12)[:, 0]
    sc_x_disp = sc_x - sc_x[0]
    lhand_x_disp = lms[15][:, 0] - lms[15][0, 0]
    
    # 8. 肩线旋转减髋线旋转
    rot_diff = side_shoulder_angle - side_hip_angle

    # --- Front View Metrics ---
    # 1. Left Hip X Displacement (Front)
    lh_x_disp_front = lh_x_disp
    rh_x_disp_front = rh_x_disp
    
    # 3. Torso Center Y Displacement
    torso_c = (mid(11, 12) + mid(23, 24)) / 2
    torso_y_disp = torso_c[:, 1] - torso_c[0, 1]
    
    # 4. Shoulder Center X Displacement (Front)
    sc_x_disp_front = sc_x_disp
    
    # 5. Shoulder Rotation Angle (Front) - Angle with X axis
    # atan2(z, x)
    front_shoulder_angle = np.degrees(np.arctan2(shoulder_vec[:, 2], shoulder_vec[:, 0]))
    
    # 6. Hip Rotation Angle (Front)
    front_hip_angle = np.degrees(np.arctan2(hip_vec[:, 2], hip_vec[:, 0]))

    metrics_df = pd.DataFrame({
        "视频ID": df["video_id"],
        "帧序号": df["frame_index"],
        
        # Side Metrics
        "肩线与Z轴夹角_度_左正右负_近端终点_XZ平面": side_shoulder_angle,
        "髋线与Z轴夹角_度_左正右负_近端终点_XZ平面": side_hip_angle,
        "身体平面与Y轴夹角_度_X轴为0向上为正_0到180": body_plane_angle,
        "左髋X轴位移": lh_x_disp,
        "右髋X轴位移": rh_x_disp,
        "肩线中心X轴位移": sc_x_disp,
        "左手X轴位移": lhand_x_disp,
        "肩线旋转减髋线旋转_度": rot_diff,
        
        # Front Metrics
        "左髋X轴位移_正面": lh_x_disp_front,
        "右髋X轴位移_正面": rh_x_disp_front,
        "躯干中点Y轴位移_正面": torso_y_disp,
        "肩线中心X轴位移_正面": sc_x_disp_front,
        "肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面": front_shoulder_angle,
        "髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面": front_hip_angle,
    })
    
    return metrics_df


def run_analysis(view: str, input_csv: str, std_csv: str | None = None, out_dir: str | None = None):
    """Run side/front analysis and return (frame_out, video_out, summary_df)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if std_csv is None:
        std_csv = os.path.join(base_dir, "侧面标准范围.csv" if view == "side" else "正面标准范围.csv")
    if out_dir is None:
        out_dir = os.path.join(base_dir, "output")

    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Input file not found: {input_csv}")
    if not os.path.exists(std_csv):
        raise FileNotFoundError(f"Standard file not found: {std_csv}")

    df = pd.read_csv(input_csv)

    # Clean video_id: keep as video name (string). If it still contains an extension, strip it.
    df['video_id'] = df.get('video_id', '').astype(str).str.replace('.mp4', '', regex=False)


    metrics_df = calculate_metrics(df)
    rule_table = pd.read_csv(std_csv)
    rule_table["权重"] = pd.to_numeric(rule_table["权重"], errors='coerce').fillna(1.0)

    if view == 'side':
        # 只保留侧面指标
        side_metrics = side_judge.METRICS
        metrics_df = metrics_df[[c for c in metrics_df.columns if c in ["视频ID", "帧序号"] + side_metrics]]
        judged = side_judge.apply_rules_per_metric(metrics_df, rule_table)
        judged = side_judge.add_streak_filter(judged, min_streak=3)
        summary = side_judge.video_level_summary(judged, rule_table)
        frame_out = os.path.join(out_dir, "侧面_逐帧审判结果.csv")
        video_out = os.path.join(out_dir, "侧面_视频级审判汇总.csv")
    elif view == 'front':
        # 只保留正面指标
        front_metrics = front_judge.METRICS
        metrics_df = metrics_df[[c for c in metrics_df.columns if c in ["视频ID", "帧序号"] + front_metrics]]
        judged = front_judge.apply_rules_per_metric(metrics_df, rule_table)
        judged = front_judge.add_streak_filter(judged, min_streak=3)
        summary = front_judge.video_level_summary(judged)
        frame_out = os.path.join(out_dir, "正面_逐帧审判结果.csv")
        video_out = os.path.join(out_dir, "正面_视频级审判汇总.csv")
    else:
        raise ValueError("view must be 'side' or 'front'")

    judged.to_csv(frame_out, index=False, encoding="utf-8-sig")
    summary.to_csv(video_out, index=False, encoding="utf-8-sig")
    return frame_out, video_out, summary

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    import config

    parser = argparse.ArgumentParser(description="Golf Swing Analysis")
    parser.add_argument("--view", type=str, required=True, choices=['side', 'front'], help="View to analyze: 'side' or 'front'")
    parser.add_argument("--input_csv", type=str, required=True, help="Input landmark CSV path")
    parser.add_argument("--std_csv", type=str, default=None, help="Standard range CSV path. Defaults to preset files if None.")
    parser.add_argument("--out_dir", type=str, default=config.ANALYSIS_CONFIG['OUTPUT_DIR'], help="Output directory")

    args = parser.parse_args()
    
    # Determine std_csv if not provided
    if args.std_csv is None:
        if args.view == 'side':
            std_csv_path = config.ANALYSIS_CONFIG['STD_SIDE_PATH']
        else:
            std_csv_path = config.ANALYSIS_CONFIG['STD_FRONT_PATH']
    else:
        std_csv_path = args.std_csv

    frame_out, video_out, _summary = run_analysis(
        view=args.view,
        input_csv=args.input_csv,
        std_csv=std_csv_path,
        out_dir=args.out_dir,
    )
    print(f"Saved frame-level results to: {frame_out}")
    print(f"Saved video-level results to: {video_out}")