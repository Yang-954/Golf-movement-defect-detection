import json
from pathlib import Path
import numpy as np
import pandas as pd

# ====================== 配置区 ======================
METRICS_CSV = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\侧面\缺陷指标结果_down_the_line.csv"

RANGES_DIR = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\侧面\标准范围_60_20_20"
RANGES_CSV = r"normal_ranges_down_the_line_60_20_20.csv"
# 也可以用 JSON：RANGES_JSON = r"normal_ranges_down_the_line_60_20_20.json"

OUT_DIR = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\侧面\缺陷判定_60_20_20"
OUT_CSV_WIDE = "defect_judgement_wide.csv"
OUT_CSV_LONG = "defect_judgement_long.csv"

EVENT_INDEXES = list(range(1, 9))

METRIC_COLS = [
    # 如果你最新文件是 shoulder_rot_z_deg/hip_rot_z_deg，请改成这两个
    "shoulder_rot_rel_deg",
    "hip_rot_rel_deg",
    "body_tilt_yz_deg",
    "hip_dx",
    "shoulder_center_dx",
    "left_hand_dx",
    "energy_index",
]

# 方向规则（可选，但建议保留接口）
# 你的要求是：低端 = 严重不足（20%），高端 = 略微超标（20%）
# 对大多数“角度/位移/能量差”类指标，都适用。
# 若某些指标你认为“越大越好”或“越小越好”需要反过来，可在这里单独改：
#   "low_is_bad": True  -> 低于阈值判严重不足
#   "high_is_bad": True -> 高于阈值判略微超标
METRIC_RULES = {m: {"low_is_bad": True, "high_is_bad": True} for m in METRIC_COLS}

# 最少样本数（从 ranges 中读不到阈值时直接给 nan）
# ===================================================


def load_ranges_csv(path: Path):
    df = pd.read_csv(path)
    required = {"event_index", "metric", "low_th_q20", "high_th_q80", "n_samples"}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"标准范围CSV缺少列：{required - set(df.columns)}")
    # 构建字典：ranges[(event_index, metric)] = (low, high)
    ranges = {}
    for _, r in df.iterrows():
        ei = int(r["event_index"])
        m = str(r["metric"])
        low = r["low_th_q20"]
        high = r["high_th_q80"]
        ranges[(ei, m)] = (low, high)
    return ranges


def classify_value(x, low_th, high_th, low_is_bad=True, high_is_bad=True):
    """
    三分类：
      - normal
      - slight_exceed
      - severe_insufficient
    若 x/阈值为 NaN -> "nan"
    """
    if pd.isna(x) or pd.isna(low_th) or pd.isna(high_th):
        return "nan"

    # 默认规则：低于 q20 -> 严重不足；高于 q80 -> 略超；中间 -> 正常
    if low_is_bad and x < low_th:
        return "severe_insufficient"
    if high_is_bad and x > high_th:
        return "slight_exceed"
    return "normal"


def severity_rank(label: str) -> int:
    """
    用于聚合“最严重等级”
    nan 不计入缺陷
    """
    if label == "severe_insufficient":
        return 2
    if label == "slight_exceed":
        return 1
    return 0


def judge_defects(df, ranges_path):
    """
    对指标进行缺陷判定 (侧面)
    :param df: 指标DataFrame
    :param ranges_path: 标准范围CSV路径
    :return: (df_wide, df_long)
    """
    for col in ["video_id", "event_index"] + METRIC_COLS:
        if col not in df.columns:
            print(f"[WARN] 缺少必要列：{col}")
            if col in METRIC_COLS:
                df[col] = np.nan

    df = df[df["event_index"].isin(EVENT_INDEXES)].copy()

    ranges = load_ranges_csv(Path(ranges_path))

    long_rows = []
    wide_rows = []

    key_cols = ["video_id", "event_index", "abs_frame", "real_frame"]
    for k in key_cols:
        if k not in df.columns:
            df[k] = np.nan

    for _, row in df.iterrows():
        vid = row["video_id"]
        ei = int(row["event_index"])

        per_metric_labels = {}
        per_metric_values = {}
        per_metric_low = {}
        per_metric_high = {}

        worst = 0
        defect_cnt = 0

        for m in METRIC_COLS:
            low_th, high_th = ranges.get((ei, m), (np.nan, np.nan))
            rule = METRIC_RULES.get(m, {"low_is_bad": True, "high_is_bad": True})

            x = row[m]
            label = classify_value(
                x, low_th, high_th,
                low_is_bad=rule["low_is_bad"],
                high_is_bad=rule["high_is_bad"]
            )

            per_metric_labels[m] = label
            per_metric_values[m] = x
            per_metric_low[m] = low_th
            per_metric_high[m] = high_th

            rnk = severity_rank(label)
            if rnk > 0:
                defect_cnt += 1
            worst = max(worst, rnk)

            long_rows.append({
                "video_id": vid,
                "event_index": ei,
                "metric": m,
                "value": x,
                "low_th_q20": low_th,
                "high_th_q80": high_th,
                "label": label
            })

        worst_label = "normal"
        if worst == 2:
            worst_label = "severe_insufficient"
        elif worst == 1:
            worst_label = "slight_exceed"

        wide = {
            "video_id": vid,
            "event_index": ei,
            "abs_frame": row["abs_frame"],
            "real_frame": row["real_frame"],
            "defect_count": defect_cnt,
            "has_defect": int(defect_cnt > 0),
            "worst_label": worst_label,
        }

        # 输出每个指标：值 / 阈值 / 判定
        for m in METRIC_COLS:
            wide[f"{m}"] = per_metric_values[m]
            wide[f"{m}__low_q20"] = per_metric_low[m]
            wide[f"{m}__high_q80"] = per_metric_high[m]
            wide[f"{m}__label"] = per_metric_labels[m]

        wide_rows.append(wide)

    df_long = pd.DataFrame(long_rows)
    if not df_long.empty:
        df_long = df_long.sort_values(["video_id", "event_index", "metric"])
        
    df_wide = pd.DataFrame(wide_rows)
    if not df_wide.empty:
        df_wide = df_wide.sort_values(["video_id", "event_index"])
        
    return df_wide, df_long

def main():
    df = pd.read_csv(METRICS_CSV)
    ranges_path = Path(RANGES_DIR) / RANGES_CSV
    
    df_wide, df_long = judge_defects(df, ranges_path)

    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_wide_path = out_dir / OUT_CSV_WIDE
    out_long_path = out_dir / OUT_CSV_LONG

    df_wide.to_csv(out_wide_path, index=False, encoding="utf-8-sig")
    df_long.to_csv(out_long_path, index=False, encoding="utf-8-sig")

    print(f"[OK] 缺陷判定结果已生成：\n- {out_wide_path}\n- {out_long_path}")



if __name__ == "__main__":
    main()
