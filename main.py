#!/usr/bin/env python3
"""
松材线虫病知识图谱构建系统 - 主程序
从PDF文献中提取知识，构建Neo4j知识图谱
"""

import os
import sys
from datetime import datetime

from pdf_extractor import PDFExtractor
from entity_recognizer import EntityRecognizer
from relation_extractor import RelationExtractor
from data_cleaner import DataCleaner
from neo4j_generator import Neo4jGenerator
from config_loader import load_config
from logger_config import get_logger
from incremental_updater import IncrementalUpdater
from entity_linker import EntityLinker

# 初始化日志器
logger = get_logger('Main')


def print_banner():
    """打印程序横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        松材线虫病知识图谱构建系统v1.1                      ║
║        Pine Wilt Disease Knowledge Graph Builder             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_step(step_num: int, total_steps: int, title: str):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}/{total_steps}: {title}")
    print(f"{'='*60}\n")


def main():
    """主函数"""
    print_banner()
    
    # 加载配置
    logger.info("加载配置文件...")
    config = load_config()
    
    # 获取配置参数
    PDF_DIR = config.get('pdf.input_directory', './文献')
    OUTPUT_DIR = config.get('output.base_directory', './output')
    CONFIDENCE_THRESHOLD = config.get('cleaning.confidence_threshold', 0.65)
    USE_CACHE = config.get('system.enable_cache', True)
    ENABLE_PARALLEL = config.get('system.enable_parallel', True)
    ENABLE_INCREMENTAL = config.get('system.enable_incremental', False)
    ENABLE_ENTITY_LINKING = config.get('cleaning.enable_entity_linking', False)
    ENABLE_OCR = config.get('pdf.enable_ocr', False)
    OCR_ENGINE = config.get('pdf.ocr_engine', 'tesseract')
    
    logger.info(f"PDF目录: {PDF_DIR}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info(f"置信度阈值: {CONFIDENCE_THRESHOLD}")
    logger.info(f"缓存状态: {'启用' if USE_CACHE else '禁用'}")
    logger.info(f"并行处理: {'启用' if ENABLE_PARALLEL else '禁用'}")
    logger.info(f"增量更新: {'启用' if ENABLE_INCREMENTAL else '禁用'}")
    logger.info(f"实体链接: {'启用' if ENABLE_ENTITY_LINKING else '禁用'}")
    logger.info(f"OCR支持: {'启用 (' + OCR_ENGINE + ')' if ENABLE_OCR else '禁用'}")
    
    # 检查PDF目录
    if not os.path.exists(PDF_DIR):
        logger.error(f"找不到PDF目录: {PDF_DIR}")
        print(f"错误: 找不到PDF目录: {PDF_DIR}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    start_time = datetime.now()
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # ========== 增量更新检查 ==========
        updater = None
        if ENABLE_INCREMENTAL:
            print_step(1, 7, "增量更新检查")
            logger.info("检查新增文件...")
            
            updater = IncrementalUpdater(OUTPUT_DIR)
            new_files = updater.get_new_files(PDF_DIR)
            
            if not new_files:
                print("✓ 没有新增文件，跳过处理")
                logger.info("没有新增文件")
                return
            
            print(f"发现 {len(new_files)} 个新增文件:")
            for f in new_files:
                print(f"  - {f}")
            
            # 备份现有结果
            if os.path.exists(f"{OUTPUT_DIR}/entities_clean.csv"):
                backup_dir = updater.backup_current_results()
                if backup_dir:
                    print(f"已备份现有结果到: {backup_dir}")
        
        # ========== 步骤 1: PDF文本提取 ==========
        step_offset = 1 if ENABLE_INCREMENTAL else 0
        print_step(1 + step_offset, 7 if ENABLE_INCREMENTAL else 6, "PDF文本提取")
        logger.info("开始PDF文本提取")
        
        extractor = PDFExtractor(
            use_cache=USE_CACHE, 
            enable_parallel=ENABLE_PARALLEL,
            enable_ocr=ENABLE_OCR,
            ocr_engine=OCR_ENGINE
        )
        pdf_texts = extractor.extract_from_directory(PDF_DIR)
        
        if not pdf_texts:
            print("错误: 没有成功提取任何PDF文本")
            sys.exit(1)
        
        extractor.save_extracted_texts(pdf_texts, f"{OUTPUT_DIR}/extracted_texts")
        
        # ========== 步骤 2: 实体识别 ==========
        print_step(2 + step_offset, 7 if ENABLE_INCREMENTAL else 6, "实体识别（NER）")
        logger.info("开始实体识别")
        
        recognizer = EntityRecognizer()
        entities_df = recognizer.extract_all_entities(pdf_texts)
        
        # 保存原始实体
        entities_df.to_csv(f"{OUTPUT_DIR}/entities.csv", index=False, encoding='utf-8-sig')
        print(f"\n✓ 原始实体数据已保存: {OUTPUT_DIR}/entities.csv")
        
        # ========== 步骤 3: 关系抽取 ==========
        print_step(3 + step_offset, 7 if ENABLE_INCREMENTAL else 6, "关系抽取")
        logger.info("开始关系抽取")
        
        extractor_rel = RelationExtractor()
        relations_df = extractor_rel.extract_all_relations(pdf_texts, entities_df)
        
        # 保存原始关系
        relations_df.to_csv(f"{OUTPUT_DIR}/relations.csv", index=False, encoding='utf-8-sig')
        print(f"\n✓ 原始关系数据已保存: {OUTPUT_DIR}/relations.csv")
        
        # ========== 步骤 4: 数据清洗 ==========
        print_step(4 + step_offset, 7 if ENABLE_INCREMENTAL else 6, "数据清洗和规范化")
        logger.info("开始数据清洗")
        
        cleaner = DataCleaner(confidence_threshold=CONFIDENCE_THRESHOLD)
        
        entities_clean = cleaner.clean_entities(entities_df)
        relations_clean = cleaner.clean_relations(relations_df, entities_clean)
        
        # ========== 实体链接与消歧（可选）==========
        if ENABLE_ENTITY_LINKING:
            print_step(5 + step_offset, 8 if ENABLE_INCREMENTAL else 7, "实体链接与消歧")
            logger.info("开始实体链接")
            
            linker = EntityLinker()
            entities_clean, relations_clean = linker.link_entities(
                entities_clean,
                relations_clean,
                enable_normalization=True,
                enable_clustering=True,
                enable_importance=True
            )
            
            print("✓ 实体链接完成")
        
        # ========== 增量更新合并（如果启用）==========
        if ENABLE_INCREMENTAL and updater:
            logger.info("合并增量数据...")
            
            # 加载旧数据
            old_entities_path = f"{OUTPUT_DIR}/entities_clean.csv"
            old_relations_path = f"{OUTPUT_DIR}/relations_clean.csv"
            
            if os.path.exists(old_entities_path):
                import pandas as pd
                old_entities = pd.read_csv(old_entities_path, encoding='utf-8-sig')
                old_relations = pd.read_csv(old_relations_path, encoding='utf-8-sig')
                
                # 合并数据
                entities_clean = updater.merge_entities(old_entities, entities_clean)
                relations_clean = updater.merge_relations(old_relations, relations_clean)
                
                print("✓ 已合并增量数据")
            
            # 标记文件为已处理
            processed_files = list(pdf_texts.keys())
            updater.mark_batch_as_processed(processed_files)
        
        # 保存清洗后的数据
        entities_clean.to_csv(f"{OUTPUT_DIR}/entities_clean.csv", index=False, encoding='utf-8-sig')
        relations_clean.to_csv(f"{OUTPUT_DIR}/relations_clean.csv", index=False, encoding='utf-8-sig')
        
        print("\n✓ 清洗后的数据已保存:")
        print(f"  - {OUTPUT_DIR}/entities_clean.csv")
        print(f"  - {OUTPUT_DIR}/relations_clean.csv")
        
        # ========== 步骤 5/6: 生成Neo4j导入文件 ==========
        total_steps = 7 if ENABLE_INCREMENTAL else 6
        if ENABLE_ENTITY_LINKING:
            total_steps += 1
        neo4j_step = total_steps - 1
        
        print_step(neo4j_step, total_steps, "生成Neo4j导入文件")
        logger.info("开始生成Neo4j导入文件")
        
        generator = Neo4jGenerator(output_dir=f"{OUTPUT_DIR}/neo4j_import")
        generator.generate_all(entities_clean, relations_clean)
        
        # ========== 步骤 6/7: 生成统计报告 ==========
        print_step(total_steps, total_steps, "生成统计报告")
        logger.info("开始生成统计报告")
        
        generate_statistics_report(entities_clean, relations_clean, OUTPUT_DIR)
        
        # ========== 完成 ==========
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"知识图谱构建完成，总耗时: {duration}")
        
        print("\n" + "="*60)
        print("✓ 知识图谱构建完成！")
        print("="*60)
        print(f"\n结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration}")
        print(f"\n输出目录: {os.path.abspath(OUTPUT_DIR)}")
        
        print("\n生成的文件:")
        print(f"  1. {OUTPUT_DIR}/entities.csv - 原始实体数据")
        print(f"  2. {OUTPUT_DIR}/relations.csv - 原始关系数据")
        print(f"  3. {OUTPUT_DIR}/entities_clean.csv - 清洗后的实体数据")
        print(f"  4. {OUTPUT_DIR}/relations_clean.csv - 清洗后的关系数据")
        print(f"  5. {OUTPUT_DIR}/neo4j_import/nodes.csv - Neo4j节点文件")
        print(f"  6. {OUTPUT_DIR}/neo4j_import/relations.csv - Neo4j关系文件")
        print(f"  7. {OUTPUT_DIR}/neo4j_import/import.cypher - Neo4j导入脚本")
        print(f"  8. {OUTPUT_DIR}/statistics_report.txt - 统计报告")
        
        print("\n后续步骤:")
        print("  1. 将 nodes.csv 和 relations.csv 复制到 Neo4j 的 import 目录")
        print("  2. 在 Neo4j Browser 中执行 import.cypher 脚本")
        print("  3. 或运行: python ./output/neo4j_import/import_to_neo4j.py")
        
        print("\n示例查询:")
        print("  MATCH (d:Disease)-[r:hasPathogen]->(p:Pathogen)")
        print("  RETURN d.name, p.name;")
        
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
        print("\n\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}", exc_info=True)
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def generate_statistics_report(entities_df, relations_df, output_dir):
    """生成统计报告"""
    report_path = f"{output_dir}/statistics_report.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("松材线虫病知识图谱统计报告\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 实体统计
        f.write("一、实体统计\n")
        f.write("-"*60 + "\n")
        f.write(f"实体总数: {len(entities_df)}\n\n")
        
        f.write("实体类型分布:\n")
        for entity_type, count in entities_df['type'].value_counts().items():
            percentage = count / len(entities_df) * 100
            f.write(f"  - {entity_type}: {count} ({percentage:.1f}%)\n")
        
        # 关系统计
        f.write("\n二、关系统计\n")
        f.write("-"*60 + "\n")
        f.write(f"关系总数: {len(relations_df)}\n\n")
        
        f.write("关系类型分布:\n")
        for relation_type, count in relations_df['relation'].value_counts().items():
            percentage = count / len(relations_df) * 100
            f.write(f"  - {relation_type}: {count} ({percentage:.1f}%)\n")

        # 抽样示例
        f.write("\n三、关系抽样示例\n")
        f.write("-"*60 + "\n")
        sample_relations = relations_df.groupby('relation').head(5)
        if sample_relations.empty:
            f.write("  暂无样例\n")
        else:
            for relation_type, group in sample_relations.groupby('relation'):
                f.write(f"\n  [{relation_type}]\n")
                for _, row in group.iterrows():
                    f.write(f"    - {row['head']} -> {row['tail']} (来源: {row['source_pdf']})\n")
        
        # 置信度统计
        f.write("\n四、关系置信度统计\n")
        f.write("-"*60 + "\n")
        f.write(f"平均置信度: {relations_df['confidence'].mean():.3f}\n")
        f.write(f"最高置信度: {relations_df['confidence'].max():.3f}\n")
        f.write(f"最低置信度: {relations_df['confidence'].min():.3f}\n")
        
        # 数据源统计
        f.write("\n五、数据源统计\n")
        f.write("-"*60 + "\n")
        f.write(f"PDF文献数量: {entities_df['source_pdf'].nunique()}\n\n")
        
        f.write("各文献贡献的实体数:\n")
        for pdf, count in entities_df['source_pdf'].value_counts().items():
            f.write(f"  - {pdf}: {count}\n")
        
        f.write("\n各文献贡献的关系数:\n")
        for pdf, count in relations_df['source_pdf'].value_counts().items():
            f.write(f"  - {pdf}: {count}\n")
        
        # 核心实体
        f.write("\n六、核心实体（按类型）\n")
        f.write("-"*60 + "\n")
        
        for entity_type in ['Disease', 'Pathogen', 'Host', 'Vector']:
            type_entities = entities_df[entities_df['type'] == entity_type]
            if not type_entities.empty:
                f.write(f"\n{entity_type}:\n")
                for name in type_entities['name'].head(10):
                    f.write(f"  - {name}\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("报告生成完成\n")
        f.write("="*60 + "\n")
    
    print(f"✓ 统计报告已生成: {report_path}")
    
    # 在控制台显示摘要
    print("\n知识图谱摘要:")
    print(f"  - 实体总数: {len(entities_df)}")
    print(f"  - 关系总数: {len(relations_df)}")
    print(f"  - PDF文献数: {entities_df['source_pdf'].nunique()}")
    print(f"  - 平均置信度: {relations_df['confidence'].mean():.3f}")


if __name__ == "__main__":
    main()

