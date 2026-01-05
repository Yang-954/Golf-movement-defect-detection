import os
import argparse
import numpy as np
import pandas as pd

COL_VIDEO = "视频ID"
COL_FRAME = "帧序号"

METRICS = [
    "左髋X轴位移_正面",
    "右髋X轴位移_正面",
    "躯干中点Y轴位移_正面",
    "肩线中心X轴位移_正面",
    "肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面",
    "髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面",
]

DEFAULT_P_LOW = 10
DEFAULT_P_HIGH = 90
DEFAULT_MIN_STREAK = 3

DEFAULT_WEIGHTS = {
    "左髋X轴位移_正面": 1.0,
    "右髋X轴位移_正面": 1.0,
    "躯干中点Y轴位移_正面": 1.0,
    "肩线中心X轴位移_正面": 1.1,
    "肩线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面": 1.2,
    "髋线旋转角_与X轴夹角_左端终点_Y轴0度_朝镜头正负180_正面": 1.2,
}

DEFAULT_RULE = {m: "between" for m in METRICS}


def require_columns(df: pd.DataFrame, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")


def robust_quantile_bounds(df: pd.DataFrame, metrics, p_low: float, p_high: float) -> pd.DataFrame:
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

    bounds = pd.DataFrame(rows)
    bounds["下限_主合规"] = bounds[f"P{int(p_low)}"] if f"P{int(p_low)}" in bounds.columns else np.nan
    bounds["上限_主合规"] = bounds[f"P{int(p_high)}"] if f"P{int(p_high)}" in bounds.columns else np.nan
    return bounds


def build_rule_table(bounds: pd.DataFrame, weights: dict, rules: dict, use_band: str = "标准") -> pd.DataFrame:
    b = bounds.set_index("指标")

    def pick(m: str, band: str):
        if band == "严格":
            return float(b.loc[m, "下限_严格(P15)"]), float(b.loc[m, "上限_严格(P85)"])
        if band == "宽松":
            return float(b.loc[m, "下限_宽松(P5)"]), float(b.loc[m, "上限_宽松(P95)"])
        if band == "主合规":
            return float(b.loc[m, "下限_主合规"]), float(b.loc[m, "上限_主合规"])
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
    rt = rule_table.set_index("指标")
    
    # Filter metrics to only those present in the rule table
    available_metrics = [m for m in METRICS if m in rt.index]
    
    # Ensure we only select columns that exist in df
    cols_to_select = [COL_VIDEO, COL_FRAME] + [m for m in available_metrics if m in df.columns]
    out = df[cols_to_select].copy()

    for m in available_metrics:
        if m not in df.columns:
            continue
            
        x = pd.to_numeric(out[m], errors="coerce")
        lo = float(rt.loc[m, "下限"])
        hi = float(rt.loc[m, "上限"])

        ok = (x >= lo) & (x <= hi)
        low_bad = (x < lo)
        high_bad = (x > hi)

        width = (hi - lo) if (hi - lo) != 0 else 1e-9
        dev = pd.Series(0.0, index=out.index, dtype=float)
        dev = dev.mask(low_bad, (lo - x) / width)
        dev = dev.mask(high_bad, (x - hi) / width)
        dev = dev.fillna(np.nan).clip(lower=0)

        out[f"{m}__合规"] = ok.astype("Int64")
        out[f"{m}__超下限"] = low_bad.astype("Int64")
        out[f"{m}__超上限"] = high_bad.astype("Int64")
        out[f"{m}__偏差"] = dev

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

    weights = {row["指标"]: float(row["权重"]) for _, row in rule_table.iterrows()}

    dev_cols = [f"{m}__偏差" for m in available_metrics if f"{m}__偏差" in out.columns]
    
    if not dev_cols:
        out["帧级加权偏差"] = 0.0
        out["帧级评分_0到100"] = 100.0
    else:
        dev_mat = out[dev_cols].to_numpy(dtype=float)
        
        # Use weights only for available metrics
        w = np.array([weights.get(m, 1.0) for m in available_metrics if f"{m}__偏差" in out.columns], dtype=float)
        
        mask = np.isfinite(dev_mat)
        w_mat = np.tile(w.reshape(1, -1), (dev_mat.shape[0], 1))
        w_eff = np.where(mask, w_mat, 0.0)
        denom = w_eff.sum(axis=1)
        numer = np.where(mask, dev_mat, 0.0) * w_eff
        wdev = np.where(denom > 0, numer.sum(axis=1) / denom, np.nan)

        score = 100.0 * (1.0 - np.clip(wdev, 0.0, 1.0))
        out["帧级加权偏差"] = wdev
        out["帧级评分_0到100"] = score

    judge_cols = [f"{m}__审判_0标准1轻微2异常" for m in available_metrics if f"{m}__审判_0标准1轻微2异常" in out.columns]
    if judge_cols:
        judge_mat = out[judge_cols].to_numpy(dtype=float)
        abnormal_cnt = np.nansum(judge_mat == 2, axis=1)
    else:
        abnormal_cnt = np.zeros(len(out))

    out["异常指标数_帧级"] = abnormal_cnt.astype(int)

    def frame_verdict(a_cnt, s):
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

    def adjust(row):
        if row["帧级结论"] == "不标准" and int(row["帧级异常_连续过滤后"]) == 0:
            return "基本标准"
        return row["帧级结论"]

    df_flagged["帧级结论_连续过滤后"] = df_flagged.apply(adjust, axis=1)
    return df_flagged


def video_level_summary(df_flagged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for vid, g in df_flagged.groupby(COL_VIDEO, sort=True):
        g = g.sort_values(COL_FRAME)
        n = len(g)

        verdict = g["帧级结论_连续过滤后"]
        p_bad = float((verdict == "不标准").mean()) if n else np.nan
        p_std = float((verdict == "标准").mean()) if n else np.nan
        p_basic = float((verdict == "基本标准").mean()) if n else np.nan
        p_exc = float((verdict == "优秀").mean()) if n else np.nan

        eff = g["帧级异常_连续过滤后"].fillna(0).astype(int).values
        max_streak = 0
        cur = 0
        for v in eff:
            if v == 1:
                cur += 1
                max_streak = max(max_streak, cur)
            else:
                cur = 0

        metric_stats = {}
        # Only check metrics that have judgment columns in the dataframe
        available_metrics = [m for m in METRICS if f"{m}__审判_0标准1轻微2异常" in g.columns]
        
        for m in available_metrics:
            vv = pd.to_numeric(g[f"{m}__审判_0标准1轻微2异常"], errors="coerce")
            metric_stats[f"{m}__异常占比"] = float((vv == 2).mean())

        top = sorted(metric_stats.items(), key=lambda x: -x[1])[:3]
        top_str = "; ".join([f"{k.replace('__异常占比','')}: {v:.3f}" for k, v in top])

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
    parser.add_argument("--input_csv", type=str, default="outputs_metrics_faceon/逐帧指标_正面.csv")
    parser.add_argument("--out_dir", type=str, default="standard_analysis_out_faceon")
    parser.add_argument("--p_low", type=float, default=DEFAULT_P_LOW)
    parser.add_argument("--p_high", type=float, default=DEFAULT_P_HIGH)
    parser.add_argument("--band", type=str, default="标准", choices=["严格", "标准", "宽松", "主合规"])
    parser.add_argument("--min_streak", type=int, default=DEFAULT_MIN_STREAK)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.input_csv)
    require_columns(df, [COL_VIDEO, COL_FRAME] + METRICS)

    bounds = robust_quantile_bounds(df, METRICS, p_low=args.p_low, p_high=args.p_high)
    bounds_path = os.path.join(args.out_dir, "标准区间表_正面.csv")
    bounds.to_csv(bounds_path, index=False, encoding="utf-8-sig")

    rule_table = build_rule_table(bounds, DEFAULT_WEIGHTS, DEFAULT_RULE, use_band=args.band)
    rule_path = os.path.join(args.out_dir, "每指标审判规则表_正面.csv")
    rule_table.to_csv(rule_path, index=False, encoding="utf-8-sig")

    df_judged = apply_rules_per_metric(df, rule_table)
    df_judged = add_streak_filter(df_judged, min_streak=args.min_streak)

    frame_path = os.path.join(args.out_dir, "逐帧审判结果_正面.csv")
    df_judged.to_csv(frame_path, index=False, encoding="utf-8-sig")

    summary = video_level_summary(df_judged)
    summary_path = os.path.join(args.out_dir, "视频级审判汇总_正面.csv")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"[OK] 标准区间表: {bounds_path}")
    print(f"[OK] 每指标审判规则表: {rule_path}")
    print(f"[OK] 逐帧审判结果: {frame_path}")
    print(f"[OK] 视频级审判汇总: {summary_path}")


if __name__ == "__main__":
    main()
