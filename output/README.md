# Output 目录说明

本目录包含知识图谱构建过程中生成的所有输出文件。

## 核心文件

- `neo4j_import/nodes.csv` - Neo4j 节点文件（最终版本）
- `neo4j_import/relations.csv` - Neo4j 关系文件（最终版本）
- `neo4j_import/queries.cypher` - Neo4j 查询示例

## 中间文件

- `entities.csv` - 原始实体数据
- `relations.csv` - 原始关系数据
- `entities_clean.csv` - 清洗后的实体
- `relations_clean.csv` - 清洗后的关系
- `statistics_report.txt` - 统计报告

## 临时文件

- `cache/` - PDF 提取缓存（可删除）
- `extracted_texts/` - 提取的文本文件（可删除）
- `kg_builder.log` - 运行日志

## 数据状态

当前示例数据库状态（基于最终语义清洗后的 PWD 图谱）：

- 节点数: 59
- 关系数: 365

详细统计信息可通过导出脚本和验证脚本生成，例如：

- `export_neo4j_to_csv.py` 导出当前数据库三元组
- `verify_neo4j_data.py` 输出节点/关系分布与一致性检查结果
