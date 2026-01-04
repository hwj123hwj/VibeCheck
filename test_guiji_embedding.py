import os
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_siliconflow_embedding():
    # 从 .env 获取配置
    api_key = os.getenv("GUIJI_API_KEY")
    api_url = os.getenv("GUIJI_EMB_URL", "https://api.siliconflow.cn/v1/embeddings")
    model = os.getenv("GUIJI_EMB_MODEL", "BAAI/bge-m3")

    if not api_key:
        print("❌ 错误: 未在 .env 中找到 GUIJI_API_KEY")
        return

    print(f"🚀 正在测试硅基流动 Embedding API...")
    print(f"📡 API 地址: {api_url}")
    print(f"🤖 使用模型: {model}")

    # 模拟我们要拼接的搜索元数据
    test_input = (
        "Tag: 黎明 燃烧 孤勇 征途 破晓。 "
        "Review: 这首歌如同一场灵魂的远征，在冷眼与嘲笑中点燃生命的火焰...。 "
        "Scene: 适合在清晨独自奔跑于空旷公路，或深夜伏案奋斗时聆听..."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "input": test_input,
        "encoding_format": "float"
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            # 获取向量数据（通常在 data[0]['embedding']）
            embedding = result['data'][0]['embedding']
            
            print("✅ API 调用成功!")
            print(f"📊 向量维度: {len(embedding)}")
            print(f"🔍 向量前 5 位: {embedding[:5]}")
            
            # 确认维度是否符合我们数据库预留的 1024 (bge-m3 默认是 1024)
            if len(embedding) == 1024:
                print("✨ 维度匹配 (1024)，可以直接存入数据库 review_vector 字段。")
            else:
                print(f"💡 提示: 向量维度为 {len(embedding)}，请确保数据库字段定义与其匹配。")
                
        else:
            print(f"❌ API 调用失败，状态码: {response.status_code}")
            print(f"💬 错误详情: {response.text}")

    except Exception as e:
        print(f"💥 发生异常: {str(e)}")

if __name__ == "__main__":
    test_siliconflow_embedding()
