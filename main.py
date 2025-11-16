#!/usr/bin/env python3
"""
松材线虫病知识图谱构建系统
集成 LLM 概念提取和嵌入式去重功能
"""

import os
import sys
from datetime import datetime

from enhanced_pipeline import EnhancedKnowledgeGraphPipeline
from data_cleaner import DataCleaner
from neo4j_generator import Neo4jGenerator
from neo4j_manager import Neo4jManager
from config_loader import load_config
from logger_config import get_logger

# 初始化日志器
logger = get_logger('MainEnhanced')



def print_step(step_num: int, total_steps: int, title: str):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}/{total_steps}: {title}")
    print(f"{'='*60}\n")


def main():
    """主函数"""
    # 加载配置
    logger.info("加载配置文件...")
    config = load_config()
    
    # 获取配置参数
    PDF_DIR = config.get('pdf.input_directory', './文献')
    OUTPUT_DIR = config.get('output.base_directory', './output')
    CONFIDENCE_THRESHOLD = config.get('cleaning.confidence_threshold', 0.65)
    USE_CACHE = config.get('system.enable_cache', True)
    ENABLE_PARALLEL = config.get('system.enable_parallel', True)
    LLM_MODEL = config.get('llm.model', 'mistral')
    MAX_CHUNKS = config.get('llm.max_chunks', 100)
    
    logger.info(f"PDF目录: {PDF_DIR}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info(f"置信度阈值: {CONFIDENCE_THRESHOLD}")
    logger.info(f"缓存状态: {'启用' if USE_CACHE else '禁用'}")
    logger.info(f"并行处理: {'启用' if ENABLE_PARALLEL else '禁用'}")
    logger.info(f"LLM 模型: {LLM_MODEL}")
    logger.info(f"处理块数: {MAX_CHUNKS if MAX_CHUNKS else '全部'}")
    
    # 检查PDF目录
    if not os.path.exists(PDF_DIR):
        logger.error(f"找不到PDF目录: {PDF_DIR}")
        print(f"错误: 找不到PDF目录: {PDF_DIR}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    start_time = datetime.now()
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # ========== Neo4j 数据库备份和清空 ==========
    neo4j_manager = None
    backup_file = None
    
    try:
        # 初始化 Neo4j 管理器
        neo4j_uri = config.get('neo4j.uri', 'bolt://localhost:7687')
        neo4j_user = config.get('neo4j.user', 'neo4j')
        neo4j_password = config.get('neo4j.password', 'password')
        
        neo4j_manager = Neo4jManager(neo4j_uri, neo4j_user, neo4j_password)
        
        if neo4j_manager.connect():
            logger.info("准备清空 Neo4j 数据库...")
            
            # 备份当前数据库
            backup_file = neo4j_manager.backup_database()
            if backup_file:
                print(f"数据库已备份: {backup_file}")
            
            # 清空数据库
            neo4j_manager.clear_database()
            print("数据库已清空，准备导入新数据\n")
        else:
            logger.info("跳过 Neo4j 数据库操作（服务未运行）\n")
    
    except Exception as e:
        logger.warning(f"Neo4j 操作失败: {e}")
        logger.info("继续执行管道处理...\n")
    
    try:
        # ========== 步骤 1-5: 增强型管道处理 ==========
        print_step(1, 4, "运行增强型知识图谱管道")
        logger.info("初始化增强型管道...")
        
        pipeline = EnhancedKnowledgeGraphPipeline(config)
        concepts_df, relationships_df = pipeline.run(PDF_DIR)
        
        if concepts_df.empty:
            logger.error("增强管道未生成任何概念")
            sys.exit(1)
        
        # ========== 步骤 2: 数据清洗 ==========
        print_step(2, 4, "数据清洗和规范化")
        logger.info("开始数据清洗")
        
        cleaner = DataCleaner(confidence_threshold=CONFIDENCE_THRESHOLD)
        
        # 转换概念为实体格式以兼容现有清洗器
        entities_clean = concepts_df.copy()
        entities_clean.rename(columns={'entity': 'name'}, inplace=True)
        
        # 添加 Neo4j 需要的列
        if 'id' not in entities_clean.columns:
            entities_clean['id'] = entities_clean['name']
        if 'type' not in entities_clean.columns:
            entities_clean['type'] = entities_clean.get('category', 'concept')
        
        # 清洗关系
        relations_clean = relationships_df.copy()
        relations_clean.rename(columns={
            'node_1': 'head',
            'node_2': 'tail',
            'edge': 'relation'
        }, inplace=True)
        
        # 添加缺失的列以兼容现有系统
        if 'confidence' not in relations_clean.columns:
            relations_clean['confidence'] = relations_clean['weight']
        if 'source_pdf' not in relations_clean.columns:
            relations_clean['source_pdf'] = relations_clean['chunk_id'].str.split('_').str[0]
        
        # 保存清洗后的数据
        entities_clean.to_csv(f"{OUTPUT_DIR}/entities_clean.csv", 
                            index=False, encoding='utf-8-sig')
        relations_clean.to_csv(f"{OUTPUT_DIR}/relations_clean.csv", 
                             index=False, encoding='utf-8-sig')
        
        print("\n清洗后的数据已保存:")
        print(f"  - {OUTPUT_DIR}/entities_clean.csv")
        print(f"  - {OUTPUT_DIR}/relations_clean.csv")
        
        # ========== 步骤 3: 生成Neo4j导入文件 ==========
        print_step(3, 4, "生成Neo4j导入文件")
        logger.info("开始生成Neo4j导入文件")
        
        generator = Neo4jGenerator(output_dir=f"{OUTPUT_DIR}/neo4j_import")
        generator.generate_all(entities_clean, relations_clean)
        
        # ========== 步骤 4: 生成统计报告 ==========
        print_step(4, 4, "生成统计报告")
        logger.info("开始生成统计报告")
        
        generate_statistics_report(entities_clean, relations_clean, OUTPUT_DIR)
        
        # ========== 完成 ==========
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"知识图谱构建完成，总耗时: {duration}")
        
        print("\n" + "="*60)
        print("增强型知识图谱构建完成。")
        print("="*60)
        print(f"\n结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration}")
        print(f"\n输出目录: {os.path.abspath(OUTPUT_DIR)}")
        
        print("\n生成的文件:")
        print(f"  1. {OUTPUT_DIR}/concepts.csv - 去重后的概念")
        print(f"  2. {OUTPUT_DIR}/relationships.csv - 合并后的关系")
        print(f"  3. {OUTPUT_DIR}/entities_clean.csv - 清洗后的实体")
        print(f"  4. {OUTPUT_DIR}/relations_clean.csv - 清洗后的关系")
        print(f"  5. {OUTPUT_DIR}/neo4j_import/nodes.csv - Neo4j节点文件")
        print(f"  6. {OUTPUT_DIR}/neo4j_import/relations.csv - Neo4j关系文件")
        print(f"  7. {OUTPUT_DIR}/statistics_report.txt - 统计报告")
        
        print("\n后续步骤:")
        print("  1. 将 nodes.csv 和 relations.csv 复制到 Neo4j 的 import 目录")
        print("  2. 在 Neo4j Browser 中执行 import.cypher 脚本")
        print("  3. 或运行: python ./output/neo4j_import/import_to_neo4j.py")
        
        print("\n示例查询:")
        print("  MATCH (d:Disease)-[r:hasPathogen]->(p:Pathogen)")
        print("  RETURN d.name, p.name;")
        
        print("\n管道特性:")
        print("  - LLM 概念提取（Mistral/Llama/Zephyr）")
        print("  - 语义关系提取（带权重）")
        print("  - 上下文邻近性分析")
        print("  - 嵌入式概念去重")
        print("  - 自动重要性过滤")
        print("  - Neo4j 自动备份和回滚")
        
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
        print("\n\n程序被用户中断")
        
        # 回滚数据库
        if neo4j_manager and backup_file:
            logger.info("尝试回滚 Neo4j 数据库...")
            if neo4j_manager.restore_from_backup(backup_file):
                print("数据库已回滚到之前的状态")
        
        if neo4j_manager:
            neo4j_manager.close()
        
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}", exc_info=True)
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 回滚数据库
        if neo4j_manager and backup_file:
            logger.info("尝试回滚 Neo4j 数据库...")
            if neo4j_manager.restore_from_backup(backup_file):
                print("数据库已回滚到之前的状态")
            else:
                print("数据库回滚失败，请手动恢复")
                print(f"   备份文件: {backup_file}")
        
        if neo4j_manager:
            neo4j_manager.close()
        
        sys.exit(1)
    
    finally:
        # 确保关闭 Neo4j 连接
        if neo4j_manager:
            neo4j_manager.close()


def generate_statistics_report(entities_df, relations_df, output_dir):
    """生成统计报告"""
    report_path = f"{output_dir}/statistics_report.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("松材线虫病知识图谱统计报告\n")
        f.write("Pine Wilt Disease Knowledge Graph Statistics Report\n")
        f.write("="*60 + "\n\n")
        
        f.write("处理方法: LLM 概念提取 + 嵌入式去重 + 邻近性分析\n")
        f.write("Processing Method: LLM Concept Extraction + Embedding Deduplication + Proximity Analysis\n\n")
        
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 实体统计
        f.write("一、实体统计\n")
        f.write("-"*60 + "\n")
        f.write(f"实体总数: {len(entities_df)}\n\n")
        
        if 'type' in entities_df.columns:
            f.write("实体类型分布:\n")
            for entity_type, count in entities_df['type'].value_counts().items():
                percentage = count / len(entities_df) * 100
                f.write(f"  - {entity_type}: {count} ({percentage:.1f}%)\n")
        
        if 'category' in entities_df.columns:
            f.write("\n概念类别分布:\n")
            for category, count in entities_df['category'].value_counts().items():
                percentage = count / len(entities_df) * 100
                f.write(f"  - {category}: {count} ({percentage:.1f}%)\n")
        
        if 'importance' in entities_df.columns:
            f.write("\n重要性分布:\n")
            for importance in sorted(entities_df['importance'].unique()):
                count = len(entities_df[entities_df['importance'] == importance])
                percentage = count / len(entities_df) * 100
                f.write(f"  - 等级 {importance}: {count} ({percentage:.1f}%)\n")
        
        # 关系统计
        f.write("\n二、关系统计\n")
        f.write("-"*60 + "\n")
        f.write(f"关系总数: {len(relations_df)}\n\n")
        
        if 'relation' in relations_df.columns:
            f.write("关系类型分布:\n")
            for relation_type, count in relations_df['relation'].value_counts().items():
                percentage = count / len(relations_df) * 100
                f.write(f"  - {relation_type}: {count} ({percentage:.1f}%)\n")
        
        if 'source' in relations_df.columns:
            f.write("\n关系来源分布:\n")
            for source, count in relations_df['source'].value_counts().items():
                percentage = count / len(relations_df) * 100
                f.write(f"  - {source}: {count} ({percentage:.1f}%)\n")
        
        # 权重统计
        if 'weight' in relations_df.columns:
            f.write("\n三、关系权重统计\n")
            f.write("-"*60 + "\n")
            f.write(f"平均权重: {relations_df['weight'].mean():.3f}\n")
            f.write(f"最高权重: {relations_df['weight'].max():.3f}\n")
            f.write(f"最低权重: {relations_df['weight'].min():.3f}\n")
        
        # 抽样示例
        f.write("\n四、关系抽样示例\n")
        f.write("-"*60 + "\n")
        
        if 'relation' in relations_df.columns:
            sample_relations = relations_df.groupby('relation').head(3)
        else:
            sample_relations = relations_df.head(10)
        
        if sample_relations.empty:
            f.write("  暂无样例\n")
        else:
            for _, row in sample_relations.iterrows():
                head = row.get('head', row.get('node_1', 'N/A'))
                tail = row.get('tail', row.get('node_2', 'N/A'))
                relation = row.get('relation', row.get('edge', 'N/A'))
                weight = row.get('weight', row.get('confidence', 'N/A'))
                f.write(f"    - {head} --[{relation}]--> {tail} (权重: {weight})\n")
        
        # 核心实体
        f.write("\n五、核心实体（按重要性）\n")
        f.write("-"*60 + "\n")
        
        if 'importance' in entities_df.columns:
            top_entities = entities_df.nlargest(15, 'importance')
            for _, row in top_entities.iterrows():
                name = row.get('name', row.get('entity', 'N/A'))
                importance = row.get('importance', 'N/A')
                category = row.get('category', row.get('type', 'N/A'))
                f.write(f"  - {name} (重要性: {importance}, 类别: {category})\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("报告生成完成\n")
        f.write("="*60 + "\n")
    
    print(f"统计报告已生成: {report_path}")
    
    # 在控制台显示摘要
    print("\n知识图谱摘要:")
    print(f"  - 实体总数: {len(entities_df)}")
    print(f"  - 关系总数: {len(relations_df)}")
    if 'importance' in entities_df.columns:
        print(f"  - 平均重要性: {entities_df['importance'].mean():.2f}")
    if 'weight' in relations_df.columns:
        print(f"  - 平均权重: {relations_df['weight'].mean():.3f}")


if __name__ == "__main__":
    main()
