# encoding: UTF-8
import json
import requests
import sys
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# =====================================================
# 【方案 1】编码修复 —— 必须放在最前面
# =====================================================
try:
    # Python 3.7+：强制 stdout 使用 UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 对 Windows / PowerShell 兜底
os.environ["PYTHONIOENCODING"] = "utf-8"

# =====================================================
# 1. 星火接口配置
# =====================================================
API_KEY = os.getenv("SPARK_API_KEY")
if not API_KEY:
    # 尝试从硬编码读取（仅作为本地开发未配置环境变量时的后备，或者直接报错）
    # 为了安全，建议直接报错提示
    print("Error: SPARK_API_KEY environment variable not set.")
    # 也可以选择在这里保留一个空字符串或者抛出异常
    
URL = "https://spark-api-open.xf-yun.com/v1/chat/completions"
MODEL = "lite"   # 文档推荐的小写模型名

# =====================================================
# 2. Golf 运动健康专家 Prompt（System）
# =====================================================
SYSTEM_PROMPT = """
你是一名“高尔夫运动健康与挥杆动作风险分析专家（Golf Health & Biomechanics Expert）”。

你的任务是：
基于用户提供的【挥杆动作量化指标】，从“运动健康与长期伤病预防”的角度，
识别潜在的动作风险，并给出专业、克制、可执行的建议。

你不是击球效果教练，也不是医疗医生。

=====================
【工作原则】
=====================
1）只基于用户明确提供的指标、数值、单位、方向定义进行分析
2）健康优先：重点关注腰椎/下背、髋、膝、肩、肘腕的负荷与代偿
3）不进行医疗诊断，仅描述潜在风险与长期负荷
4）区分视角：
   - 正面：侧移、重心、上下起伏、左右对称
   - 侧面：前倾、转体、侧屈、空间与起身风险

=====================
【固定输出结构】
=====================
【1. 结论摘要】
【2. 指标证据说明】
【3. 动作模式与健康风险解释】
【4. 纠正方向（原则级）】
【5. 训练与自我提醒建议】
【6. 复测与跟踪建议】

语言风格：专业、理性、克制，不制造恐慌。
"""

# =====================================================
# 3. 星火 SSE 流式调用（UTF-8 强制解码）
# =====================================================
def spark_chat_stream(messages):
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "model": MODEL,
        "user": "user_id",
        "messages": messages,
        "stream": True
    }

    response = requests.post(
        URL,
        headers=headers,
        json=body,
        stream=True,
        timeout=60
    )

    # 【关键】强制 requests 使用 UTF-8
    response.encoding = "utf-8"

    if response.status_code != 200:
        print(f"\n[HTTP ERROR {response.status_code}] {response.text}")
        return ""

    full_response = ""

    # 【关键】不要用 decode_unicode=True，手动 UTF-8 解码最稳
    for raw in response.iter_lines(decode_unicode=False):
        if not raw:
            continue

        # 强制 UTF-8 解码，防止乱码
        line = raw.decode("utf-8", errors="replace").strip()

        if not line.startswith("data:"):
            # 有些错误信息可能不带 data: 前缀，直接打印出来看看
            if "error" in line.lower():
                 print(f"[API Error Line] {line}")
            continue

        payload = line[len("data:"):].strip()

        if payload == "[DONE]":
            break
        if not payload:
            continue

        try:
            obj = json.loads(payload)
            # 检查是否有错误码
            if obj.get("code") and obj.get("code") != 0:
                print(f"[API Error] Code: {obj.get('code')}, Message: {obj.get('message')}")
                return ""
                
            delta = obj["choices"][0].get("delta", {})
            content = delta.get("content", "")
        except Exception as e:
            # print(f"[Parse Error] {e}")
            continue

        if content:
            # print(content, end="", flush=True) # 在Web应用中不要直接打印到stdout，除非调试
            full_response += content

    return full_response


# =====================================================
# 4. 对话历史管理
# =====================================================
def add_message(history, role, content):
    history.append({"role": role, "content": content})
    return history


# =====================================================
# 5. 主程序入口
# =====================================================
def main():
    print("=== Golf 运动健康专家（星火 · UTF-8 不乱码版）===")
    print("直接粘贴你的指标内容（文本或 JSON），输入 exit 退出\n")

    chat_history = []
    chat_history = add_message(chat_history, "system", SYSTEM_PROMPT)

    while True:
        user_input = input("我: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("已退出。")
            break

        chat_history = add_message(chat_history, "user", user_input)
        print("星火:", end="")

        answer = spark_chat_stream(chat_history)
        chat_history = add_message(chat_history, "assistant", answer)

        print("\n")  # 换行分隔下一轮


if __name__ == "__main__":
    main()
