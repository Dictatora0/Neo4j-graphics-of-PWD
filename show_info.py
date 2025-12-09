#!/usr/bin/env python3
"""
显示运行信息（不实际运行管道）
用于快速查看配置和环境状态
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_pipeline import (
    print_banner,
    check_environment,
    show_config_info,
    estimate_time,
    show_progress_tips
)


def main():
    """只显示信息，不运行"""
    
    print_banner()
    
    # 环境检查
    env_ok, has_model, model_name = check_environment()
    
    # 显示配置
    show_config_info()
    
    # 时间估算
    estimate_time()
    
    # 进度监控提示
    show_progress_tips()
    
    # 启动建议
    print("="*70)
    print("准备启动")
    print("="*70)
    print("""
选择启动方式:

1. 完整运行（交互式，需要按 Enter 确认）:
   python run_pipeline.py

2. 快速启动（跳过确认，直接运行）:
   python start.py

3. 直接运行（最简单）:
   python enhanced_pipeline_safe.py

4. 快速测试（15个块，约23分钟）:
   python test_safe_with_bge.py --clear
""")
    print("="*70)
    
    if not env_ok:
        print("\n[警告] 请先解决环境问题再运行\n")
        sys.exit(1)
    else:
        print("\n[提示] 环境就绪，可以开始运行了。\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
