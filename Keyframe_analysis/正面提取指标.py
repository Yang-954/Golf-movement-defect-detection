import re
import ast
import math
import numpy as np
import pandas as pd
from pathlib import Path

# ======================= 路径配置 =======================
POINTS_CSV = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\正面\用于分析缺陷的点数据_face_on.csv"
EVENTS_CSV = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\正面\关键帧数据_face_on.csv"
OUT_CSV    = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\正面\缺陷指标结果_face_on.csv"
# =======================================================

# ---------------- MediaPipe Pose index -----------------
L_SHOULDER = 11
R_SHOULDER = 12
L_HIP      = 23
R_HIP      = 24
L_WRIST    = 15
# ------------------------------------------------------


# ======================= 解析函数 =======================
def parse_xyz(s):
    if pd.isna(s):
        return np.array([np.nan, np.nan, np.nan], dtype=np.float32)
    try:
        x, y, z = ast.literal_eval(str(s))
        return np.array([float(x), float(y), float(z)], dtype=np.float32)
    except Exception:
        return np.array([np.nan, np.nan, np.nan], dtype=np.float32)

def parse_events(val):
    """
    兼容解析 events 字段：
    - "[408 455 473 ...]" 或 "[408,455,...]" 或 "408 455 ..."
    """
    if pd.isna(val):
        return np.array([], dtype=int)
    s = str(val).strip()
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, (list, tuple, np.ndarray)):
            return np.array(obj, dtype=int)
    except Exception:
        pass
    nums = re.findall(r"-?\d+", s)
    return np.array([int(x) for x in nums], dtype=int)


# ======================= 几何计算 =======================
def tilt_deg_xy(pL, pR, eps=1e-8):
    """
    正面“倾斜(roll)”：肩线/髋线在 XY 平面相对水平(X轴)的角度
    angle = atan2(dy, dx)  -> [-180, 180]
    """
    dx = float(pR[0] - pL[0])
    dy = float(pR[1] - pL[1])
    if abs(dx) < eps and abs(dy) < eps:
        return np.nan
    return math.degrees(math.atan2(dy, dx))

def angle_with_yz_plane(p_top, p_bottom):
    """
    身体倾斜角：身体轴线 与 YZ 面的夹角（0 表示在 YZ 面内）
    """
    body_vec = p_top - p_bottom
    nx = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # YZ面法向=X轴
    n1 = float(np.linalg.norm(body_vec))
    if n1 < 1e-8:
        return np.nan
    u = body_vec / n1
    dot = float(np.clip(np.dot(u, nx), -1.0, 1.0))
    ang_to_normal = math.degrees(math.acos(abs(dot)))  # 0..90
    return 90.0 - ang_to_normal

# 如果你强制要“与Z轴夹角”，可用这一版（不默认启用）
def tilt_deg_with_z(pL, pR, use_plane="YZ", eps=1e-8):
    """
    可选：把线向量投影到某个平面后，与 +Z 的夹角（有符号）
    - use_plane="YZ": 只看 (y,z)
    - use_plane="XZ": 只看 (x,z)
    注意：这更像“深度差导致的旋转/开合”，通常不叫“倾斜”
    """
    v = pR - pL
    if use_plane == "YZ":
        a = float(v[1])
        b = float(v[2])
    elif use_plane == "XZ":
        a = float(v[0])
        b = float(v[2])
    else:
        raise ValueError("use_plane must be 'YZ' or 'XZ'")
    if abs(a) < eps and abs(b) < eps:
        return np.nan
    # 与Z轴夹角：atan2(横向分量, z分量)
    return math.degrees(math.atan2(a, b))


# ======================= 主流程 =======================
# ======================= 主流程 =======================
def calculate_metrics(df_pts, events_abs, video_id):
    """
    计算单个视频的指标
    :param df_pts: 关键点DataFrame (包含 landmark_x 列)
    :param events_abs: 关键帧绝对帧号数组
    :param video_id: 视频ID
    :return: list of dicts (metrics)
    """
    results = []
    
    # 只计算 8 个关键帧：events[1:9] (对应索引 0-8, 取 1-8)
    # 注意：events_abs 可能是 8个或9个。
    # 如果是8个 (0-7)，通常 0=Address, ..., 7=Finish
    # 如果是9个 (0-8)，通常 0=Toe-up?, 1=Address? ... 
    # 原代码逻辑是 events_abs[1:9]，假设 events_abs 至少有9个元素，取第2到第9个。
    # 如果 events_abs 只有 8 个，这里会出错或为空。
    # 假设输入 events_abs 包含了所有需要的事件帧。
    
    # 兼容逻辑：如果 events_abs 长度为 8，则取 0-7 ?
    # 原代码：events_abs[1:9] -> 取索引 1,2,3,4,5,6,7,8. 共8帧。
    # 这意味着原代码期望 events_abs 至少有 9 帧 (索引0-8)。
    # 且 base_abs = events_abs[0]。
    
    if events_abs.size < 9:
        # 尝试兼容 8 帧的情况 (假设没有 Toe-up，直接从 Address 开始)
        # 但原逻辑是用 events[0] 作为 base_abs (real_frame=0)。
        # 如果只有8帧，可能 events[0] 就是 Address。
        pass

    # 确保 df_pts 包含该视频数据
    df_v = df_pts[df_pts["video_id"] == str(video_id)].copy()
    if df_v.empty:
        # 尝试 int 匹配
        df_v = df_pts[df_pts["video_id"] == int(video_id)].copy()
        
    if df_v.empty:
        print(f"[WARN] video_id={video_id} 在点数据CSV中不存在，跳过。")
        return []

    df_v = df_v.set_index("frame_index")

    # 确定 base_abs
    # 原逻辑：base_abs = events_abs[0]
    # 如果 events_abs 只有 8 个，我们假设 events_abs[0] 是 Address
    # 如果 events_abs 有 9 个，我们假设 events_abs[0] 是 Toe-up (或忽略), events_abs[1] 是 Address
    
    # 根据 Extract_key_frames.py:
    # EVENT_NAMES_8: 0:Address ... 7:Finish
    # EVENT_NAMES_9: 0:脚尖抬起 ... 1:起摆动作(Address?) ...
    
    # 原代码逻辑是取 events_abs[1:9]，即取第2个到第9个事件。
    # 并且 base_abs = events_abs[0]。
    # 这暗示 events_abs[0] 是参考帧 (real_frame=0)，但不在输出结果中 (输出从 event_index=1 开始)。
    
    # 如果当前算法输出 8 帧 (Address...Finish)，那么 events_abs[0] 就是 Address。
    # 我们可能需要调整逻辑。
    
    # 假设：如果 len=8，则 0-7 都是关键帧。base_abs = events_abs[0]。
    # 输出 event_index 1..8 对应 events_abs[0..7] ?
    # 或者 event_index 1..8 对应 events_abs[0..7] 且 base_abs = events_abs[0] ?
    
    # 为了保持兼容性，如果 len >= 9，沿用原逻辑。
    # 如果 len == 8，我们假设 events_abs[0] 是 Address，作为 base_abs，并且它也是第一个输出帧。
    
    if events_abs.size >= 9:
        base_abs = int(events_abs[0])
        target_events = events_abs[1:9]
        start_event_idx = 1
    else:
        # 只有8帧的情况
        base_abs = int(events_abs[0])
        target_events = events_abs[0:8]
        start_event_idx = 1 # 依然从 1 开始编号

    start_real = 0

    # 检查 base_abs (real_frame=0) 是否存在
    # 注意：df_v 的 index 是 frame_index (可能是绝对帧号，也可能是相对帧号)
    # 通常 keypoints csv 里的 frame_index 是绝对帧号。
    # 但原代码逻辑：
    # get_pt(0, ...) -> 读取 real_frame=0 的点。
    # real_frame = abs_frame - base_abs
    # 所以 df_v 的 index 应该是 real_frame ? 
    # 不，df_v = df_pts[...].set_index("frame_index")
    # 如果 df_pts 里的 frame_index 是绝对帧号，那么 get_pt(0) 应该是 get_pt(base_abs) ?
    
    # 原代码：
    # if start_real not in df_v.index: ...
    # get_pt(0, ...)
    # 这意味着 df_v 的 index 必须包含 0。
    # 这意味着 df_pts 里的 frame_index 必须是 相对帧号 (real_frame)。
    # 但通常 export_all_keypoints.py 输出的是绝对帧号。
    
    # 让我们检查 export_all_keypoints.py (未读，但根据命名推测)。
    # 如果 df_pts 里是绝对帧号，那么我们需要用 abs_frame 来索引。
    
    # 假设 df_pts index 是绝对帧号。
    # 原代码逻辑似乎假设 df_pts 已经被处理成相对帧号了？
    # 或者 events_abs[0] 对应的帧号在 df_pts 里就是 0？
    
    # 让我们修改逻辑以适应绝对帧号。
    # get_pt_abs(abs_frame, idx)
    
    def get_pt_abs(fr, idx):
        if fr not in df_v.index:
            return np.array([np.nan, np.nan, np.nan], dtype=np.float32)
        return parse_xyz(df_v.loc[fr, f"landmark_{idx}"])

    # ===== 起点 (Base Frame) =====
    # 无论 len=8 还是 9，base_abs 都是参考帧
    ls0, rs0 = get_pt_abs(base_abs, L_SHOULDER), get_pt_abs(base_abs, R_SHOULDER)
    lh0, rh0 = get_pt_abs(base_abs, L_HIP), get_pt_abs(base_abs, R_HIP)
    
    # 如果 base_abs 缺失，无法计算位移
    if np.isnan(ls0).all():
         print(f"[WARN] video_id={video_id} 缺少基准帧 frame={base_abs}，跳过。")
         return []

    shoulder_center_0 = (ls0 + rs0) / 2.0
    hip_center_0 = (lh0 + rh0) / 2.0
    trunk_mid_0 = (shoulder_center_0 + hip_center_0) / 2.0
    # left_hand_0 = get_pt_abs(base_abs, L_WRIST)

    # ===== 关键帧 =====
    for i, abs_frame in enumerate(target_events):
        ei = start_event_idx + i
        abs_frame = int(abs_frame)
        real_frame = abs_frame - base_abs

        if abs_frame not in df_v.index:
            # print(f"[WARN] video_id={video_id} 缺少帧 {abs_frame}")
            results.append({
                "video_id": video_id,
                "event_index": ei,
                "abs_frame": abs_frame,
                "real_frame": real_frame,
                "hip_dx": np.nan,
                "trunk_mid_dy": np.nan,
                "shoulder_center_dx": np.nan,
                "shoulder_tilt_deg": np.nan,
                "hip_tilt_deg": np.nan,
            })
            continue

        ls, rs = get_pt_abs(abs_frame, L_SHOULDER), get_pt_abs(abs_frame, R_SHOULDER)
        lh, rh = get_pt_abs(abs_frame, L_HIP), get_pt_abs(abs_frame, R_HIP)

        shoulder_center = (ls + rs) / 2.0
        hip_center = (lh + rh) / 2.0
        trunk_mid = (shoulder_center + hip_center) / 2.0

        # 位移：以 base_abs 为零点
        hip_dx = float(hip_center[0] - hip_center_0[0])                  # X 左右
        trunk_mid_dy = float(trunk_mid[1] - trunk_mid_0[1])              # Y 上下
        shoulder_center_dx = float(shoulder_center[0] - shoulder_center_0[0])

        # 倾斜角
        shoulder_tilt = tilt_deg_xy(ls, rs)
        hip_tilt = tilt_deg_xy(lh, rh)

        results.append({
            "video_id": video_id,
            "event_index": ei,
            "abs_frame": abs_frame,
            "real_frame": real_frame,

            "hip_dx": hip_dx,
            "trunk_mid_dy": trunk_mid_dy,
            "shoulder_center_dx": shoulder_center_dx,

            "shoulder_tilt_deg": shoulder_tilt,
            "hip_tilt_deg": hip_tilt,
        })
        
    return results

def main():
    df_pts = pd.read_csv(POINTS_CSV)
    df_evt = pd.read_csv(EVENTS_CSV)

    all_results = []

    for _, evt_row in df_evt.iterrows():
        vid = evt_row["id"] # 可能是 int 或 str
        events_abs = parse_events(evt_row["events"])
        
        res = calculate_metrics(df_pts, events_abs, vid)
        all_results.extend(res)

    df_out = pd.DataFrame(all_results)

    out_path = Path(OUT_CSV)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[OK] 正面缺陷指标已生成：{out_path}")



if __name__ == "__main__":
    main()
