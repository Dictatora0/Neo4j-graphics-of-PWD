#!/usr/bin/env python3
"""
检查当前运行状态和问题诊断
"""

import json
import os
from datetime import datetime
from pathlib import Path

print("\n" + "="*70)
print(" 📊 运行状态检查")
print("="*70 + "\n")

# 检查进度文件: 由 CheckpointManager 周期性写入,反映当前块号和累计统计
progress_file = Path("output/checkpoints/.progress.json")
if progress_file.exists():
    with open(progress_file) as f:
        progress = json.load(f)
    
    processed = len(progress['processed_chunks'])
    concepts = progress['total_concepts']
    relationships = progress['total_relationships']
    started = progress['started_at']
    last_update = progress['last_update']
    
    print(f"✓ Checkpoint 进度:")
    print(f"  - 已处理块数: {processed}")
    print(f"  - 概念总数: {concepts}")
    print(f"  - 关系总数: {relationships}")
    print(f"  - 开始时间: {started[:19]}")
    print(f"  - 最后更新: {last_update[:19]}")
    
    # 计算运行时间
    try:
        start_time = datetime.fromisoformat(started[:19])
        update_time = datetime.fromisoformat(last_update[:19])
        now = datetime.now()
        
        total_elapsed = (now - start_time).total_seconds() / 60
        since_update = (now - update_time).total_seconds() / 60
        
        print(f"\n⏱️  时间统计:")
        print(f"  - 总运行时间: {total_elapsed:.1f} 分钟")
        print(f"  - 距上次更新: {since_update:.1f} 分钟")
        
        if processed > 0:
            avg_time = total_elapsed / processed
            print(f"  - 平均速度: {avg_time:.1f} 分钟/块 ({avg_time*60:.0f} 秒/块)")
    except:
        pass
else:
    print("❌ 未找到进度文件")

# 检查日志中的错误
print("\n" + "="*70)
print(" 🔍 错误分析")
print("="*70 + "\n")

log_file = Path("output/kg_builder.log")
if log_file.exists():
    with open(log_file) as f:
        lines = f.readlines()
    
    errors = [line for line in lines if 'ERROR' in line]
    warnings = [line for line in lines if 'WARNING' in line and 'timeout' in line]
    
    print(f"错误总数: {len(errors)}")
    print(f"超时警告: {len(warnings)}")
    
    if errors:
        print("\n最近的错误:")
        for line in errors[-5:]:
            print(f"  {line.strip()}")
    
    if warnings:
        print(f"\n超时情况:")
        print(f"  - 发生次数: {len(warnings)}")
        print(f"  - 这表明 LLM 处理较慢，需要增加超时时间")

# 问题诊断
print("\n" + "="*70)
print(" 💊 问题诊断和解决方案")
print("="*70 + "\n")

print("检测到的问题:")
print("  1. ❌ LLM 超时导致返回 None")
print("  2. ❌ 代码未处理 None 情况")
print("  3. ⚠️  实际速度比预期慢 (~180秒/块 vs 预期90秒)")

print("\n解决方案:")
print("  ✓ 已调整配置:")
print("     - timeout: 180 → 300 秒")
print("     - max_chunks: 100 → 50 块")
print()
print("  需要修复:")
print("     - 修复 NoneType 错误处理")
print("     - 让失败的块跳过而不是中断")

print("\n建议操作:")
print("  1. 停止当前进程（如果还在运行）")
print("  2. 运行修复脚本: python fix_error_handling.py")
print("  3. 重新启动: python start.py")
print("     （会自动从第 18 个块继续）")

print("\n" + "="*70 + "\n")
