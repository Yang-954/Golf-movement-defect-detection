from pathlib import Path
import numpy as np
import pandas as pd

# ====================== 配置区 ======================
METRICS_CSV = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\正面\缺陷指标结果_face_on.csv"

RANGES_DIR = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\正面\标准范围_60_20_20"
RANGES_CSV = r"normal_ranges_face_on_60_20_20.csv"

OUT_DIR = r"D:\桌面\工作\高尔夫挥杆动作缺陷检测与分析\教学\缺陷分析\02\正面\缺陷判定_60_20_20"
OUT_CSV_WIDE = "defect_judgement_face_on_wide.csv"
OUT_CSV_LONG = "defect_judgement_face_on_long.csv"

EVENT_INDEXES = list(range(1, 9))

METRIC_COLS = [
    "hip_dx",
    "trunk_mid_dy",
    "shoulder_center_dx",
    "shoulder_tilt_deg",
    "hip_tilt_deg",
]

# 默认：低于q20 -> 严重不足；高于q80 -> 略超
METRIC_RULES = {m: {"low_is_bad": True, "high_is_bad": True} for m in METRIC_COLS}
# ===================================================

def load_ranges_csv(path: Path):
    df = pd.read_csv(path)
    required = {"event_index", "metric", "low_th_q20", "high_th_q80", "n_samples"}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"标准范围CSV缺少列：{required - set(df.columns)}")
    ranges = {}
    for _, r in df.iterrows():
        ei = int(r["event_index"])
        m = str(r["metric"])
        ranges[(ei, m)] = (r["low_th_q20"], r["high_th_q80"])
    return ranges

def classify_value(x, low_th, high_th, low_is_bad=True, high_is_bad=True):
    if pd.isna(x) or pd.isna(low_th) or pd.isna(high_th):
        return "nan"
    if low_is_bad and x < low_th:
        return "severe_insufficient"
    if high_is_bad and x > high_th:
        return "slight_exceed"
    return "normal"

def severity_rank(label: str) -> int:
    if label == "severe_insufficient":
        return 2
    if label == "slight_exceed":
        return 1
    return 0

def judge_defects(df, ranges_path):
    """
    对指标进行缺陷判定
    :param df: 指标DataFrame
    :param ranges_path: 标准范围CSV路径
    :return: (df_wide, df_long)
    """
    for col in ["video_id", "event_index"] + METRIC_COLS:
        if col not in df.columns:
            # 允许缺失，但要警告
            print(f"[WARN] 缺少必要列：{col}")
            if col in METRIC_COLS:
                df[col] = np.nan

    df = df[df["event_index"].isin(EVENT_INDEXES)].copy()

    # 兼容 abs_frame/real_frame 不存在的情况
    for k in ["abs_frame", "real_frame"]:
        if k not in df.columns:
            df[k] = np.nan

    ranges = load_ranges_csv(Path(ranges_path))

    long_rows = []
    wide_rows = []

    for _, row in df.iterrows():
        vid = row["video_id"] # int or str
        ei = int(row["event_index"])

        worst = 0
        defect_cnt = 0

        wide = {
            "video_id": vid,
            "event_index": ei,
            "abs_frame": row["abs_frame"],
            "real_frame": row["real_frame"],
        }

        for m in METRIC_COLS:
            low_th, high_th = ranges.get((ei, m), (np.nan, np.nan))
            rule = METRIC_RULES[m]

            x = row[m]
            label = classify_value(x, low_th, high_th, rule["low_is_bad"], rule["high_is_bad"])

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
                "label": label,
            })

            wide[m] = x
            wide[f"{m}__low_q20"] = low_th
            wide[f"{m}__high_q80"] = high_th
            wide[f"{m}__label"] = label

        worst_label = "normal"
        if worst == 2:
            worst_label = "severe_insufficient"
        elif worst == 1:
            worst_label = "slight_exceed"

        wide["defect_count"] = defect_cnt
        wide["has_defect"] = int(defect_cnt > 0)
        wide["worst_label"] = worst_label

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

    print(f"[OK] 正面缺陷判定结果已生成：\n- {out_wide_path}\n- {out_long_path}")


if __name__ == "__main__":
    main()
