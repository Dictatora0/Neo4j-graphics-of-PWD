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

当前数据库状态：
- 节点数: 37
- 关系数: 46
- 数据质量: 100/100 ⭐⭐⭐⭐⭐

详细信息请查看项目根目录的 `DATA_STATUS.md`。
