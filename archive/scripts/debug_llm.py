#!/usr/bin/env python3
"""测试LLM输出格式"""

import requests
import json

def test_llm_output():
    """测试LLM的实际输出"""
    
    test_text = """
    松材线虫病是由松材线虫引起的松树病害。
    松褐天牛是主要传播媒介。
    马尾松和黑松是主要寄主植物。
    """
    
    system_prompt = """你是松材线虫病知识图谱构建专家。从文本中提取具体的领域概念。

重点关注:
- 病原体: 松材线虫、伴生细菌、线虫种类
- 寄主植物: 松树、马尾松、黑松、湿地松
- 媒介昆虫: 松褐天牛、云杉花墨天牛
- 病害症状: 萎蔫、枯死、变色、针叶脱落
- 防治措施: 药剂、诱捕器、生物防治
- 环境因子: 温度、湿度、海拔、气候
- 地理位置: 疫区、分布区、省份

类别: pathogen, host, vector, symptom, treatment, environment, location, mechanism, compound

避免: 过于通用的词(因素、过程、机制、方法)
必须严格返回JSON数组格式，不要添加任何解释文字。"""
    
    user_prompt = f"""从以下文本提取松材线虫病相关概念:
{test_text}

严格按照以下JSON格式返回，不要添加markdown标记或其他文字:
[{{"entity": "概念名", "importance": 3, "category": "pathogen"}}, ...]"""
    
    payload = {
        "model": "llama3.2:3b",
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "temperature": 0.1,
        "top_p": 0.9,
        "top_k": 40,
        "num_ctx": 2048,
        "num_predict": 512,
    }
    
    print("发送请求到Ollama...")
    response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        llm_output = result.get('response', '').strip()
        
        print("\n" + "="*60)
        print("LLM原始输出:")
        print("="*60)
        print(llm_output)
        print("="*60)
        
        # 尝试解析
        try:
            # 清理
            output_clean = llm_output
            if output_clean.startswith('```'):
                lines = output_clean.split('\n')
                output_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else output_clean
            
            if output_clean.startswith('json'):
                output_clean = output_clean[4:].strip()
            
            import re
            json_match = re.search(r'\[.*?\]', output_clean, re.DOTALL)
            if json_match:
                output_clean = json_match.group(0)
            
            output_clean = output_clean.replace("'", '"')
            
            print("\n清理后的JSON:")
            print(output_clean)
            
            data = json.loads(output_clean)
            print("\n✓ JSON解析成功!")
            print(f"提取到 {len(data)} 个概念:")
            for item in data:
                print(f"  - {item}")
                
        except json.JSONDecodeError as e:
            print(f"\n✗ JSON解析失败: {e}")
            print(f"错误位置: {e.pos}")
            if e.pos < len(output_clean):
                print(f"错误附近: ...{output_clean[max(0,e.pos-20):e.pos+20]}...")
    else:
        print(f"请求失败: {response.status_code}")

if __name__ == "__main__":
    test_llm_output()
