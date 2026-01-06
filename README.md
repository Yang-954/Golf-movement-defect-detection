# 高尔夫挥杆动作缺陷检测与分析系统

## 📋 项目简介

本项目是一个完整的高尔夫挥杆视频分析系统，提供从视频上传、关键帧提取、关键点检测到动作缺陷分析的全流程解决方案。系统采用 Flask Web 框架，结合 MediaPipe 关键点检测技术和深度学习模型，实现自动化的挥杆动作评估与可视化展示。

### 🎯 核心功能

#### 1. Web界面与视频管理
- **视频上传与管理**：支持 MP4、AVI、MOV、MKV 等多种格式，最大 500MB
- **双视角支持**：侧面视角和正面视角独立分析
- **实时状态跟踪**：上传后自动分析，实时显示处理进度
- **历史记录管理**：视频列表展示、批量删除、缩略图预览
- **多语言支持**：中英文界面切换

#### 2. 智能限流与数据管理
- **IP访问限流**：每个IP地址每小时最多上传5次（可配置）
- **自动数据清理**：系统仅保留最新10条记录（可配置），自动清理过期数据
- **孤儿文件清理**：定期清理数据库中不存在的残留文件
- **实时配额显示**：前端显示剩余上传次数和数据保留策略

#### 3. 视频分析流水线
- **关键帧提取**：基于深度学习模型自动识别挥杆动作的8个关键事件
- **关键点检测**：使用 MediaPipe 检测人体33个关键点，实时跟踪动作
- **指标计算**：提取角度、距离、速度等动作特征指标
- **缺陷判断**：基于专业标准阈值，自动识别动作缺陷
- **AI反馈生成**：智能分析动作问题，提供改进建议

#### 4. 可视化与报告
- **骨架视频生成**：叠加关键点骨架的可视化视频
- **分析面板视频**：包含实时指标曲线和缺陷标注的可视化
- **详细分析报告**：
  - 逐帧分析数据
  - 视频级汇总评分
  - 关键帧深度分析
  - 问题排序与建议

## 🚀 快速开始

### 环境要求

- **操作系统**：Windows 10/11、Linux、macOS
- **Python**：3.10 或 3.11（推荐）
- **内存**：建议 8GB 以上
- **GPU**（可选）：NVIDIA GPU（CUDA 11+）用于加速

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd 项目汇总
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

### 核心依赖

```
Flask==3.0.0              # Web框架
pandas==2.0.3             # 数据处理
numpy==1.24.3             # 数值计算
opencv-python==4.8.1.78   # 视频处理
mediapipe==0.10.8         # 关键点检测
Werkzeug==3.0.1           # WSGI工具
```

### 启动应用

```bash
python app.py
```

访问 `http://localhost` 打开Web界面。

## 📁 项目结构

```
项目汇总/
├── app.py                          # Flask主应用
├── config.py                       # 系统配置
├── run_full_analysis.py           # 完整分析流水线入口
├── video_utils.py                 # 视频处理工具
├── ai反馈.py                       # AI反馈生成
│
├── Extract_key_frames/            # 关键帧提取模块
│   ├── Extract_key_frames.py     # 关键帧提取主脚本
│   ├── model.py                   # SwingNet模型定义
│   ├── MobileNetV2.py            # MobileNetV2骨干网络
│   └── output/                    # 关键帧输出目录
│
├── Keypoint_detection/            # 关键点检测模块
│   ├── export_all_keypoints.py   # 关键点导出脚本
│   └── output_single/            # 关键点数据输出
│
├── Keyframe_analysis/             # 关键帧分析模块
│   ├── 侧面提取指标.py           # 侧面指标计算
│   ├── 正面提取指标.py           # 正面指标计算
│   ├── 侧面缺陷判断.py           # 侧面缺陷识别
│   ├── 正面缺陷判断.py           # 正面缺陷识别
│   ├── run_keyframe_analysis.py  # 关键帧分析入口
│   └── output/                    # 分析结果输出
│
├── analyze/                       # 运动分析模块
│   ├── 侧向标准判断.py           # 侧面标准判断
│   ├── 正面标准判断.py           # 正面标准判断
│   ├── run_single_analysis.py    # 单视频分析
│   └── output/                    # 分析输出
│
├── visualization/                 # 可视化模块
│   ├── generate_visualization_video.py  # 生成可视化视频
│   └── output/                    # 可视化视频输出
│
├── templates/                     # HTML模板
│   ├── index.html                # 主页
│   ├── analysis.html             # 侧面分析页
│   └── analysis_front.html       # 正面分析页
│
├── static/                        # 静态资源
│   ├── css/                      # 样式文件
│   ├── js/                       # JavaScript文件
│   └── thumbnails/               # 视频缩略图
│
├── uploads/                       # 上传视频存储
└── golf_analysis.db              # SQLite数据库
```

## ⚙️ 配置说明

### config.py 主要配置项

```python
APP_CONFIG = {
    'SECRET_KEY': 'golf-swing-analysis-2025',
    'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,  # 最大上传文件大小：500MB
    'UPLOAD_FOLDER': 'uploads',                # 上传目录
    'DATABASE': 'golf_analysis.db',            # 数据库文件
    'ALLOWED_EXTENSIONS': {'mp4', 'avi', 'mov', 'mkv'},
    
    # IP限流配置
    'MAX_UPLOADS_PER_HOUR': 5,    # 每个IP每小时最多上传次数
    
    # 数据保留配置
    'MAX_VIDEOS_RETAINED': 10      # 系统最多保留的视频数量
}
```

### 其他配置模块

- **KEYFRAME_CONFIG**：关键帧提取配置（模型路径、序列长度等）
- **KEYPOINT_CONFIG**：关键点检测配置（输出目录、模型复杂度）
- **ANALYSIS_CONFIG**：运动分析配置（标准范围文件路径）
- **KEYFRAME_ANALYSIS_CONFIG**：关键帧分析配置
- **VISUALIZATION_CONFIG**：可视化配置（面板宽度、输出目录）

## 🔄 完整分析流程

### 1. 视频上传
```
用户上传视频 → IP限流检查 → 文件保存 → 生成缩略图 → 数据库记录
```

### 2. 自动分析（后台任务）
```
视频转码（兼容性） → 关键帧提取 → 关键点检测 → 指标计算 → 缺陷判断 → 可视化生成
```

### 3. 数据清理
```
检查数据量 → 删除超出限制的旧数据 → 清理文件系统 → 清理数据库 → 清理孤儿文件
```

### 详细步骤

#### 步骤1：关键帧提取
- 使用 SwingNet 深度学习模型
- 识别8个关键事件：Address, Toe-up, Mid-backswing, Top, Mid-downswing, Impact, Mid-follow-through, Finish
- 输出关键帧图像和事件时间戳

#### 步骤2：关键点检测
- 使用 MediaPipe Pose 检测33个人体关键点
- 实时跟踪身体姿态变化
- 输出关键点坐标和可见性信息

#### 步骤3：指标计算
根据视角不同计算相应指标：

**侧面指标**：
- 上身前倾角度
- 头部位移
- 髋部旋转角度
- 肩部旋转角度
- 膝盖弯曲角度
- 脊柱角度
- 手臂伸展度
- 重心转移

**正面指标**：
- 身体侧倾角度
- 肩部水平度
- 髋部水平度
- 双脚宽度
- 重心位置
- 上下半身协调性

#### 步骤4：缺陷判断
- 基于专业标准阈值范围
- 逐帧评分和判定
- 识别常见错误：
  - 上身过度前倾/后仰
  - 头部移动过大
  - 髋部旋转不足
  - 重心转移不当
  - 身体协调性问题

#### 步骤5：可视化生成
- 骨架视频：叠加关键点连线
- 分析面板视频：包含实时指标曲线图
- 缺陷标注：高亮问题帧

## 💾 数据库结构

系统使用 SQLite 数据库，包含以下主要表：

- **videos**：视频基本信息（ID、文件名、视角、状态等）
- **analysis_results**：分析结果汇总（CSV路径、可视化路径、AI反馈等）
- **frame_analysis_details**：逐帧分析详情（侧面）
- **frame_analysis_details_front**：逐帧分析详情（正面）
- **video_analysis_summary**：视频级汇总（侧面）
- **video_analysis_summary_front**：视频级汇总（正面）
- **keyframe_analysis_details**：关键帧分析详情（侧面/正面）
- **metric_standards**：指标标准阈值

## 🔐 限流与安全

### IP限流机制
- 使用内存字典存储IP访问记录
- 自动清理1小时前的记录
- 超过限制返回 HTTP 429 状态码
- 支持代理环境下的真实IP识别（X-Forwarded-For）

### 数据清理机制
1. **定时清理**：每次上传后自动触发
2. **清理范围**：
   - 上传的视频文件（原始+转码）
   - 视频缩略图
   - 所有分析输出目录
   - 关键帧提取结果
   - 可视化视频
   - 数据库相关记录
3. **孤儿文件清理**：清理数据库中不存在但文件系统残留的文件

## 🌐 API接口

### GET /config
获取系统配置信息
```json
{
  "max_videos_retained": 10,
  "max_uploads_per_hour": 5
}
```

### POST /upload
上传视频并触发分析
- **请求**：multipart/form-data（video文件 + view_angle）
- **响应**：
  ```json
  {
    "video_id": "10_20260106_155047",
    "message": "视频上传成功，正在后台分析...",
    "status": "processing",
    "remaining_uploads": 4
  }
  ```
- **错误**：HTTP 429（超过限流限制）

### GET /videos
获取所有视频列表
- **响应**：视频数组（禁用缓存）

### GET /videos/<video_id>
获取特定视频的分析结果

### POST /videos/delete
批量删除视频

## 📊 输出文件说明

### 1. 关键帧提取输出
```
Extract_key_frames/output/YYYYMMDD_HHMMSS/
  └── events.json  # 关键事件时间戳
```

### 2. 关键点检测输出
```
Keypoint_detection/output_single/VIDEO_ID/
  └── 单视频_缺陷分析数据.csv  # 所有帧的关键点坐标
```

### 3. 分析结果输出
```
analyze/output/VIDEO_ID/
  ├── 侧面_逐帧审判结果.csv      # 每帧的指标和判定
  └── 侧面_视频级审判汇总.csv    # 整体评分和问题总结
```

### 4. 关键帧分析输出
```
Keyframe_analysis/output/VIDEO_ID/
  ├── 侧面_关键帧分析_逐帧详情.csv
  └── 侧面_关键帧分析_视频汇总.csv
```

### 5. 可视化输出
```
visualization/output/
  ├── VIDEO_ID_侧面_skeleton.webm    # 骨架视频
  └── VIDEO_ID_侧面_可视化.webm      # 带分析面板的视频
```

## 🎨 前端功能

### 主页（index.html）
- 视频上传表单（拖放支持）
- 上传限额实时显示
- 视频列表网格展示
- 缩略图预览
- 状态实时更新
- 批量管理操作

### 分析页面（analysis.html / analysis_front.html）
- 视频播放器（原始/骨架/可视化视频切换）
- 分析数据表格（逐帧/汇总）
- AI反馈建议
- 数据导出功能
- 多语言支持

## 🛠️ 开发指南

### 添加新的分析指标

1. 在对应的指标计算文件中添加计算逻辑：
   - `Keyframe_analysis/侧面提取指标.py`
   - `Keyframe_analysis/正面提取指标.py`

2. 在标准范围CSV中添加阈值：
   - `Keyframe_analysis/侧面normal_ranges_*.csv`
   - `Keyframe_analysis/正面normal_ranges_*.csv`

3. 更新数据库表结构（如需要）

### 自定义限流规则

修改 `config.py`：
```python
'MAX_UPLOADS_PER_HOUR': 10,  # 改为每小时10次
'MAX_VIDEOS_RETAINED': 20     # 改为保留20条记录
```

### 扩展AI反馈

修改 `ai反馈.py`，自定义反馈生成逻辑。

## 🐛 常见问题

### 1. MediaPipe 安装失败
- **原因**：Python版本不兼容或缺少 Visual C++ 运行库
- **解决**：
  - 使用 Python 3.10 或 3.11
  - Windows：安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 2. 视频无法播放
- **原因**：视频编码不兼容
- **解决**：系统会自动尝试转码为 H.264/WebM 格式

### 3. 分析卡住不动
- **检查**：
  - 查看控制台日志
  - 确认视频质量和分辨率
  - 检查磁盘空间

### 4. IP限流误触发
- **原因**：代理或负载均衡导致IP识别错误
- **解决**：
  - 检查 X-Forwarded-For 头设置
  - 临时提高限流阈值

### 5. 数据清理过于激进
- **原因**：MAX_VIDEOS_RETAINED 设置过小
- **解决**：在 `config.py` 中增大该值

## 📝 性能优化建议

### 1. 视频预处理
- 降低分辨率（推荐 720p）
- 裁剪无关区域
- 使用 ffmpeg 预转码

### 2. 批量处理
- 使用队列系统（Celery）
- 并行处理多个视频
- 分离前端和分析服务

### 3. 存储优化
- 使用对象存储（S3/OSS）
- 定期归档旧数据
- 压缩中间文件

### 4. 数据库优化
- 添加索引（video_id, upload_time）
- 定期 VACUUM 清理
- 考虑迁移到 PostgreSQL

## 🔄 系统维护

### 手动清理数据
```bash
# 查看当前数据量
sqlite3 golf_analysis.db "SELECT COUNT(*) FROM videos;"

# 清理会在下次上传时自动触发
# 或重启应用后首次访问时清理
```

### 备份数据库
```bash
# 备份
sqlite3 golf_analysis.db ".backup backup_$(date +%Y%m%d).db"

# 恢复
sqlite3 golf_analysis.db ".restore backup_20260106.db"
```

### 日志查看
系统日志输出到控制台，建议使用日志管理工具：
```bash
python app.py 2>&1 | tee app.log
```

## 📄 许可证

请参考项目根目录的 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 项目文档：查看 [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md)

## 🎓 技术栈

- **后端**：Flask、SQLite
- **AI/ML**：MediaPipe、PyTorch/TensorFlow（SwingNet）
- **视频处理**：OpenCV、FFmpeg
- **前端**：原生 JavaScript、HTML5、CSS3
- **数据处理**：Pandas、NumPy

---

**更新日期**：2026年1月6日  
**版本**：v2.0.0
