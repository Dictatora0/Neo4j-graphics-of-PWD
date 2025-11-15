#!/usr/bin/env python3
"""
测试JSON解析修复
"""
import json

# 模拟LLM返回的markdown格式
test_responses = [
    # 格式1: 带```json标记
    '''```json
{
  "concepts": [
    {"entity": "松材线虫病", "importance": 5, "category": "疾病"}
  ]
}
```''',
    
    # 格式2: 只有```
    '''```
{
  "concepts": [
    {"entity": "松材线虫", "importance": 4, "category": "病原体"}
  ]
}
```''',
    
    # 格式3: 纯JSON
    '''{
  "concepts": [
    {"entity": "马尾松", "importance": 3, "category": "寄主"}
  ]
}''',
]

def clean_response(response):
    """清理markdown代码块"""
    response = response.strip()
    if response.startswith('```json'):
        response = response[7:].strip()
    elif response.startswith('```'):
        response = response[3:].strip()
    if response.endswith('```'):
        response = response[:-3].strip()
    response = response.strip('`').strip()
    return response

print("测试JSON解析修复\n" + "="*50)
for i, resp in enumerate(test_responses, 1):
    print(f"\n测试 {i}:")
    print(f"原始响应:\n{resp[:100]}...")
    
    cleaned = clean_response(resp)
    print(f"\n清理后:\n{cleaned[:100]}...")
    
    try:
        data = json.loads(cleaned)
        print(f"✅ 解析成功: {data}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")

print("\n" + "="*50)
print("✓ 测试完成")
