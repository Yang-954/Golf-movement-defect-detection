# 可视化视频生成模块

## 功能说明

本模块为高尔夫挥杆分析系统生成可视化视频，包含以下功能：

1. **关键点绘制**：在原视频上绘制MediaPipe检测的33个人体关键点和骨架连接
2. **参数指标显示**：在视频左侧添加信息面板，显示每帧的参数指标值
3. **评判结果标注**：为每个指标显示评判结果（标准/轻微/异常），使用不同颜色标识
4. **帧级评分**：显示每帧的综合评分和结论

## 目录结构

```
visualization/
├── generate_visualization_video.py  # 核心可视化模块
├── output/                          # 可视化视频输出目录
└── README.md                        # 本说明文档
```

## 使用方法

### 方法1：集成到完整分析流程

在运行 `run_full_analysis.py` 时添加 `--enable_visualization` 参数：

```bash
python run_full_analysis.py \
    --video_path "视频路径.mp4" \
    --view side \
    --enable_visualization \
    --viz_panel_width 400
```

**参数说明：**
- `--enable_visualization`：启用可视化视频生成
- `--viz_output_dir`：可视化视频输出目录（可选，默认为 `visualization/output`）
- `--viz_panel_width`：左侧信息面板宽度（可选，默认400像素）

### 方法2：为已分析的视频生成可视化

如果已经完成了关键点检测和分析，可以使用独立脚本生成可视化视频：

```bash
python run_visualization.py \
    --video "原始视频.mp4" \
    --keypoints "Keypoint_detection/output_single/单视频_缺陷分析数据.csv" \
    --analysis "analyze/output/侧面_逐帧审判结果.csv" \
    --output "输出路径.mp4" \
    --panel_width 400
```

**参数说明：**
- `--video`：原始视频文件路径（必需）
- `--keypoints`：关键点检测CSV文件路径（必需）
- `--analysis`：分析结果CSV文件路径，即逐帧审判结果（必需）
- `--output`：输出视频路径（可选，不指定则自动生成）
- `--panel_width`：左侧信息面板宽度（可选，默认400）
- `--fps`：输出视频帧率（可选，默认使用原视频帧率）

### 方法3：在Python代码中调用

```python
import sys
from pathlib import Path

# 添加模块路径
sys.path.append(str(Path(__file__).parent / "visualization"))
import generate_visualization_video as viz

# 生成可视化视频
viz.generate_visualization_video(
    video_path="视频.mp4",
    keypoints_csv="关键点.csv",
    analysis_csv="分析结果.csv",
    output_path="输出.mp4",
    panel_width=400
)
```

## 可视化效果说明

### 视频布局

```
+------------------+------------------------+
|   信息面板        |      原始视频 +        |
|   (左侧)          |      关键点绘制        |
|                  |                        |
| Frame: 123       |                        |
| Score: 95.5      |      [人体姿态]        |
| Result: 优秀      |      + 关键点          |
|                  |      + 骨架连接        |
| -----------      |                        |
| 指标1: 10.5°     |                        |
| Standard         |                        |
|                  |                        |
| 指标2: 15.3°     |                        |
| Minor            |                        |
|                  |                        |
| 指标3: 25.8°     |                        |
| Abnormal         |                        |
| ...              |                        |
+------------------+------------------------+
```

### 颜色标识

**关键点颜色：**
- 蓝色：面部和头部关键点（0-10）
- 黄色：上身和手臂关键点（11-16）
- 粉色：下身和腿部关键点（17-32）
- 绿色：骨架连接线

**评判结果颜色：**
- 绿色：标准（Standard）- 指标在正常范围内
- 黄色：轻微偏差（Minor）- 指标轻微超出范围
- 红色：异常（Abnormal）- 指标明显超出范围

**帧级评分颜色：**
- 绿色：≥90分（优秀）
- 黄色：70-89分（良好）
- 红色：<70分（需改进）

## 输出文件

可视化视频默认保存在 `visualization/output/` 目录下，文件名格式：
- 通过完整流程生成：`[原视频名]_[视角]_可视化.mp4`
- 通过独立脚本生成：`[原视频名]_可视化.mp4` 或自定义名称

## 性能说明

- 处理速度约为原视频帧率的1-5倍（取决于CPU性能）
- 建议使用中等分辨率视频（720p-1080p）以平衡质量和性能
- 处理过程中会显示进度信息

## 依赖要求

- opencv-python (cv2)
- numpy
- pandas

这些依赖已包含在关键点检测和分析模块中，无需额外安装。

## 故障排除

### 问题1：视频无法打开
**解决方法：**
- 确认视频文件路径正确
- 确认视频格式被OpenCV支持（推荐MP4格式）
- 尝试使用 `ffmpeg` 重新编码视频

### 问题2：CSV文件读取失败
**解决方法：**
- 确认CSV文件存在且未被其他程序占用
- 确认CSV文件格式正确（逗号分隔）
- 检查文件编码（应为UTF-8）

### 问题3：输出视频无法播放
**解决方法：**
- 尝试使用VLC等通用播放器
- 检查输出路径是否有写入权限
- 尝试更换输出格式（修改fourcc编码）

### 问题4：处理速度过慢
**解决方法：**
- 减小 `panel_width` 参数（如300）
- 使用较低分辨率的输入视频
- 关闭其他占用CPU的程序

## 自定义配置

如需自定义可视化效果，可修改 `generate_visualization_video.py` 中的以下参数：

```python
# 调整关键点和连接线粗细
cv2.circle(frame, (x, y), 4, color, -1)  # 关键点半径
cv2.line(frame, start, end, color, 2)    # 连接线粗细

# 调整信息面板样式
panel[:] = (40, 40, 40)  # 背景颜色 (B, G, R)
font_scale = 0.4         # 字体大小
line_height = 40         # 行间距

# 调整显示的指标数量
max_display = 12  # 最多显示的指标数
```

## 示例

完整示例命令：

```bash
# 完整分析并生成可视化
python run_full_analysis.py \
    --video_path "测试视频.mp4" \
    --view side \
    --enable_visualization

# 仅生成可视化（已有分析结果）
python run_visualization.py \
    --video "测试视频.mp4" \
    --keypoints "Keypoint_detection/output_single/单视频_缺陷分析数据.csv" \
    --analysis "analyze/output/侧面_逐帧审判结果.csv"
```
