import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
import json

# Add current directory to sys.path to allow importing local modules
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    import 正面提取指标 as front_metrics
    import 侧面提取指标 as side_metrics
    import 正面缺陷判断 as front_judge
    import 侧面缺陷判断 as side_judge
except ImportError as e:
    print(f"[ERROR] Failed to import keyframe analysis modules: {e}")
    # Fallback or re-raise depending on needs
    raise

def run_keyframe_analysis(view, input_csv, out_dir, events, num_events, std_csv=None):
    """
    Run keyframe analysis pipeline.
    
    Args:
        view (str): 'side' or 'front'
        input_csv (str): Path to keypoints CSV
        out_dir (str): Output directory
        events (list or np.array): List of event frame indices
        num_events (int): Number of events (8 or 9)
        std_csv (str): Path to standard ranges CSV
        
    Returns:
        tuple: (frame_out_path, video_out_path, summary_df)
    """
    print(f"[Keyframe Analysis] View: {view}, Events: {events}")
    
    # 1. Load Keypoints
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Keypoints CSV not found: {input_csv}")
    
    df_pts = pd.read_csv(input_csv)
    
    # Extract video_id from input_csv or assume single video
    # Usually input_csv contains one video's data
    if 'video_id' in df_pts.columns:
        video_ids = df_pts['video_id'].unique()
        video_id = video_ids[0] if len(video_ids) > 0 else "unknown"
    else:
        video_id = "unknown"
        df_pts['video_id'] = video_id # Add dummy video_id if missing
        
    # Ensure events is numpy array
    if isinstance(events, list):
        events_abs = np.array(events)
    else:
        events_abs = events
        
    # 2. Calculate Metrics
    if view == 'front':
        metrics_list = front_metrics.calculate_metrics(df_pts, events_abs, video_id)
    else:
        metrics_list = side_metrics.calculate_metrics(df_pts, events_abs, video_id)
        
    if not metrics_list:
        print("[Keyframe Analysis] No metrics calculated.")
        return None, None, None
        
    df_metrics = pd.DataFrame(metrics_list)
    
    # 3. Judge Defects
    if not std_csv or not os.path.exists(std_csv):
        # Try to find default if not provided
        if view == 'front':
            std_csv = str(current_dir / "正面normal_ranges_face_on_60_20_20.csv")
        else:
            std_csv = str(current_dir / "侧面normal_ranges_down_the_line_60_20_20.csv")
            
    if not os.path.exists(std_csv):
        print(f"[Keyframe Analysis] Standard ranges file not found: {std_csv}")
        # Return metrics without judgment? Or fail?
        # Let's try to proceed if possible, but judge_defects needs it.
        return None, None, None

    print(f"[Keyframe Analysis] Using standards: {std_csv}")
    
    if view == 'front':
        df_wide, df_long = front_judge.judge_defects(df_metrics, std_csv)
    else:
        df_wide, df_long = side_judge.judge_defects(df_metrics, std_csv)
        
    # 4. Save Results
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    
    view_cn = "正面" if view == 'front' else "侧面"
    
    out_wide_path = os.path.join(out_dir, f"{view_cn}_关键帧分析_视频汇总.csv")
    out_long_path = os.path.join(out_dir, f"{view_cn}_关键帧分析_逐帧详情.csv")
    
    df_wide.to_csv(out_wide_path, index=False, encoding="utf-8-sig")
    df_long.to_csv(out_long_path, index=False, encoding="utf-8-sig")
    
    print(f"[Keyframe Analysis] Results saved to:")
    print(f"  - {out_wide_path}")
    print(f"  - {out_long_path}")
    
    return out_long_path, out_wide_path, df_wide

if __name__ == "__main__":
    # Test run
    pass
