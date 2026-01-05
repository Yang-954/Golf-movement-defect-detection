import re
import ast
import math
import numpy as np
import pandas as pd
from pathlib import Path

# ======================= 路径配置 =======================
POINTS_CSV = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\侧面\用于分析缺陷的点数据_down_the_line.csv"
EVENTS_CSV = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\侧面\关键帧数据_down_the_line.csv"
OUT_CSV    = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\侧面\缺陷指标结果_down_the_line.csv"
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
def proj_xz(p):
    """点/向量投影到 XZ 平面（保留 x,z，令 y=0）"""
    return np.array([float(p[0]), 0.0, float(p[2])], dtype=np.float32)

def signed_angle_between_lines_xz(pL0, pR0, pL1, pR1, eps=1e-8):
    """
    你指定的新规则：用四个点计算两条线的夹角（XZ 平面）
    - 起点线：L0--R0
    - 当前线：L1--R1
    - 向量方向统一取 L -> R（保证角度定义一致）
    - 角度幅值：0~180
    - 符号：cross(v0, v1).y > 0 记为正（向左），<0 记为负（向右）
    返回：[-180, 180]
    """
    a0 = proj_xz(pR0) - proj_xz(pL0)  # 起点线向量
    a1 = proj_xz(pR1) - proj_xz(pL1)  # 当前线向量

    n0 = float(np.linalg.norm(a0))
    n1 = float(np.linalg.norm(a1))
    if n0 < eps or n1 < eps:
        return np.nan

    u0 = a0 / n0
    u1 = a1 / n1

    dot = float(np.clip(np.dot(u0, u1), -1.0, 1.0))
    ang = math.degrees(math.acos(dot))  # 0..180

    cross_y = float(np.cross(u0, u1)[1])  # 在XZ平面中，y分量决定左右旋
    if abs(cross_y) < 1e-10:
        return 0.0

    sign = 1.0 if cross_y > 0 else -1.0
    return sign * ang

def angle_with_yz_plane(p_top, p_bottom):
    """
    身体倾斜角：身体轴线 与 YZ 面的倾斜（0 表示在 YZ 面内）
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

# ======================= 主流程 =======================
# ======================= 主流程 =======================
def calculate_metrics(df_pts, events_abs, video_id):
    """
    计算单个视频的指标 (侧面)
    :param df_pts: 关键点DataFrame (包含 landmark_x 列)
    :param events_abs: 关键帧绝对帧号数组
    :param video_id: 视频ID
    :return: list of dicts (metrics)
    """
    results = []
    
    # 兼容逻辑：如果 events_abs 长度为 8，则取 0-7
    if events_abs.size >= 9:
        base_abs = int(events_abs[0])
        target_events = events_abs[1:9]
        start_event_idx = 1
    else:
        # 只有8帧的情况
        base_abs = int(events_abs[0])
        target_events = events_abs[0:8]
        start_event_idx = 1

    # 确保 df_pts 包含该视频数据
    df_v = df_pts[df_pts["video_id"] == str(video_id)].copy()
    if df_v.empty:
        df_v = df_pts[df_pts["video_id"] == int(video_id)].copy()
        
    if df_v.empty:
        print(f"[WARN] video_id={video_id} 在点数据CSV中不存在，跳过。")
        return []

    df_v = df_v.set_index("frame_index")

    def get_pt_abs(fr, idx):
        if fr not in df_v.index:
            return np.array([np.nan, np.nan, np.nan], dtype=np.float32)
        return parse_xyz(df_v.loc[fr, f"landmark_{idx}"])

    # ===== 起点 (Base Frame) =====
    ls0, rs0 = get_pt_abs(base_abs, L_SHOULDER), get_pt_abs(base_abs, R_SHOULDER)
    lh0, rh0 = get_pt_abs(base_abs, L_HIP), get_pt_abs(base_abs, R_HIP)
    
    if np.isnan(ls0).all():
         print(f"[WARN] video_id={video_id} 缺少基准帧 frame={base_abs}，跳过。")
         return []

    shoulder_center_0 = (ls0 + rs0) / 2.0
    hip_center_0 = (lh0 + rh0) / 2.0
    trunk_mid_0 = (shoulder_center_0 + hip_center_0) / 2.0
    left_hand_0 = get_pt_abs(base_abs, L_WRIST)

    # ===== 关键帧 =====
    for i, abs_frame in enumerate(target_events):
        ei = start_event_idx + i
        abs_frame = int(abs_frame)
        real_frame = abs_frame - base_abs

        if abs_frame not in df_v.index:
            results.append({
                "video_id": video_id,
                "event_index": ei,
                "abs_frame": abs_frame,
                "real_frame": real_frame,
                "shoulder_rot_rel_deg": np.nan,
                "hip_rot_rel_deg": np.nan,
                "body_tilt_yz_deg": np.nan,
                "hip_dx": np.nan,
                "shoulder_center_dx": np.nan,
                "left_hand_dx": np.nan,
                "energy_index": np.nan,
            })
            continue

        ls, rs = get_pt_abs(abs_frame, L_SHOULDER), get_pt_abs(abs_frame, R_SHOULDER)
        lh, rh = get_pt_abs(abs_frame, L_HIP), get_pt_abs(abs_frame, R_HIP)
        lhand = get_pt_abs(abs_frame, L_WRIST)

        shoulder_center = (ls + rs) / 2.0
        hip_center = (lh + rh) / 2.0
        trunk_mid = (shoulder_center + hip_center) / 2.0

        # 1. 旋转（相对 Address）
        shoulder_rot = signed_angle_between_lines_xz(ls0, rs0, ls, rs)
        hip_rot = signed_angle_between_lines_xz(lh0, rh0, lh, rh)

        # 2. 身体前倾（YZ平面）
        body_tilt = angle_with_yz_plane(trunk_mid, hip_center)

        # 3. 位移（相对 Address）
        hip_dx = float(hip_center[0] - hip_center_0[0])
        shoulder_center_dx = float(shoulder_center[0] - shoulder_center_0[0])
        left_hand_dx = float(lhand[0] - left_hand_0[0])

        # 4. 能量指数 (shoulder_rot - hip_rot)
        if not pd.isna(shoulder_rot) and not pd.isna(hip_rot):
            energy = shoulder_rot - hip_rot
        else:
            energy = np.nan

        results.append({
            "video_id": video_id,
            "event_index": ei,
            "abs_frame": abs_frame,
            "real_frame": real_frame,

            "shoulder_rot_rel_deg": shoulder_rot,
            "hip_rot_rel_deg": hip_rot,
            "body_tilt_yz_deg": body_tilt,
            "hip_dx": hip_dx,
            "shoulder_center_dx": shoulder_center_dx,
            "left_hand_dx": left_hand_dx,
            "energy_index": energy,
        })
        
    return results

def main():
    df_pts = pd.read_csv(POINTS_CSV)
    df_evt = pd.read_csv(EVENTS_CSV)

    all_results = []

    for _, evt_row in df_evt.iterrows():
        vid = evt_row["id"]
        events_abs = parse_events(evt_row["events"])
        
        res = calculate_metrics(df_pts, events_abs, vid)
        all_results.extend(res)

    df_out = pd.DataFrame(all_results)

    out_path = Path(OUT_CSV)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[OK] 缺陷指标已生成：{out_path}")


if __name__ == "__main__":
    main()
