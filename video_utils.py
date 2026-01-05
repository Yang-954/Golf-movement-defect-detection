import cv2
import os
import sys

def convert_video_to_compatible_format(input_path, output_dir=None):
    """
    将视频转换为浏览器兼容格式 (H.264/MP4 或 VP8/WEBM)
    返回转换后的文件路径，如果转换失败则返回None
    """
    if not os.path.exists(input_path):
        print(f"[转码] 输入文件不存在: {input_path}")
        return None

    # 生成输出路径
    directory = output_dir if output_dir else os.path.dirname(input_path)
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    
    # 策略列表
    strategies = [
        {'codec': 'avc1', 'ext': '.mp4', 'name': 'H.264'},
        {'codec': 'vp80', 'ext': '.webm', 'name': 'VP8'},
        {'codec': 'mp4v', 'ext': '.mp4', 'name': 'MPEG-4'}
    ]
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"[转码] 无法打开视频文件: {input_path}")
        return None
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 如果无法获取FPS，默认30
    if fps <= 0 or fps > 120:
        fps = 30.0
        
    print(f"[转码] 视频信息: {width}x{height}, {fps:.2f} fps, {total_frames} frames")
        
    success_path = None
    
    for strategy in strategies:
        # 如果原视频已经是该格式，且我们假设原视频可能不兼容，
        # 我们仍然尝试转码，但文件名要区分
        output_path = os.path.join(directory, f"{name}_web{strategy['ext']}")
        
        print(f"[转码] 尝试策略: {strategy['name']} -> {os.path.basename(output_path)}")
        
        try:
            fourcc = cv2.VideoWriter_fourcc(*strategy['codec'])
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                print(f"[转码] 无法初始化编码器: {strategy['name']}")
                continue
                
            # 重置读取位置
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                frame_count += 1
                
                if frame_count % 100 == 0:
                    print(f"  - 转码进度: {frame_count}/{total_frames}")
            
            out.release()
            
            if frame_count > 0:
                print(f"[转码] 成功: {output_path}")
                success_path = output_path
                break
            else:
                print(f"[转码] 失败: 生成了0帧")
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                    
        except Exception as e:
            print(f"[转码] 异常: {e}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            continue
            
    cap.release()
    return success_path
