#!/usr/bin/env python3
"""
知识图谱构建启动脚本
提供详细的运行信息、进度监控和环境检查
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from enhanced_pipeline_safe import run_safe_pipeline


def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        松材线虫病知识图谱构建系统                                        ║
║        Pine Wilt Disease Knowledge Graph Builder                    ║
║                                                                      ║
║        特性: LLM 抽取 | BGE-M3 去重 | 断点续传 | 安全保护               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_environment():
    """环境检查"""
    print("\n" + "="*70)
    print(" 环境检查")
    print("="*70)
    
    checks = []
    # 统一收集 Python 版本、Ollama、模型和依赖库状态,最后整体给出诊断结果
    
    # 检查 Python 版本
    py_version = sys.version.split()[0]
    checks.append(("Python 版本", py_version, True))
    
    # 检查 Ollama 服务: 使用 curl 探针而不是 Python SDK,降低依赖复杂度
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=3
        )
        ollama_ok = result.returncode == 0
        checks.append(("Ollama 服务", "运行中" if ollama_ok else "未运行", ollama_ok))
    except Exception as e:
        checks.append(("Ollama 服务", f"检查失败: {e}", False))
        ollama_ok = False
    
    # 检查模型
    config = load_config()
    model_name = config['llm']['model']
    
    if ollama_ok:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True
            )
            has_model = model_name in result.stdout
            checks.append(("LLM 模型", model_name if has_model else f"{model_name} (未安装)", has_model))
        except:
            checks.append(("LLM 模型", "检查失败", False))
            has_model = False
    else:
        checks.append(("LLM 模型", "无法检查", False))
        has_model = False
    
    # 检查依赖库
    # 关键依赖库检查: 提前发现缺失,避免管道中途才因为 ImportError 中断
    deps = [
        ("torch", "PyTorch"),
        ("sentence_transformers", "SentenceTransformers"),
        ("pandas", "Pandas"),
        ("tqdm", "tqdm"),
    ]
    
    for module, name in deps:
        try:
            __import__(module)
            checks.append((f"{name} 库", "已安装", True))
        except ImportError:
            checks.append((f"{name} 库", "未安装", False))
    
    # 检查 PyTorch 版本
    try:
        import torch
        torch_version = torch.__version__
        mps_available = torch.backends.mps.is_available()
        checks.append(("PyTorch 版本", torch_version, True))
        checks.append(("Apple GPU (MPS)", "可用" if mps_available else "不可用", mps_available))
    except:
        checks.append(("PyTorch", "未安装", False))
    
    # 检查输入文件: 直接统计待处理 PDF 数量,给出是否“有活可干”的直观提示
    pdf_dir = config.get('pdf.input_directory', './文献')
    pdf_files = list(Path(pdf_dir).glob("*.pdf")) if os.path.exists(pdf_dir) else []
    checks.append(("PDF 文件", f"{len(pdf_files)} 个", len(pdf_files) > 0))
    
    # 打印检查结果
    all_ok = True
    for name, status, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {name:<20} {status}")
        if not ok:
            all_ok = False
    
    print()
    return all_ok, has_model, model_name


def show_config_info():
    """显示配置信息"""
    print("="*70)
    print(" 运行配置")
    print("="*70)
    
    config = load_config()
    
    # LLM 配置
    print("\nLLM 配置:")
    print(f"  • 模型: {config['llm']['model']}")
    print(f"  • 主机: {config['llm']['ollama_host']}")
    print(f"  • 处理块数: {config['llm'].get('max_chunks', 'ALL')}")
    print(f"  • 超时时间: {config['llm']['timeout']} 秒")
    print(f"  • 上下文窗口: {config['llm']['num_ctx']}")
    print(f"  • 温度: {config['llm']['temperature']}")
    
    # 去重配置
    print("\n去重配置:")
    use_bge = config['deduplication']['use_bge_m3']
    print(f"  • 引擎: {'BGE-M3 (混合检索)' if use_bge else 'MiniLM'}")
    # 当启用 BGE-M3 时,额外展示具体模型和 dense/sparse 混合权重,方便调参
    if use_bge:
        print(f"  • 模型: {config['deduplication']['embedding_model']}")
        print(f"  • 混合权重: {config['deduplication']['hybrid_alpha']}")
    print(f"  • 相似度阈值: {config['deduplication']['similarity_threshold']}")
    
    # 过滤配置
    print("\n过滤配置:")
    print(f"  • 最小重要性: {config['filtering']['min_importance']}")
    print(f"  • 最小连接数: {config['filtering']['min_connections']}")
    
    # 输入输出
    print("\n文件配置:")
    print(f"  • 输入目录: {config['pdf']['input_directory']}")
    print(f"  • 输出目录: {config['output']['base_directory']}")
    
    # 安全特性
    print("\n安全特性:")
    print(f"  • Checkpoint 间隔: 10 个块")
    print(f"  • 断点续传: 启用")
    print(f"  • 异常保护: 启用")
    print(f"  • 进度保存: output/checkpoints/")
    
    print()


def estimate_time():
    """估算运行时间"""
    print("="*70)
    print(" 时间估算")
    print("="*70)
    
    config = load_config()
    max_chunks = config['llm'].get('max_chunks', 100)
    
    # 读取测试结果估算: 基于历史实验给出一个粗略人类可读的时间预估
    time_per_chunk = 92  # 7B 模型约 92 秒/块
    
    total_seconds = time_per_chunk * max_chunks if max_chunks else time_per_chunk * 100
    total_minutes = total_seconds / 60
    total_hours = total_minutes / 60
    
    print(f"\n基于 {config['llm']['model']} 模型估算:")
    print(f"  • 单块耗时: ~{time_per_chunk} 秒")
    
    if max_chunks:
        print(f"  • 处理块数: {max_chunks} 个")
        print(f"  • 预计总耗时: {total_minutes:.1f} 分钟 ({total_hours:.1f} 小时)")
    else:
        print(f"  • 处理块数: ALL（取决于 PDF 数量）")
        print(f"  • 预计耗时: ~{total_minutes:.1f} 分钟（100块）")
    
    # 阶段时间分布
    print(f"\n各阶段时间分布:")
    print(f"  • PDF 提取: ~2-3 分钟")
    print(f"  • 文本分块: <1 分钟")
    print(f"  • LLM 抽取: ~{total_minutes*0.9:.1f} 分钟 (主要耗时)")
    print(f"  • 去重过滤: ~1-2 分钟")
    print(f"  • 保存结果: <1 分钟")
    
    print()


def show_progress_tips():
    """显示进度查看提示"""
    print("="*70)
    print(" 进度监控")
    print("="*70)
    
    print("""
在另一个终端窗口中，可以使用以下命令监控进度:

1. 实时查看日志:
   tail -f output/kg_builder.log

2. 查看 checkpoint 进度:
   cat output/checkpoints/.progress.json

3. 查看已保存的文件:
   ls -lh output/checkpoints/

4. 查看系统资源使用:
   top | grep python

提示:
  - 每 10 个块会看到 "Checkpoint: X/Y chunks processed"
  - 可随时按 Ctrl+C 安全退出(会自动保存进度)
  - 重新运行会自动从断点继续
    """)
    print("="*70)


def run_with_monitoring():
    """运行管道并监控"""
    print("\n" + "="*70)
    print(" 启动知识图谱构建")
    print("="*70)
    
    start_time = datetime.now()
    print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n正在运行...")
    print("提示: 按 Ctrl+C 可安全退出并保存进度\n")
    print("-"*70 + "\n")
    
    try:
        # 运行管道: 启用 resume 模式,在已有 checkpoint 基础上继续,默认不清空历史进度
        concepts_df, relationships_df = run_safe_pipeline(
            resume=True,
            clear_checkpoint=False
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # 显示结果
        print("\n" + "="*70)
        print(" 构建完成")
        print("="*70)
        
        print(f"\n结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration}")
        
        print(f"\n结果统计:")
        print(f"  • 概念总数: {len(concepts_df)}")
        print(f"  • 关系总数: {len(relationships_df)}")
        
        if not concepts_df.empty:
            print(f"\nTOP 10 重要概念:")
            top_concepts = concepts_df.nlargest(10, 'importance')
            for idx, (_, row) in enumerate(top_concepts.iterrows(), 1):
                print(f"  {idx:2d}. {row['entity']:<30} (重要性: {row.get('importance', 0):.1f})")
        
        if not relationships_df.empty:
            print(f"\nTOP 5 高权重关系:")
            top_rels = relationships_df.nlargest(5, 'weight')
            for idx, (_, row) in enumerate(top_rels.iterrows(), 1):
                print(f"  {idx}. {row['node_1']} --[{row['edge']}]-> {row['node_2']} ({row['weight']:.2f})")
        
        # 输出文件
        print(f"\n输出文件:")
        print(f"  • 概念文件: output/concepts.csv")
        print(f"  • 关系文件: output/relationships.csv")
        print(f"  • 日志文件: output/kg_builder.log")
        print(f"  • Checkpoint: output/checkpoints/")
        
        print("\n" + "="*70)
        print(" 知识图谱构建成功")
        print("="*70 + "\n")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print(" 用户中断")
        print("="*70)
        print("\n进度已自动保存到: output/checkpoints/")
        print("\n要继续处理，请重新运行此脚本")
        print("\n" + "="*70 + "\n")
        return False
        
    except Exception as e:
        print("\n\n" + "="*70)
        print(f" 发生错误")
        print("="*70)
        print(f"\n错误信息: {e}")
        print("\n已处理的数据已保存(如果有)")
        print("\n查看详细日志: output/kg_builder.log")
        print("\n" + "="*70 + "\n")
        
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 打印横幅
    print_banner()
    
    # 环境检查
    env_ok, has_model, model_name = check_environment()
    
    if not env_ok:
        print("环境检查发现问题，请先解决上述问题再运行")
        
        # 提供解决建议
        print("\n" + "="*70)
        print(" 解决建议")
        print("="*70)
        print("""
如果 Ollama 服务未运行:
  ollama serve

如果模型未安装:
  ollama pull qwen2.5-coder:7b

如果依赖库缺失:
  pip install -r requirements.txt
        """)
        print("="*70 + "\n")
        sys.exit(1)
    
    # 显示配置
    show_config_info()
    
    # 时间估算
    estimate_time()
    
    # 进度监控提示
    show_progress_tips()
    
    # 确认开始
    print("\n" + "="*70)
    print(" 准备就绪")
    print("="*70)
    print("\n按 Enter 开始运行，或按 Ctrl+C 取消...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n已取消\n")
        sys.exit(0)
    
    # 运行管道
    success = run_with_monitoring()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
