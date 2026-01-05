import os
import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp

def landmarks_to_np(landmarks):
    """
    将 pose_landmarks.landmark 转为 shape=(33,4) 的数组:
    [x, y, z, visibility]
    """
    if landmarks is None:
        return None
    arr = np.zeros((33, 4), dtype=np.float32)
    for i, lm in enumerate(landmarks):
        arr[i, 0] = lm.x
        arr[i, 1] = lm.y
        arr[i, 2] = lm.z
        arr[i, 3] = lm.visibility
    return arr

def process_video(video_path, output_dir, scale=1, model_complexity=1, video_id=None):
    # Reduce chances of native crashes / thread conflicts on Windows
    try:
        cv2.setNumThreads(0)
    except Exception:
        pass

    # ================== MediaPipe Pose 初始化 ==================
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=int(model_complexity),  # 2=最精准但最慢，1=中等，0=最快
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"[ERROR] 找不到视频文件: {video_path}")
        return None

    # 输出设置
    out_dir_path = Path(output_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    # 输出的 CSV 文件名
    csv_output = out_dir_path / "单视频_缺陷分析数据.csv"

    # 获取视频名作为 ID (用于记录)：去掉扩展名，避免后续分析强转 int 失败
    if video_id is None:
        video_filename = Path(video_path).stem
    else:
        video_filename = video_id

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] 无法打开视频: {video_path}")
        return None

    # 读取首帧，获取原始尺寸
    ret, first_frame = cap.read()
    if not ret or first_frame is None:
        print(f"[ERROR] 视频为空: {video_path}")
        cap.release()
        return None

    orig_h, orig_w = first_frame.shape[:2]
    up_w, up_h = int(orig_w * scale), int(orig_h * scale)

    # 回到第一帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    frame_idx = 0
    print(f"[INFO] 开始处理视频: {video_filename}")
    print(f"       原始尺寸=({orig_w},{orig_h}) -> 处理尺寸=({up_w},{up_h})")

    records = []
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        
        # 当前帧索引（从 0 开始）
        frame_idx_local = frame_idx
        frame_idx += 1

        # 1. 放大/调整尺寸
        if scale != 1:
            frame_proc = cv2.resize(frame, (up_w, up_h), interpolation=cv2.INTER_CUBIC)
        else:
            frame_proc = frame

        # 2. 转为 RGB 供 MediaPipe 使用
        rgb = cv2.cvtColor(frame_proc, cv2.COLOR_BGR2RGB)

        # 3. 推理
        result = pose.process(rgb)

        if result.pose_landmarks:
            arr = landmarks_to_np(result.pose_landmarks.landmark)
        else:
            arr = None

        # 4. 构建数据行
        # 为了兼容之前的格式，保留 video_id 字段，值为文件名
        row_dict = {
            "video_id": video_filename,
            "frame_index": frame_idx_local,
        }

        # 33 个关键点，每个点写一个 "(x,y,z)" 字符串
        if arr is not None:
            for lid in range(33):
                x = float(arr[lid, 0])
                y = float(arr[lid, 1])
                z = float(arr[lid, 2])
                # 注意：这里的 x,y 是归一化坐标(0~1)，对应的是 up_w, up_h 的比例
                coord_str = f"({x},{y},{z})"
                row_dict[f"landmark_{lid}"] = coord_str
        else:
            # 没检测到人体，全部写空字符串
            for lid in range(33):
                row_dict[f"landmark_{lid}"] = ""

        records.append(row_dict)

        # 可选：显示进度，每100帧打印一次
        if frame_idx % 100 == 0:
            print(f"       已处理 {frame_idx} 帧...")

    cap.release()
    print(f"[INFO] 视频处理完毕，共 {frame_idx} 帧。")

    # ================== 写入 CSV ==================
    if records:
        keypoints_df = pd.DataFrame.from_records(records)
        keypoints_df.to_csv(csv_output, index=False, encoding="utf-8-sig")
        print(f"\n[SUCCESS] 结果已保存至: {csv_output}")
        return str(csv_output)
    else:
        print("\n[WARNING] 未生成任何记录。")
        return None

if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    import config

    parser = argparse.ArgumentParser(description="Export Keypoints from Video")
    parser.add_argument("--video_path", type=str, required=True, help="Path to the input video")
    parser.add_argument("--output_dir", type=str, default=config.KEYPOINT_CONFIG['OUTPUT_DIR'], help="Directory to save the output CSV")
    parser.add_argument("--scale", type=float, default=config.KEYPOINT_CONFIG['SCALE_FACTOR'], help="Scale factor for resizing frames")
    parser.add_argument("--model_complexity", type=int, default=config.KEYPOINT_CONFIG['MODEL_COMPLEXITY'], choices=[0, 1, 2], help="MediaPipe Pose model complexity")
    
    args = parser.parse_args()
    
    process_video(args.video_path, args.output_dir, args.scale, model_complexity=args.model_complexity)
