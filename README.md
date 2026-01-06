# 🏌️ 高尔夫挥杆分析系统 - 快速入门

## 📋 项目简介

一个基于 AI 的高尔夫挥杆视频分析系统，自动检测动作缺陷并提供改进建议。

**核心功能**：

- 🎥 视频上传（支持侧面/正面视角）
- 🤖 AI 自动分析（关键帧提取、关键点检测、缺陷识别）
- 📊 可视化报告（骨架视频、指标曲线、AI 建议）
- 🌐 Web 界面（支持中英文）

---

## 🚀 快速开始

### 1. 环境要求

- **Python**: 3.10 或 3.11
- **内存**: 建议 8GB+
- **系统**: Windows/Linux/macOS

### 2. 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd 项目汇总

# 2. 创建虚拟环境
python -m venv venv

# Windows 激活
venv\Scripts\Activate.ps1

# Linux/macOS 激活
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载模型权重
# 将 swingnet_2000.pth.tar 放到 Extract_key_frames/ 目录
```

### 3. 配置（可选）

如需 AI 反馈功能，创建 `.env` 文件：

```bash
SPARK_API_KEY=your_api_key_here
```

### 4. 启动应用

```bash
python app.py
```

访问：`http://localhost:80`

---

## 📖 使用指南

### 上传视频

1. 打开浏览器访问主页
2. 选择视角（侧面/正面）
3. 拖放或选择视频文件上传
4. 等待分析完成（自动后台处理）

### 查看结果

点击视频卡片查看：

- **原始视频**：上传的视频
- **骨架视频**：叠加关键点骨架
- **分析视频**：包含指标曲线和缺陷标注
- **数据表格**：逐帧详细数据
- **AI 建议**：动作改进建议

---

## 📁 项目结构

```
项目汇总/
├── app.py                    # Web 应用主程序
├── config.py                 # 配置文件
├── requirements.txt          # 依赖清单
├── Extract_key_frames/       # 关键帧提取模块
├── Keypoint_detection/       # 关键点检测模块
├── Keyframe_analysis/        # 关键帧分析模块
├── analyze/                  # 运动分析模块
├── visualization/            # 可视化模块
├── templates/                # HTML 模板
├── static/                   # 静态资源
└── uploads/                  # 上传文件目录
```

---

## ⚙️ 配置说明

编辑 `config.py` 自定义设置：

```python
APP_CONFIG = {
    'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,  # 最大上传 500MB
    'MAX_UPLOADS_PER_HOUR': 5,                # 每小时最多 5 次
    'MAX_VIDEOS_RETAINED': 9,                 # 保留最新 10 条记录
}
```

---

## 🐛 常见问题

### 1. 视频无法播放

安装 FFmpeg：

- **Windows**: [下载 FFmpeg](https://www.gyan.dev/ffmpeg/builds/) 并添加到 PATH
- **Linux**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

### 2. 端口 80 被占用

编辑 `app.py` 修改端口：

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)  # 改为 5000
```

### 3. 分析失败

检查：

- 视频中人物是否清晰可见
- 视频分辨率是否过高（建议 1080p）
- 磁盘空间是否充足
- 模型权重文件是否存在

### 4. AI 反馈不显示

- 检查 `.env` 文件中的 API Key 是否配置
- 不影响基本分析功能，可选使用

---

## 📊 分析指标说明

### 侧面视角（Down-the-line）

- 上身前倾角度
- 头部位移
- 髋部旋转
- 肩部旋转
- X-Factor（肩髋分离角）
- 重心转移

### 正面视角（Face-on）

- 身体侧倾角度
- 肩部水平度
- 髋部水平度
- 双脚宽度
- 重心位置
- 上下半身协调性

---

## 🔧 维护操作

### 清理数据

```bash
# 系统会自动保留最新 10 条记录
# 手动清理所有数据：
rm -rf uploads/* analyze/output/* visualization/output/*
rm golf_analysis.db
```

### 备份数据

```bash
# 备份数据库
sqlite3 golf_analysis.db ".backup backup.db"

# 完整备份
tar -czf backup_$(date +%Y%m%d).tar.gz golf_analysis.db uploads/
```

### 查看日志

```bash
# 运行时查看日志
python app.py 2>&1 | tee app.log

# 实时查看
tail -f app.log
```

---

## 📚 核心依赖

```
Flask==3.1.2              # Web 框架
pandas==2.3.3             # 数据处理
numpy==2.2.6              # 数值计算
opencv-python==4.12.0.88  # 视频处理
mediapipe==0.10.14        # 关键点检测
torch==2.7.1              # 深度学习
```

---

## 📄 许可证

[MIT License](LICENSE)
