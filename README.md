项目汇总 — 高尔夫挥杆动作缺陷检测与分析
========================================

**简介**:

- 本项目用于从视频中提取关键帧、检测人体关键点并基于规则/阈值进行高尔夫挥杆动作缺陷检测与分析，包含单视频与批量分析流程，以及一个基于 Flask 的简单可视化界面。

**环境与依赖（建议）**:

- **操作系统**: Windows 10/11（开发时使用 Windows）。也可在 Linux 下运行。
- **Python**: 推荐使用 Python 3.10 或 3.11（确保与依赖兼容）。
- **编辑器**: 推荐使用 Visual Studio Code（最新稳定版），并安装 Python 扩展。
- **GPU（可选）**: 当前代码主要依赖 OpenCV 与 MediaPipe，默认使用 CPU。若需加速自定义深度学习推理，请准备 NVIDIA GPU（CUDA 11+），并安装相应的 GPU 版本框架（如 TensorFlow 或 PyTorch）与驱动。
- **系统库/工具**: Windows 上请确保安装了 Microsoft Visual C++ 运行库（部分包在编译时需要）。

**Python 依赖**（来自 requirements.txt）:

- Flask==3.0.0
- pandas==2.0.3
- numpy==1.24.3
- opencv-python==4.8.1.78
- mediapipe==0.10.8
- Werkzeug==3.0.1

安装依赖示例（Windows PowerShell）:

```
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**代码文件与目录说明**:

- **主要入口与服务**:
  - **[app.py](app.py)**: Flask 应用（可用来展示分析结果或提供简单的前端界面）。
  - **[run_full_analysis.py](run_full_analysis.py)**: 触发整个流水线的脚本（若存在整合逻辑，可做批量分析）。
- **视频与关键帧提取**:
  - **[Extract_key_frames/Extract_key_frames.py](Extract_key_frames/Extract_key_frames.py)**: 提取关键帧的主脚本。
  - **[Extract_key_frames/dataloader.py](Extract_key_frames/dataloader.py)**: 数据加载/视频处理辅助代码。
  - **[Extract_key_frames/model.py](Extract_key_frames/model.py)** 与 **[Extract_key_frames/MobileNetV2.py](Extract_key_frames/MobileNetV2.py)**: 模型定义/网络结构（若使用模型推理时参考）。
- **关键点检测**:
  - **[Keypoint_detection/export_all_keypoints.py](Keypoint_detection/export_all_keypoints.py)**: 导出/批量处理关键点信息的脚本。
  - 输出目录：**Keypoint_detection/output_single/**（包含 `单视频_缺陷分析数据.csv` 示例输出）。
- **关键帧指标与缺陷判断**:
  - **[Keyframe_analysis/侧面提取指标.py](Keyframe_analysis/侧面提取指标.py)** 和 **[Keyframe_analysis/正面提取指标.py](Keyframe_analysis/正面提取指标.py)**: 从关键帧计算动作指标。
  - **[Keyframe_analysis/侧面缺陷判断.py](Keyframe_analysis/侧面缺陷判断.py)** 与 **[Keyframe_analysis/正面缺陷判断.py](Keyframe_analysis/正面缺陷判断.py)**: 基于阈值/规则判断缺陷。
  - **[Keyframe_analysis/run_keyframe_analysis.py](Keyframe_analysis/run_keyframe_analysis.py)**: 运行关键帧分析的入口脚本。
  - 输出目录：**Keyframe_analysis/output/**（包含逐帧与视频级汇总 CSV）。
- **视频级与帧级规则审判（Analyze）**:
  - **[analyze/正面标准判断.py](analyze/正面标准判断.py)**、**[analyze/侧向标准判断.py](analyze/侧向标准判断.py)**: 按预定义标准对帧或视频进行判定。
  - 输入/输出示例文件：`analyze/output/` 下的 CSV 文件（逐帧与视频汇总）。
- **可视化**:
  - **[visualization/generate_visualization_video.py](visualization/generate_visualization_video.py)**: 将关键帧/关键点与判定结果可视化为视频。
  - 静态前端：`templates/` 与 `static/`（包含前端 HTML/JS/CSS，供 `app.py` 使用）。

**典型运行步骤（建议顺序）**:

1. 创建虚拟环境并安装依赖（见上文）。
2. 准备输入视频：将视频放入项目某个输入目录（例如创建 `inputs/`），或修改脚本中指定的路径。
3. 提取关键帧（单视频示例）:

```
python Extract_key_frames/Extract_key_frames.py --input path\to\video.mp4 --output Extract_key_frames/output/...
```

4. 导出关键点（若使用批处理）:

```
python Keypoint_detection/export_all_keypoints.py --input Extract_key_frames/output/ --output Keypoint_detection/output_single/
```

5. 关键帧指标计算与缺陷判断:

```
python Keyframe_analysis/run_keyframe_analysis.py --input Keypoint_detection/output_single/ --output Keyframe_analysis/output/
```

6. 汇总与可视化（可选）:

```
python visualization/generate_visualization_video.py --input Keyframe_analysis/output/ --out_video visualization/output/...
```

7. 启动前端展示（若需要交互查看）:

```
python app.py
# 打开浏览器访问 http://127.0.0.1:5000/ 或控制台提示的地址
```

注意：上述脚本的命令行参数与实际实现可能有差异，请参考各脚本顶部的参数说明或在脚本中搜索 `argparse`/参数解析部分以确认正确用法。

**操作注意事项与常见问题**:

- MediaPipe 在 Windows 下的安装有时依赖于特定 Python 版本，遇到安装问题请先确认 Python 版本并安装 Visual C++ 运行库。
- 如果出现性能瓶颈：
  - 使用更小分辨率的视频或先裁剪关注区域以减少处理开销；
  - 对自定义深度学习推理启用 GPU，并安装相应的 GPU 框架（本仓库当前依赖列表不包含 TensorFlow/PyTorch GPU 包）。
- 视频格式兼容性：OpenCV 支持常见编码（mp4、avi 等），但在 Windows 上有时受缺失 codec 影响，遇到读取失败可先用 ffmpeg 转码。
- 路径注意：Windows 下路径分隔请使用 `\\` 或使用原生的 Python 原始字符串（`r"C:\\path\\..."`）。
- 日志与调试：若脚本抛出 KeyError/IndexError，请检查输入 CSV/关键点文件是否按预期生成，或是否存在空帧/检测失败的情况。

**输出文件位置（常见）**:

- `Extract_key_frames/output/` — 关键帧提取结果
- `Keypoint_detection/output_single/` — 单视频关键点与缺陷数据
- `Keyframe_analysis/output/` — 关键帧分析逐帧与视频汇总
- `analyze/output/` — 规则审判产生的 CSV 汇总

**下一步建议**:

- 若需在服务器上部署分析流水线，建议将各步骤封装为可运行的 CLI 命令或 Docker 镜像，便于自动化与扩展。
- 若想利用 GPU 加速深度学习模型，补充安装并测试相应的 GPU 框架（并在 README 中记录 GPU 驱动与 CUDA 版本）。
