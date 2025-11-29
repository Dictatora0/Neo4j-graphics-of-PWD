#!/usr/bin/env python3
"""
快速启动脚本（无需交互确认）
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_pipeline import (
    print_banner, 
    check_environment, 
    show_config_info,
    estimate_time,
    run_with_monitoring
)


def main():
    """主函数 - 无需确认直接运行"""
    
    # 打印横幅
    print_banner()
    
    # 环境检查
    env_ok, has_model, model_name = check_environment()
    
    if not env_ok:
        print("\n环境检查发现问题，请先解决上述问题再运行\n")
        print("解决方法:")
        print("  • Ollama 未运行: ollama serve")
        print("  • 模型未安装: ollama pull qwen2.5-coder:7b")
        print("  • 依赖缺失: pip install -r requirements.txt")
        print()
        sys.exit(1)
    
    # 显示配置
    show_config_info()
    
    # 时间估算
    estimate_time()
    
    # 显示监控提示
    print("="*70)
    print(" 提示")
    print("="*70)
    print("""
- 在另一个终端运行监控: bash monitor.sh
- 实时查看日志: tail -f output/kg_builder.log  
- 按 Ctrl+C 可安全退出并保存进度
""")
    print("="*70)
    
    # 直接开始运行
    success = run_with_monitoring()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
