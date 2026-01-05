技术细节说明 — 关键技术与实现建议
=====================================

说明：本文件为补充性的技术文档，保留项目根目录下的 `README.md` 原版内容不变。本文档聚焦关键帧提取、关键点检测（MediaPipe）与关键点分析的技术实现细节与工程建议，便于后续优化与复现。

一、总体流程回顾
- 视频预处理 → 关键帧检测/提取 → 关键点检测（Pose/Landmarks）→ 指标计算 → 缺陷判定 → 可视化/汇总。

二、关键帧提取（Keyframe Extraction）
- 参考项目：请参考 golfdb（https://github.com/wmcnally/golfdb）以获取对“击球帧”检测与事件定位的思路与实现细节。golfdb 的实现包含事件级标注与模型驱动的方法，可用于定位挥杆中的关键事件（如击球瞬间）。
- 常见技术选项（由轻到重）：
  1. 基于帧差/像素变化的启发式方法：计算相邻帧的像素差（或结构相似性 SSIM），当变化超过阈值时标记为候选关键帧。此法对场景切换/大幅运动敏感，适用于快速过滤。
  2. 基于光流（Optical Flow）和运动能量的检测：使用稠密/稀疏光流估计主体运动，结合运动能量曲线识别运动高峰（例如击球瞬间）。
  3. 基于视觉检测的事件分类器：对时间窗口内的帧使用 CNN（例如 MobileNet、ResNet）进行分类，或用时序模型（1D-CNN、LSTM、Temporal ConvNet）检测击球事件；golfdb 提供了训练/标注数据与事件定位思路，适合做二次验证/精排。
  4. 混合策略（推荐）：先用帧差/光流做候选过滤，再用轻量分类器做精排。此方案在效率与精度间取得平衡。

实现建议：
- 滑动窗口与非极大值抑制（NMS）：对检测到的候选关键帧在时间上做 NMS，避免多帧重复标注同一事件。
- 多尺度与 ROI：先检测并裁剪包含球手/球的 ROI，再在 ROI 内做细粒度检测，减少背景噪声影响。

三、关键点检测（Keypoint Detection）— MediaPipe
- 官方参考：MediaPipe Pose 文档 https://developers.google.com/mediapipe/solutions/vision/pose
- 推荐使用 MediaPipe 的 `pose` 或 `holistic` 方案获取人体关键点（landmarks）。主要要点：
  - 输出为一组标准化坐标（$x,y,z$），$x,y$ 为相对于图像宽高的归一化坐标；同时提供可视化与置信度分数（visibility/score）。
  - MediaPipe 在各种分辨率、角度下表现稳定，且自带平滑与时序滤波（可调整或关闭以做自定义滤波）。

使用细节与注意：
  - 坐标转换：将归一化坐标映射回像素坐标时，使用原始帧的宽高进行反算；若做跨摄像机或标定分析，请先进行相机内参校正或视角归一化。
  - 丢失/低置信点处理：对置信度低的点做插值（线性/样条）或用前 N 帧的平滑值填补，避免下游指标突变。
  - 实时与批处理：MediaPipe 的 CPU 性能良好，如需在大量视频上运行可考虑并行化（多进程）或在 GPU 上用兼容框架加速。

四、关键点分析技术（Keypoint Analysis）
本节列出常用的坐标变换、特征工程与判定方法，能支持“缺陷检测”模块的实现与优化。

1) 坐标归一化与对齐
- 目标：去除个体差异与摄像头尺度影响，使指标可比较。常用方法：
  - 以身体线段长度归一化（例如肩宽、躯干高度）：对所有点坐标除以参考距离 $d$（例如两肩之间欧氏距离）。
  - 平移对齐：将坐标系原点移动到骨盆或躯干关键点（例如 `mid_hip`）。
  - 旋转对齐：将躯干主方向旋转到固定方向，便于比较左右/前后视角。

2) 几何特征（角度/长度）
- 关节角度：用向量与点计算关节夹角。给定向量 $u$ 与 $v$，夹角 $\theta$ 可由下式计算：
$$
\\theta = \\arccos\\left(\\frac{u\\cdot v}{\\|u\\|\\,\\|v\\|}\\right)
$$
  或使用更稳定的 $\\operatorname{atan2}$ 差值方法计算二维角度差。
- 常用角度：肩-肘-腕角、髋-膝-踝角、躯干与地平线夹角等。

3) 时序特征（速度/加速度/峰值）
- 速度：$v_t = p_t - p_{t-1}$（或除以时间间隔）；加速度为速度差。
- 峰值检测：检测角速度/加速度的峰值以定位关键动作瞬间（如挥杆最大速度点）。

4) 平滑与滤波
- 对原始关键点序列做低通滤波或指数移动平均（EMA）以减少噪声：
$$
s_t = \\alpha x_t + (1-\\alpha) s_{t-1}
$$
  其中 $\\alpha\\in(0,1)$ 为平滑因子。

5) 缺失值与插值
- 若某些帧检测失败，使用线性/样条插值补全；对长时间缺失（例如 > 10 帧）则视为不可用并在结果中标注。

6) 判定策略（规则 vs 学习）
- 规则/阈值法：基于领域专家设定的角度/速度阈值直接判定（工程简单，易解释）。适用于明确的技术动作缺陷。
- 统计/范围基准：用训练集/样本计算正常区间（均值 ± kσ 或分位数范围），以统计差异做判定。
- 机器学习法：将时序特征（角度序列、速度峰值、归一化长度等）输入分类器（SVM、随机森林、轻量神经网络）进行判定；需要标注数据集用于训练。
- 序列模型：对于复杂的时间关系，可使用 LSTM、Temporal CNN 或 Transformer-based 模型学习时间上下文。

7) 序列对齐与相似度
- 若要比对动作路径（例如与标准动作模版对齐），推荐使用 Dynamic Time Warping (DTW) 或序列相似度度量，对齐时间维度后计算误差。

8) 多视角融合（若项目支持正面+侧面）
- 通过时间戳/关键帧对齐两视角的结果，融合角度与投影信息，或在三维重建（若有标定）后直接在世界坐标系中计算指标。

五、工程实现与性能优化建议
- 并行化：对视频文件使用多进程池并行运行关键帧提取与关键点检测，或把不同阶段拆成流水线任务（Producer/Consumer）。
- 存储格式：使用压缩 CSV 或 Parquet 存储关键点与中间指标，加速后续读取与分析。
- 日志与断点续跑：为每个视频/任务记录状态（processing/done/error），支持失败重试与断点续跑。
- 单元/集成测试：为关键转换函数（坐标系变换、角度计算、插值）添加测试用例，保证数学实现稳定。

六、实践示例（端到端建议命令）
- 建议流程（以项目脚本为基础，需先确认各脚本参数）：
```
python Extract_key_frames/Extract_key_frames.py --input inputs/video.mp4 --out_dir Extract_key_frames/output/
python Keypoint_detection/export_all_keypoints.py --input_dir Extract_key_frames/output/ --out_csv Keypoint_detection/output_single/points.csv
python Keyframe_analysis/run_keyframe_analysis.py --keypoints Keypoint_detection/output_single/points.csv --out_dir Keyframe_analysis/output/
python visualization/generate_visualization_video.py --analysis Keyframe_analysis/output/ --out visualization/output/video_with_annotations.mp4
```

七、参考资料
- golfdb 项目（关键帧 / 事件定位思路）：https://github.com/wmcnally/golfdb
- MediaPipe Pose（关键点检测 API 与说明）：https://developers.google.com/mediapipe/solutions/vision/pose
- 光流与帧差基础：OpenCV 文档（`cv2.calcOpticalFlowFarneback` / `cv2.absdiff`）

八、后续可选项（扩展方向）
- 标注工具：为复杂模型训练构建或扩充击球帧/缺陷标注集合（可使用 CVAT/LabelStudio）。
- 引入深度学习回归/检测器：若规则方法精度不足，可训练专用检测器定位击球帧或回归角度误差。
- 容器化与 CI：提供 Dockerfile 与 GitHub Actions 流水线，便于部署与自动化测试。

如需，我可以：
- 根据项目中每个脚本的实际参数将上面的示例命令逐个对齐并补全；
- 为关键算法（如角度计算、平滑、插值）补充示例代码片段并放入 `utils/`；
- 生成 Dockerfile 并提供快速部署说明。

*** 文档结束
