import os
import argparse
import numpy as np
import pandas as pd

# =========================
# 输入逐帧指标列名（中文）
# =========================
COL_VIDEO = "视频ID"
COL_FRAME = "帧序号"

METRICS = [
    "肩线与Z轴夹角_度_左正右负_近端终点_XZ平面",
    "髋线与Z轴夹角_度_左正右负_近端终点_XZ平面",
    "身体平面与Y轴夹角_度_X轴为0向上为正_0到180",
    "左髋X轴位移",
    "右髋X轴位移",
    "肩线中心X轴位移",
    "左手X轴位移",
    "肩线旋转减髋线旋转_度",
]

# 默认分位区间（稳健）
DEFAULT_P_LOW = 10
DEFAULT_P_HIGH = 90

# 连续异常过滤
DEFAULT_MIN_STREAK = 3

# 每个指标的“重要性/权重”（可调）
# 说明：你说“每个指标都要审判”，这里做的是“每个指标都有单独判定 + 也参与综合评分”
DEFAULT_WEIGHTS = {
    "肩线与Z轴夹角_度_左正右负_近端终点_XZ平面": 1.2,
    "髋线与Z轴夹角_度_左正右负_近端终点_XZ平面": 1.2,
    "身体平面与Y轴夹角_度_X轴为0向上为正_0到180": 1.0,
    "左髋X轴位移": 1.0,
    "右髋X轴位移": 1.0,
    "肩线中心X轴位移": 1.0,
    "左手X轴位移": 0.8,
    "肩线旋转减髋线旋转_度": 1.3,
}

# 每个指标的判定方式：区间（between） or 双侧阈值（abs_le）
# 目前统一用区间 between（最通用）。如你想对位移类用绝对值阈值，可切到 abs_le。
DEFAULT_RULE = {m: "between" for m in METRICS}


def require_columns(df: pd.DataFrame, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")


def robust_quantile_bounds(df: pd.DataFrame, metrics, p_low: float, p_high: float) -> pd.DataFrame:
    """
    对每个指标计算分位数“标准区间”，并额外提供“严/中/宽”三档区间，便于每指标审判分级。
      - 宽松：P5~P95
      - 标准：P10~P90（默认用于合规）
      - 严格：P15~P85（可用于“优秀”判定）
    输出：标准区间表.csv
    """
    rows = []
    for m in metrics:
        s = pd.to_numeric(df[m], errors="coerce").dropna()
        if len(s) < 50:
            rows.append({
                "指标": m, "样本数": int(len(s)),
                "P5": np.nan, "P10": np.nan, "P15": np.nan,
                "P50": np.nan,
                "P85": np.nan, "P90": np.nan, "P95": np.nan,
                "下限_严格(P15)": np.nan, "上限_严格(P85)": np.nan,
                "下限_标准(P10)": np.nan, "上限_标准(P90)": np.nan,
                "下限_宽松(P5)": np.nan, "上限_宽松(P95)": np.nan,
            })
            continue

        q = {p: float(np.nanpercentile(s.values, p)) for p in [5, 10, 15, 50, 85, 90, 95]}
        rows.append({
            "指标": m,
            "样本数": int(len(s)),
            "P5": q[5], "P10": q[10], "P15": q[15],
            "P50": q[50],
            "P85": q[85], "P90": q[90], "P95": q[95],
            "下限_严格(P15)": q[15], "上限_严格(P85)": q[85],
            "下限_标准(P10)": q[10], "上限_标准(P90)": q[90],
            "下限_宽松(P5)": q[5], "上限_宽松(P95)": q[95],
        })

    # 仍保留命令行 p_low/p_high 的“主合规区间”
    bounds = pd.DataFrame(rows)
    bounds["下限_主合规"] = bounds[f"P{int(p_low)}"] if f"P{int(p_low)}" in bounds.columns else np.nan
    bounds["上限_主合规"] = bounds[f"P{int(p_high)}"] if f"P{int(p_high)}" in bounds.columns else np.nan
    return bounds


def build_rule_table(bounds: pd.DataFrame,
                     weights: dict,
                     rules: dict,
                     use_band: str = "标准") -> pd.DataFrame:
    """
    生成“每指标审判规则表”：
      - 指标
      - 判定方式（between/abs_le）
      - 下限/上限（从 bounds 里取某一档区间）
      - 权重
    use_band: "严格" / "标准" / "宽松" / "主合规"
    """
    b = bounds.set_index("指标")

    def pick(m: str, band: str):
        if band == "严格":
            return float(b.loc[m, "下限_严格(P15)"]), float(b.loc[m, "上限_严格(P85)"])
        if band == "宽松":
            return float(b.loc[m, "下限_宽松(P5)"]), float(b.loc[m, "上限_宽松(P95)"])
        if band == "主合规":
            return float(b.loc[m, "下限_主合规"]), float(b.loc[m, "上限_主合规"])
        # 默认 标准
        return float(b.loc[m, "下限_标准(P10)"]), float(b.loc[m, "上限_标准(P90)"])

    rows = []
    for m in METRICS:
        lo, hi = pick(m, use_band)
        rows.append({
            "指标": m,
            "判定方式": rules.get(m, "between"),
            "下限": lo,
            "上限": hi,
            "权重": float(weights.get(m, 1.0)),
        })
    return pd.DataFrame(rows)


def apply_rules_per_metric(df: pd.DataFrame, rule_table: pd.DataFrame) -> pd.DataFrame:
    """
    对每个指标分别“审判”，输出每帧每指标的：
      - 结果：0标准 / 1轻微 / 2异常（三档）
      - 合规（标准档区间内=1，否则0）
      - 超下限 / 超上限
      - 归一化偏差（可用于评分）：距离区间的相对偏离程度
    并给出帧级综合评分与帧级判定。
    """
    rt = rule_table.set_index("指标")
    out = df[[COL_VIDEO, COL_FRAME] + METRICS].copy()

    # 逐指标审判
    for m in METRICS:
        x = pd.to_numeric(out[m], errors="coerce")
        mode = rt.loc[m, "判定方式"]
        lo = float(rt.loc[m, "下限"])
        hi = float(rt.loc[m, "上限"])

        if mode == "abs_le":
            # 绝对值不超过阈值：这里用 hi 作为阈值（lo 忽略）
            thr = hi
            ok = x.abs() <= thr
            low_bad = (x.abs() > thr)
            high_bad = (x.abs() > thr)
            # 距离阈值的归一化偏差
            dev = (x.abs() - thr) / (thr + 1e-9)
            dev = dev.clip(lower=0)
        else:
            # between：区间内合规
            ok = (x >= lo) & (x <= hi)
            low_bad = (x < lo)
            high_bad = (x > hi)
            # 到区间的“相对偏差”：超出多少个区间宽度
            width = (hi - lo) if (hi - lo) != 0 else 1e-9
            dev = np.zeros(len(out), dtype=float)
            dev = pd.Series(dev, index=out.index, dtype=float)
            dev = dev.mask(low_bad, (lo - x) / width)
            dev = dev.mask(high_bad, (x - hi) / width)
            dev = dev.fillna(np.nan).clip(lower=0)

        out[f"{m}__合规"] = ok.astype("Int64")
        out[f"{m}__超下限"] = low_bad.astype("Int64")
        out[f"{m}__超上限"] = high_bad.astype("Int64")
        out[f"{m}__偏差"] = dev

        # 三档审判：标准/轻微/异常
        # 这里将“偏差”分层：<=0 标准；(0,0.5] 轻微；>0.5 异常（可按经验调整）
        def grade_from_dev(v):
            if pd.isna(v):
                return np.nan
            if v <= 0:
                return 0
            elif v <= 0.5:
                return 1
            else:
                return 2

        out[f"{m}__审判_0标准1轻微2异常"] = out[f"{m}__偏差"].apply(grade_from_dev).astype("Int64")

    # 帧级聚合：每个指标都审判后，给出综合评分与结论
    # 评分：100 - 加权偏差*100（截断到0-100）
    weights = {row["指标"]: float(row["权重"]) for _, row in rule_table.iterrows()}
    wsum = float(sum(weights.values()))

    # 计算加权偏差（忽略 NaN）
    dev_cols = [f"{m}__偏差" for m in METRICS]
    dev_mat = out[dev_cols].to_numpy(dtype=float)

    w = np.array([weights[m] for m in METRICS], dtype=float)
    # mask nan
    mask = np.isfinite(dev_mat)
    w_mat = np.tile(w.reshape(1, -1), (dev_mat.shape[0], 1))
    w_eff = np.where(mask, w_mat, 0.0)
    denom = w_eff.sum(axis=1)
    numer = np.where(mask, dev_mat, 0.0) * w_eff
    wdev = np.where(denom > 0, numer.sum(axis=1) / denom, np.nan)

    score = 100.0 * (1.0 - np.clip(wdev, 0.0, 1.0))
    out["帧级加权偏差"] = wdev
    out["帧级评分_0到100"] = score

    # 帧级判定：基于“异常指标数 + 评分”双条件，更可解释
    judge_cols = [f"{m}__审判_0标准1轻微2异常" for m in METRICS]
    judge_mat = out[judge_cols].to_numpy(dtype=float)
    abnormal_cnt = np.nansum(judge_mat == 2, axis=1)
    mild_cnt = np.nansum(judge_mat == 1, axis=1)

    out["异常指标数_帧级"] = abnormal_cnt.astype(int)
    out["轻微偏差指标数_帧级"] = mild_cnt.astype(int)

    def frame_verdict(a_cnt, s):
        # a_cnt: 异常指标数
        # s: 评分
        if pd.isna(a_cnt) or pd.isna(s):
            return np.nan
        a_cnt = int(a_cnt)
        s = float(s)
        if a_cnt == 0 and s >= 90:
            return "优秀"
        if a_cnt == 0:
            return "标准"
        if a_cnt <= 2 and s >= 75:
            return "基本标准"
        return "不标准"

    out["帧级结论"] = [frame_verdict(a, s) for a, s in zip(out["异常指标数_帧级"], out["帧级评分_0到100"])]

    return out


def add_streak_filter(df_flagged: pd.DataFrame, min_streak: int) -> pd.DataFrame:
    """
    连续异常过滤：以“帧级结论==不标准”为异常帧，短段降级为基本标准
    """
    df_flagged = df_flagged.sort_values([COL_VIDEO, COL_FRAME]).reset_index(drop=True)
    raw_bad = (df_flagged["帧级结论"] == "不标准").fillna(False).to_numpy()

    effective = np.zeros(len(df_flagged), dtype=bool)

    for vid, idx in df_flagged.groupby(COL_VIDEO).groups.items():
        inds = np.array(list(idx), dtype=int)
        seq = raw_bad[inds]

        start = None
        for i, v in enumerate(seq):
            if v and start is None:
                start = i
            if ((not v) or i == len(seq) - 1) and start is not None:
                end = i if (not v) else i + 1
                length = end - start
                if length >= min_streak:
                    effective[inds[start:end]] = True
                start = None

    df_flagged["帧级异常_连续过滤后"] = pd.Series(effective).astype("Int64")

    # 过滤后帧级结论调整：未通过连续过滤的“不标准”降级为“基本标准”
    def adjust(row):
        if row["帧级结论"] == "不标准" and int(row["帧级异常_连续过滤后"]) == 0:
            return "基本标准"
        return row["帧级结论"]

    df_flagged["帧级结论_连续过滤后"] = df_flagged.apply(adjust, axis=1)
    return df_flagged


def video_level_summary(df_flagged: pd.DataFrame, rule_table: pd.DataFrame) -> pd.DataFrame:
    """
    视频级汇总：每个指标都给出“异常帧占比/轻微占比/标准占比”，并输出Top问题指标。
    """
    rows = []
    judge_cols = [f"{m}__审判_0标准1轻微2异常" for m in METRICS]

    for vid, g in df_flagged.groupby(COL_VIDEO, sort=True):
        g = g.sort_values(COL_FRAME)
        n = len(g)

        # 视频级总体
        verdict = g["帧级结论_连续过滤后"]
        p_bad = float((verdict == "不标准").mean()) if n else np.nan
        p_basic = float((verdict == "基本标准").mean()) if n else np.nan
        p_std = float((verdict == "标准").mean()) if n else np.nan
        p_exc = float((verdict == "优秀").mean()) if n else np.nan

        # 最长有效异常段
        eff = g["帧级异常_连续过滤后"].fillna(0).astype(int).values
        max_streak = 0
        cur = 0
        for v in eff:
            if v == 1:
                cur += 1
                max_streak = max(max_streak, cur)
            else:
                cur = 0

        # 每指标审判统计（核心：每个指标都审判）
        metric_stats = {}
        for m in METRICS:
            col = f"{m}__审判_0标准1轻微2异常"
            vv = pd.to_numeric(g[col], errors="coerce")
            metric_stats[f"{m}__标准占比"] = float((vv == 0).mean())
            metric_stats[f"{m}__轻微占比"] = float((vv == 1).mean())
            metric_stats[f"{m}__异常占比"] = float((vv == 2).mean())

        # Top问题指标（按异常占比）
        abn_rates = {m: metric_stats[f"{m}__异常占比"] for m in METRICS}
        top = sorted(abn_rates.items(), key=lambda x: (-(x[1] if x[1] == x[1] else -1)))[:3]
        top_str = "; ".join([f"{m}: {rate:.3f}" for m, rate in top])

        # 视频级最终判定（可解释、可调整）
        # 这里用连续过滤后的“不标准”占比 + 最长异常段
        if (p_bad > 0.20) or (max_streak >= 10):
            video_verdict = "不标准"
        elif p_bad > 0.05:
            video_verdict = "基本标准"
        else:
            video_verdict = "标准"

        row = {
            "视频ID": str(vid),
            "总帧数": int(n),
            "优秀帧占比": p_exc,
            "标准帧占比": p_std,
            "基本标准帧占比": p_basic,
            "不标准帧占比_连续过滤后": p_bad,
            "最长异常连续帧数": int(max_streak),
            "Top问题指标(按异常占比)": top_str,
            "视频判定": video_verdict,
        }
        row.update(metric_stats)
        rows.append(row)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", type=str, default="outputs_metrics/逐帧指标.csv",
                        help="输入：你之前生成的逐帧指标.csv")
    parser.add_argument("--out_dir", type=str, default="standard_analysis_out",
                        help="输出目录")
    parser.add_argument("--p_low", type=float, default=DEFAULT_P_LOW,
                        help="主合规区间下分位（如10）")
    parser.add_argument("--p_high", type=float, default=DEFAULT_P_HIGH,
                        help="主合规区间上分位（如90）")
    parser.add_argument("--band", type=str, default="标准",
                        choices=["严格", "标准", "宽松", "主合规"],
                        help="用于审判的区间档位")
    parser.add_argument("--min_streak", type=int, default=DEFAULT_MIN_STREAK,
                        help="连续异常帧过滤阈值（如3）")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.input_csv)
    require_columns(df, [COL_VIDEO, COL_FRAME] + METRICS)

    # 1) 标准区间表（含三档 + 主合规）
    bounds = robust_quantile_bounds(df, METRICS, p_low=args.p_low, p_high=args.p_high)
    bounds_path = os.path.join(args.out_dir, "标准区间表_三档.csv")
    bounds.to_csv(bounds_path, index=False, encoding="utf-8-sig")

    # 2) 生成“每指标审判规则表”
    rule_table = build_rule_table(
        bounds=bounds,
        weights=DEFAULT_WEIGHTS,
        rules=DEFAULT_RULE,
        use_band=args.band
    )
    rule_path = os.path.join(args.out_dir, "每指标审判规则表.csv")
    rule_table.to_csv(rule_path, index=False, encoding="utf-8-sig")

    # 3) 帧级：每指标审判 + 综合评分
    df_judged = apply_rules_per_metric(df, rule_table)

    # 4) 连续异常过滤
    df_judged = add_streak_filter(df_judged, min_streak=args.min_streak)

    frame_path = os.path.join(args.out_dir, "逐帧审判结果.csv")
    df_judged.to_csv(frame_path, index=False, encoding="utf-8-sig")

    # 5) 视频级：每指标统计 + Top问题指标 + 视频判定
    summary = video_level_summary(df_judged, rule_table)
    summary_path = os.path.join(args.out_dir, "视频级审判汇总_含每指标统计.csv")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"[OK] 标准区间表(三档): {bounds_path}")
    print(f"[OK] 每指标审判规则表: {rule_path}")
    print(f"[OK] 逐帧审判结果: {frame_path}")
    print(f"[OK] 视频级审判汇总(含每指标统计): {summary_path}")


if __name__ == "__main__":
    main()
