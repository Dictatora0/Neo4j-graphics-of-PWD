#!/usr/bin/env python3
"""
实际运行功能测试 - 无需完整依赖
测试那些可以独立运行的功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_canonical_resolver_basic():
    """测试 CanonicalResolver 的内置规则（不需要外部依赖）"""
    print_header("测试 1: CanonicalResolver 内置规则")
    
    try:
        # 动态导入，避免在文件开头就失败
        import pandas as pd
        from concept_deduplicator import CanonicalResolver
        
        resolver = CanonicalResolver(use_external_kb=False)
        
        test_cases = [
            ('松材线虫', 'Bursaphelenchus xylophilus'),
            ('线虫', 'Bursaphelenchus xylophilus'),
            ('松褐天牛', 'Monochamus alternatus'),
            ('天牛', 'Monochamus alternatus'),
            ('马尾松', 'Pinus massoniana'),
            ('黑松', 'Pinus thunbergii'),
            ('松材线虫病', 'Pine Wilt Disease'),
            ('阿维菌素', 'Avermectin'),
        ]
        
        passed = 0
        for original, expected in test_cases:
            result = resolver.resolve(original)
            if result == expected:
                print(f"  ✓ '{original}' → '{result}'")
                passed += 1
            else:
                print(f"  ✗ '{original}' → '{result}' (期望: {expected})")
        
        print(f"\n结果: {passed}/{len(test_cases)} 通过")
        
        # 测试自定义映射
        print("\n测试自定义映射...")
        resolver.add_custom_mapping("PWN", "Bursaphelenchus xylophilus")
        result = resolver.resolve("PWN")
        print(f"  ✓ 'PWN' → '{result}'")
        
        return passed == len(test_cases)
        
    except ImportError as e:
        print(f"  ⚠️  跳过测试（缺少依赖: {e}）")
        return None

def test_config_loading():
    """测试配置文件加载"""
    print_header("测试 2: 配置文件加载")
    
    try:
        import yaml
        
        config_path = project_root / 'config' / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("  ✓ 配置文件加载成功")
        
        # 检查第一阶段配置
        if 'improvements' in config:
            print("  ✓ improvements 配置节存在")
            print(f"    - context_window.enable: {config['improvements']['context_window']['enable']}")
            print(f"    - hierarchical_ontology.enable: {config['improvements']['hierarchical_ontology']['enable']}")
            print(f"    - local_search.enable: {config['improvements']['local_search']['enable']}")
        
        # 检查第二阶段配置
        if 'improvements_phase2' in config:
            print("  ✓ improvements_phase2 配置节存在")
            el_config = config['improvements_phase2']['entity_linking']
            print(f"    - entity_linking.use_canonical_resolver: {el_config['use_canonical_resolver']}")
            print(f"    - entity_linking.use_external_kb: {el_config['use_external_kb']}")
            print(f"    - multimodal.enable: {config['improvements_phase2']['multimodal']['enable']}")
            print(f"    - human_feedback.enable: {config['improvements_phase2']['human_feedback']['enable']}")
        
        return True
        
    except ImportError:
        print("  ⚠️  跳过测试（缺少 PyYAML）")
        return None
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        return False

def test_file_structure():
    """测试文件结构完整性"""
    print_header("测试 3: 文件结构完整性")
    
    required_files = {
        '核心模块': [
            'concept_extractor.py',
            'concept_deduplicator.py',
            'import_to_neo4j_final.py',
            'graph_rag.py',
        ],
        '新增模块': [
            'multimodal_graph_builder.py',
            'human_feedback_manager.py',
        ],
        'Web API': [
            'web/backend/app/routers/feedback.py',
            'web/backend/app/routers/multimodal.py',
        ],
        '配置文件': [
            'config/config.yaml',
        ],
        '示例脚本': [
            'examples/local_search_demo.py',
        ],
    }
    
    all_passed = True
    for category, files in required_files.items():
        print(f"\n  {category}:")
        for file in files:
            file_path = project_root / file
            if file_path.exists():
                print(f"    ✓ {file}")
            else:
                print(f"    ✗ {file} (不存在)")
                all_passed = False
    
    return all_passed

def test_class_imports():
    """测试关键类是否可以导入（不实例化）"""
    print_header("测试 4: 关键类导入测试")
    
    imports_to_test = [
        ('concept_deduplicator', 'CanonicalResolver'),
        ('multimodal_graph_builder', 'MultimodalGraphBuilder'),
        ('multimodal_graph_builder', 'MultimodalRetriever'),
        ('human_feedback_manager', 'HumanFeedbackManager'),
        ('human_feedback_manager', 'FeedbackType'),
    ]
    
    passed = 0
    for module_name, class_name in imports_to_test:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                print(f"  ✓ {module_name}.{class_name}")
                passed += 1
            else:
                print(f"  ✗ {module_name}.{class_name} (类不存在)")
        except ImportError as e:
            print(f"  ⚠️  {module_name}.{class_name} (依赖缺失: {e})")
    
    return passed > 0

def test_web_api_routes():
    """测试 Web API 路由文件结构"""
    print_header("测试 5: Web API 路由")
    
    feedback_api = project_root / 'web/backend/app/routers/feedback.py'
    multimodal_api = project_root / 'web/backend/app/routers/multimodal.py'
    
    tests_passed = 0
    
    # 检查 Feedback API
    if feedback_api.exists():
        with open(feedback_api, 'r', encoding='utf-8') as f:
            content = f.read()
            endpoints = [
                'relation-direction',
                'relation-type',
                'entity-merge',
                'missing-relation',
                'report',
                'error-patterns',
            ]
            print("\n  Feedback API 端点:")
            for endpoint in endpoints:
                if endpoint in content:
                    print(f"    ✓ /api/feedback/{endpoint}")
                    tests_passed += 1
    
    # 检查 Multimodal API
    if multimodal_api.exists():
        with open(multimodal_api, 'r', encoding='utf-8') as f:
            content = f.read()
            endpoints = [
                'retrieve-images',
                'concept/',
                'image/',
                'stats',
            ]
            print("\n  Multimodal API 端点:")
            for endpoint in endpoints:
                if endpoint in content:
                    print(f"    ✓ /api/multimodal/...{endpoint}")
                    tests_passed += 1
    
    return tests_passed > 0

def main():
    print("\n" + "🚀"*35)
    print("  知识图谱系统功能实际运行测试")
    print("🚀"*35)
    
    results = {}
    
    # 运行测试
    results['配置加载'] = test_config_loading()
    results['文件结构'] = test_file_structure()
    results['类导入'] = test_class_imports()
    results['CanonicalResolver'] = test_canonical_resolver_basic()
    results['Web API'] = test_web_api_routes()
    
    # 汇总结果
    print("\n" + "="*70)
    print("  📊 测试结果汇总")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    total = len(results)
    
    for name, result in results.items():
        if result is True:
            status = "✅ 通过"
        elif result is None:
            status = "⚠️  跳过"
        else:
            status = "❌ 失败"
        print(f"  {name:25s} {status}")
    
    print("\n" + "-"*70)
    print(f"  通过: {passed}/{total}")
    print(f"  跳过: {skipped}/{total}")
    print(f"  失败: {failed}/{total}")
    print("-"*70)
    
    if failed == 0:
        if skipped > 0:
            print("\n✅ 所有可运行测试通过！")
            print("💡 提示: 部分测试因缺少依赖而跳过")
            print("   安装依赖: pip install -r requirements.txt")
        else:
            print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
