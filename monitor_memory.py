#!/usr/bin/env python3
"""
内存和CPU监控工具
实时监控系统资源使用情况，帮助诊断性能问题
"""

import psutil
import time
import os
from datetime import datetime

def get_process_memory():
    """获取当前进程的内存使用情况"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # 转换为MB

def get_system_memory():
    """获取系统内存使用情况"""
    mem = psutil.virtual_memory()
    return {
        'total': mem.total / 1024 / 1024 / 1024,  # GB
        'available': mem.available / 1024 / 1024 / 1024,  # GB
        'used': mem.used / 1024 / 1024 / 1024,  # GB
        'percent': mem.percent
    }

def get_cpu_usage():
    """获取CPU使用率"""
    return psutil.cpu_percent(interval=1)

def format_memory(mb):
    """格式化内存显示"""
    if mb > 1024:
        return f"{mb/1024:.2f} GB"
    return f"{mb:.2f} MB"

def monitor_continuous(interval=5):
    """持续监控系统资源"""
    print("\n" + "="*70)
    print("系统资源监控 - 按 Ctrl+C 停止")
    print("="*70)
    
    try:
        while True:
            # 获取系统信息
            sys_mem = get_system_memory()
            cpu_usage = get_cpu_usage()
            
            # 查找相关进程
            ollama_mem = 0
            python_mem = 0
            
            for proc in psutil.process_iter(['name', 'memory_info']):
                try:
                    pname = proc.info['name'].lower()
                    if 'ollama' in pname:
                        ollama_mem += proc.info['memory_info'].rss / 1024 / 1024
                    elif 'python' in pname:
                        python_mem += proc.info['memory_info'].rss / 1024 / 1024
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 清屏并显示
            os.system('clear' if os.name != 'nt' else 'cls')
            
            print(f"\n更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n" + "="*70)
            print("系统资源概览")
            print("="*70)
            
            # CPU
            print(f"\nCPU 使用率: {cpu_usage:.1f}%")
            cpu_bar = '#' * int(cpu_usage / 2)
            print(f"    [{cpu_bar:<50}]")
            
            # 内存
            print(f"\n系统内存:")
            print(f"    总计: {sys_mem['total']:.2f} GB")
            print(f"    已用: {sys_mem['used']:.2f} GB ({sys_mem['percent']:.1f}%)")
            print(f"    可用: {sys_mem['available']:.2f} GB")
            mem_bar = '#' * int(sys_mem['percent'] / 2)
            print(f"    [{mem_bar:<50}]")
            
            # 进程内存
            print(f"\n进程内存:")
            print(f"    Ollama: {format_memory(ollama_mem)}")
            print(f"    Python: {format_memory(python_mem)}")
            
            # 健康状态
            print(f"\n健康状态:")
            if sys_mem['percent'] > 90:
                print(f"    内存告急 ({sys_mem['percent']:.1f}%) - 建议停止处理")
            elif sys_mem['percent'] > 80:
                print(f"    内存紧张 ({sys_mem['percent']:.1f}%) - 密切关注")
            elif sys_mem['percent'] > 70:
                print(f"    内存偏高 ({sys_mem['percent']:.1f}%) - 正常范围")
            else:
                print(f"    内存健康 ({sys_mem['percent']:.1f}%)")
            
            if cpu_usage > 90:
                print(f"    CPU 过载 ({cpu_usage:.1f}%)")
            elif cpu_usage > 70:
                print(f"    CPU 繁忙 ({cpu_usage:.1f}%)")
            else:
                print(f"    CPU 正常 ({cpu_usage:.1f}%)")
            
            print("\n" + "="*70)
            print(f"刷新间隔: {interval}秒 | 按 Ctrl+C 停止监控")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n监控已停止")

def monitor_once():
    """单次检查系统资源"""
    sys_mem = get_system_memory()
    cpu_usage = get_cpu_usage()
    
    print("\n" + "="*70)
    print("系统资源快照")
    print("="*70)
    print(f"\nCPU 使用率: {cpu_usage:.1f}%")
    print(f"内存使用率: {sys_mem['percent']:.1f}%")
    print(f"可用内存: {sys_mem['available']:.2f} GB / {sys_mem['total']:.2f} GB")
    
    if sys_mem['percent'] > 85:
        print("\n警告: 内存使用率过高，建议:")
        print("  1. 降低配置文件中的 max_chunks 值")
        print("  2. 减少 parallel_workers 数量")
        print("  3. 重启 Ollama 服务释放内存")
        print("  4. 考虑使用更小的模型（如 7B 替代 14B）")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        monitor_once()
    else:
        monitor_continuous(interval=5)
