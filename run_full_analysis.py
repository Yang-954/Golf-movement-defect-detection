import argparse
import sys
import json
from pathlib import Path
import config

def _add_sys_path(p: Path):
    p_str = str(p.resolve())
    if p_str not in sys.path:
        sys.path.insert(0, p_str)


def main():
    parser = argparse.ArgumentParser(description="Golf swing: keyframes -> keypoints -> analysis")
    parser.add_argument("--video_path", type=str, required=True, help="输入视频路径")
    parser.add_argument("--view_angle", "--view", type=str, required=True, help="视频视角：侧面或正面")
    parser.add_argument("--video_id", type=str, default=None, help="视频ID（可选，用于文件命名）")

    # Keyframe extraction options
    parser.add_argument("--kf_weights", type=str, default=config.KEYFRAME_CONFIG['WEIGHTS_PATH'], help="关键帧模型权重(.pth.tar)")
    parser.add_argument("--kf_seq_length", type=int, default=config.KEYFRAME_CONFIG['SEQ_LENGTH'])
    parser.add_argument("--kf_num_events", type=int, default=config.KEYFRAME_CONFIG['NUM_EVENTS'], help="事件数量")
    parser.add_argument("--kf_decode", type=str, default=config.KEYFRAME_CONFIG['DECODE_METHOD'], choices=["ordered", "independent"])
    parser.add_argument("--kf_height", type=int, default=config.KEYFRAME_CONFIG['INPUT_SIZE'][0])
    parser.add_argument("--kf_width", type=int, default=config.KEYFRAME_CONFIG['INPUT_SIZE'][1])

    # Keypoint detection options
    parser.add_argument("--kp_output_dir", type=str, default=config.KEYPOINT_CONFIG['OUTPUT_DIR'], help="关键点CSV输出目录")
    parser.add_argument("--kp_scale", type=float, default=config.KEYPOINT_CONFIG['SCALE_FACTOR'], help="关键点检测前对帧放大倍数")
    parser.add_argument("--kp_model_complexity", type=int, default=config.KEYPOINT_CONFIG['MODEL_COMPLEXITY'], choices=[0, 1, 2], help="MediaPipe Pose 模型复杂度")

    # Analysis options
    parser.add_argument("--std_csv", type=str, default=None, help="标准范围CSV（不填则按view自动选）")
    parser.add_argument("--analysis_out_dir", type=str, default=config.ANALYSIS_CONFIG['OUTPUT_DIR'], help="分析结果输出目录")

    # Keyframe analysis options
    parser.add_argument("--keyframe_analysis_out_dir", type=str, default=config.KEYFRAME_ANALYSIS_CONFIG['OUTPUT_DIR'], help="关键帧分析输出目录")

    # Visualization options
    parser.add_argument("--enable_visualization", action="store_true", default=config.VISUALIZATION_CONFIG['ENABLE_VIZ'], help="是否生成可视化视频")
    parser.add_argument("--viz_output_dir", type=str, default=config.VISUALIZATION_CONFIG['OUTPUT_DIR'], help="可视化视频输出目录")
    parser.add_argument("--viz_panel_width", type=int, default=config.VISUALIZATION_CONFIG['PANEL_WIDTH'], help="可视化面板宽度")
    parser.add_argument("--generate_skeleton", action="store_true", default=config.VISUALIZATION_CONFIG['GENERATE_SKELETON'], help="是否生成骨架视频")

    args = parser.parse_args()
    
    # 标准化view参数 - 将中文转换为英文
    view_mapping = {
        "side": "side", 
        "front": "front", 
        "侧面": "side", 
        "正面": "front"
    }
    args.view = view_mapping.get(args.view_angle, args.view_angle)
    
    # 保存中文视角用于文件命名
    view_angle_cn = "侧面" if args.view == "side" else "正面"

    root = Path(__file__).resolve().parent
    extract_dir = root / "Extract_key_frames"
    keypoint_dir = root / "Keypoint_detection"
    analyze_dir = root / "analyze"
    keyframe_analysis_dir = root / "Keyframe_analysis"
    visualization_dir = root / "visualization"

    _add_sys_path(extract_dir)
    _add_sys_path(keypoint_dir)
    _add_sys_path(analyze_dir)
    _add_sys_path(keyframe_analysis_dir)
    _add_sys_path(visualization_dir)

    # -------------------- 1) Keyframes --------------------
    try:
        import Extract_key_frames as kf
    except Exception as e:
        if isinstance(e, ModuleNotFoundError):
            missing = getattr(e, "name", None)
            if missing in {"cv2", "torch", "torchvision"}:
                raise RuntimeError(
                    f"关键帧提取依赖缺失：{missing}。\n"
                    "请先安装依赖：pip install opencv-python torch torchvision\n"
                    "（或用 conda 安装对应包），再重试。"
                ) from e
        raise RuntimeError(
            "无法导入关键帧提取模块。请确认 Extract_key_frames/Extract_key_frames.py 及其依赖存在。"
        ) from e

    print("[1/4] 关键帧提取中...")
    kf_weights = args.kf_weights

    if not Path(kf_weights).exists():
        raise FileNotFoundError(
            f"关键帧模型权重不存在：{kf_weights}\n"
            "请通过 --kf_weights 指定正确的 .pth.tar 路径。"
        )

    kf_result = kf.extract_key_frames(
        video_path=args.video_path,
        weights=kf_weights,
        seq_length=args.kf_seq_length,
        num_events=args.kf_num_events,
        decode=args.kf_decode,
        height=args.kf_height,
        width=args.kf_width,
        output_root=str(extract_dir / "output"),
    )
    print(f"  - 关键帧图片输出目录: {kf_result['out_dir']}")
    print(f"  - 事件帧序号: {kf_result['events']}")
    
    # 保存events到JSON文件供后续使用
    events_json_path = Path(kf_result['out_dir']) / 'events.json'
    with open(events_json_path, 'w', encoding='utf-8') as f:
        # 将numpy数组转换为Python列表
        events_list = kf_result['events'].tolist() if hasattr(kf_result['events'], 'tolist') else list(kf_result['events'])
        json.dump({'events': events_list, 'num_events': kf_result.get('num_events', 8)}, f, indent=2)
    print(f"  - 事件信息已保存: {events_json_path}")

    # -------------------- 2) Keypoints --------------------
    try:
        import export_all_keypoints as kp
    except Exception as e:
        if isinstance(e, ModuleNotFoundError):
            missing = getattr(e, "name", None)
            if missing in {"cv2", "mediapipe"}:
                raise RuntimeError(
                    f"关键点检测依赖缺失：{missing}。\n"
                    "请先安装依赖：pip install opencv-python mediapipe\n"
                    "（或用 conda 安装对应包），再重试。"
                ) from e
        raise RuntimeError(
            "无法导入关键点检测模块。请确认已安装 mediapipe / opencv / pandas 等依赖，并且 Keypoint_detection/export_all_keypoints.py 存在。"
        ) from e

    kp_out_dir = args.kp_output_dir

    print("[2/4] 关键点检测中...")
    keypoints_csv = kp.process_video(
        args.video_path,
        kp_out_dir,
        scale=args.kp_scale,
        model_complexity=args.kp_model_complexity,
        video_id=args.video_id
    )
    if not keypoints_csv:
        raise RuntimeError("关键点检测未生成CSV（process_video 返回 None）。")
    print(f"  - 关键点CSV: {keypoints_csv}")

    # -------------------- 3) Analysis --------------------
    try:
        import run_single_analysis as analysis
    except Exception as e:
        raise RuntimeError(
            "无法导入运动分析模块。请确认 analyze/run_single_analysis.py 及相关标准判断脚本存在。"
        ) from e

    analysis_out_dir = args.analysis_out_dir

    # 确定标准文件路径
    if args.std_csv:
        std_csv_path = args.std_csv
    else:
        if args.view == "side":
            std_csv_path = config.ANALYSIS_CONFIG['STD_SIDE_PATH']
        else:
            std_csv_path = config.ANALYSIS_CONFIG['STD_FRONT_PATH']

    print("[3/4] 运动分析与缺陷判定中...")
    frame_out, video_out, summary_df = analysis.run_analysis(
        view=args.view,
        input_csv=keypoints_csv,
        std_csv=std_csv_path,
        out_dir=analysis_out_dir,
    )


    # -------------------- 4) Keyframe Analysis --------------------
    try:
        import run_keyframe_analysis as kfa
    except Exception as e:
        raise RuntimeError(
            "无法导入关键帧分析模块。请确认 Keyframe_analysis/run_keyframe_analysis.py 存在且依赖已安装。"
        ) from e

    keyframe_out_dir = args.keyframe_analysis_out_dir

    # 侧面和正面分别调用对应的关键帧分析
    if args.view == "side":
        kf_std_csv = config.KEYFRAME_ANALYSIS_CONFIG['STD_SIDE_PATH']
        print("[4/4] 关键帧幅度分析中...（侧面）")
        kf_frame_out, kf_video_out, kf_summary_df = kfa.run_keyframe_analysis(
            view="side",
            input_csv=keypoints_csv,
            out_dir=keyframe_out_dir,
            events=kf_result.get("events"),
            num_events=int(kf_result.get("num_events") or 8),
            std_csv=kf_std_csv,
        )
    else:
        kf_std_csv = config.KEYFRAME_ANALYSIS_CONFIG['STD_FRONT_PATH']
        print("[4/4] 关键帧幅度分析中...（正面）")
        kf_frame_out, kf_video_out, kf_summary_df = kfa.run_keyframe_analysis(
            view="front",
            input_csv=keypoints_csv,
            out_dir=keyframe_out_dir,
            events=kf_result.get("events"),
            num_events=int(kf_result.get("num_events") or 8),
            std_csv=kf_std_csv,
        )

    # Print final verdict
    verdict = None
    top_issues = None
    if summary_df is not None and len(summary_df) > 0:
        if "视频判定" in summary_df.columns:
            verdict = str(summary_df.iloc[0]["视频判定"])
        if "Top问题指标(按异常占比)" in summary_df.columns:
            top_issues = str(summary_df.iloc[0]["Top问题指标(按异常占比)"])

    print("\n========= 最终判定 =========")
    print(f"视角(view): {args.view}")
    print(f"视频: {args.video_path}")
    if verdict is not None:
        print(f"视频判定: {verdict}")
    else:
        print("视频判定: (未能从汇总表中读取)")

    if top_issues:
        print(f"Top问题指标: {top_issues}")

    # Print keyframe analysis verdict
    kf_verdict = None
    kf_top_issues = None
    if kf_summary_df is not None and len(kf_summary_df) > 0:
        if "视频判定" in kf_summary_df.columns:
            kf_verdict = str(kf_summary_df.iloc[0]["视频判定"])
        if "Top问题指标(按异常占比)" in kf_summary_df.columns:
            kf_top_issues = str(kf_summary_df.iloc[0]["Top问题指标(按异常占比)"])

    print("\n========= 关键帧分析判定 =========")
    if kf_verdict is not None:
        print(f"关键帧判定: {kf_verdict}")
    else:
        print("关键帧判定: (未能从汇总表中读取)")
    if kf_top_issues:
        print(f"关键帧Top问题指标: {kf_top_issues}")

    # -------------------- 5) Visualization (optional) --------------------
    viz_output = None
    skeleton_output = None
    
    if args.enable_visualization or args.generate_skeleton:
        try:
            import generate_visualization_video as viz
        except Exception as e:
            print(f"\n[警告] 无法导入可视化模块: {e}")
            print("跳过可视化视频生成。")
        else:
            viz_out_dir = args.viz_output_dir
            
            Path(viz_out_dir).mkdir(parents=True, exist_ok=True)
            
            # 生成输出文件名
            if args.video_id:
                base_name = args.video_id
            else:
                base_name = Path(args.video_path).stem
            
            # 生成标准可视化视频
            if args.enable_visualization:
                viz_output = str(Path(viz_out_dir) / f"{base_name}_{view_angle_cn}_可视化.mp4")
                
                print("\n[5a/6] 生成可视化视频中...")
                try:
                    actual_viz_output = viz.generate_visualization_video(
                        video_path=args.video_path,
                        keypoints_csv=keypoints_csv,
                        analysis_csv=frame_out,
                        output_path=viz_output,
                        panel_width=args.viz_panel_width
                    )
                    if actual_viz_output:
                        viz_output = actual_viz_output
                except Exception as e:
                    print(f"[错误] 可视化视频生成失败: {e}")
                    viz_output = None
            
            # 生成纯骨架视频（白底）
            if args.generate_skeleton:
                skeleton_output = str(Path(viz_out_dir) / f"{base_name}_{view_angle_cn}_skeleton.mp4")
                
                print("\n[5b/6] 生成骨架视频中...")
                try:
                    # 获取原视频尺寸和帧率
                    import cv2
                    cap = cv2.VideoCapture(args.video_path)
                    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    video_fps = cap.get(cv2.CAP_PROP_FPS)
                    cap.release()
                    
                    actual_skeleton_output = viz.generate_skeleton_only_video(
                        keypoints_csv=keypoints_csv,
                        output_path=skeleton_output,
                        video_width=video_width,
                        video_height=video_height,
                        fps=video_fps
                    )
                    if actual_skeleton_output:
                        skeleton_output = actual_skeleton_output
                except Exception as e:
                    print(f"[错误] 骨架视频生成失败: {e}")
                    skeleton_output = None

    print("\n========= 输出文件 =========")
    print(f"逐帧结果: {frame_out}")
    print(f"视频级汇总: {video_out}")
    print(f"关键帧逐帧详情: {kf_frame_out}")
    print(f"关键帧视频级汇总: {kf_video_out}")
    if viz_output:
        print(f"可视化视频: {viz_output}")
    if skeleton_output:
        print(f"骨架视频: {skeleton_output}")


if __name__ == "__main__":
    main()
