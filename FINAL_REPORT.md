# 松材线虫病知识图谱优化完成报告

## 最终成果

### 数据统计

- 节点数：90 个
- 关系数：695 个
- 平均连接度：15.44
- 图密度：17.3%

### 核心节点（Top 10）

1. pine wilt disease (疾病) - 103 个连接
2. bursaphelenchus xylophilus (病原体) - 87 个连接
3. monochamus alternatus (媒介) - 70 个连接
4. pinus thunbergii (寄主) - 66 个连接
5. 叶片 (症状) - 52 个连接
6. 湿地松 (寄主) - 50 个连接
7. 马尾松 (寄主) - 48 个连接
8. 云杉花墨天牛 (媒介) - 47 个连接
9. 褐梗天牛 (媒介) - 42 个连接
10. 松材线虫伴生细菌 (病原体) - 37 个连接

---

## 优化过程总结

### 阶段 1：数据清洗

执行脚本：`clean_and_optimize_kg.py`

清理内容：

- 移除空实体：1 个
- 移除乱码实体：8 个
- 简化复杂关系：31 个
- 初步分类改进：84.3% → 42.5%

结果：115 → 106 个实体，775 → 745 个关系

### 阶段 2：自动消歧

执行脚本：`auto_disambiguate.py --auto`

合并实体（6 对）：

- 松材线虫病害 → pine wilt disease
- 松材线虫 → bursaphelenchus xylophilus
- pwn → bursaphelenchus xylophilus
- 松褐天牛 → monochamus alternatus
- 墨天牛 → monochamus alternatus
- 黑松 → pinus thunbergii

结果：106 → 100 个实体，745 → 735 个关系

### 阶段 3：最终优化

执行脚本：`apply_final_merges.py`

额外合并（10 对）：

- Sentinel-2 系列（3 对）
- 天牛种类（3 对）
- 伴生细菌（1 对）
- 高光谱数据（2 对）
- 林地类型（1 对）

重新分类（14 个）：

- 地点类：南天门、天烛峰、桃花峪等（8 个）
- 寄主类：杂木林、麻栎林（2 个）
- 媒介类：吉丁科、小蠢科、白蚁科（3 个）
- 其他：林区（1 个）

结果：100 → 90 个实体，735 → 704 个关系

### 阶段 4：问题修复

执行脚本：`fix_detected_issues.py`

修复内容：

- 删除自环关系：9 个
- 保留低连接度节点：2 个

最终结果：90 个实体，695 个关系

---

## 类别分布对比

| 类别   | 原始       | 最终       | 改进   |
| ------ | ---------- | ---------- | ------ |
| 其他   | 97 (84.3%) | 28 (31.1%) | -53.2% |
| 地点   | 1 (0.9%)   | 15 (16.7%) | +15.8% |
| 媒介   | 7 (6.1%)   | 13 (14.4%) | +8.3%  |
| 寄主   | 3 (2.6%)   | 10 (11.1%) | +8.5%  |
| 技术   | 0 (0%)     | 7 (7.8%)   | +7.8%  |
| 环境   | 1 (0.9%)   | 4 (4.4%)   | +3.5%  |
| 病原体 | 0 (0%)     | 3 (3.3%)   | +3.3%  |
| 疾病   | 3 (2.6%)   | 3 (3.3%)   | +0.7%  |
| 症状   | 2 (1.7%)   | 3 (3.3%)   | +1.6%  |
| 防治   | 1 (0.9%)   | 3 (3.3%)   | +2.4%  |
| 因素   | 1 (0.9%)   | 1 (1.1%)   | +0.2%  |

---

## 关系质量分析

### 关系类型分布

- co-occurs 关系：522 (75.1%)
- 语义关系：173 (24.9%)

### 主要语义关系

1. 寄生于：14 个 (2.0%)
2. 影响：12 个 (1.7%)
3. 传播：11 个 (1.6%)
4. 引起：5 个 (0.7%)
5. 媒介：3 个 (0.4%)
6. 取食：3 个 (0.4%)
7. 感染：3 个 (0.4%)

### 高权重关系示例

1. pine wilt disease --[寄生于]--> pinus thunbergii (1.000)
2. bursaphelenchus xylophilus --[引起]--> 叶片 (0.759)
3. monochamus alternatus --[co-occurs]--> 叶片 (0.688)

---

## 数据质量检查结果

### 通过的检查

- 无孤立节点
- 无重复关系
- 无自环关系（已修复）
- 无异常权重值
- 所有节点都有类别
- 所有节点都有重要性值
- 所有关系都有权重值
- 关键节点完整
- 关键传播路径完整

### 轻微警告

- 2 个低连接度节点（技术类，已保留）
- co-occurs 关系占比 75.1%（可接受范围）

---

## 关键传播路径

### 病原体 → 媒介 → 寄主

```
bursaphelenchus xylophilus → monochamus alternatus → pinus thunbergii
                                                    → 马尾松
                                                    → 湿地松
```

### 疾病 → 症状

```
pine wilt disease → 叶片
```

### 防治措施

```
诱捕器 → monochamus alternatus
生物防治 → bursaphelenchus xylophilus
```

---

## 生成的文件

### 数据文件

- `output/concepts_final.csv` - 最终实体列表
- `output/relationships_final.csv` - 最终关系列表
- `output/neo4j_import/nodes_final.csv` - Neo4j 节点文件
- `output/neo4j_import/relations_final.csv` - Neo4j 关系文件

### 日志文件

- `output/all_entity_merges.json` - 所有实体合并记录
- `output/review_changes.json` - 审查修改记录

### 工具脚本

- `clean_and_optimize_kg.py` - 数据清洗
- `auto_disambiguate.py` - 自动消歧
- `apply_final_merges.py` - 最终合并
- `fix_detected_issues.py` - 问题修复
- `detect_issues.py` - 问题检测
- `inspect_database.py` - 数据库检查
- `interactive_kg_review.py` - 交互式审查

---

## 使用建议

### 在 Neo4j Browser 中查询

1. **查看核心子图**

```cypher
MATCH (n)-[r]-(m)
WHERE n.category IN ['疾病', '病原体', '媒介', '寄主']
RETURN n, r, m LIMIT 100
```

2. **查找传播路径**

```cypher
MATCH path = (n1 {name: 'bursaphelenchus xylophilus'})
             -[*1..3]-(n2 {name: 'pinus thunbergii'})
RETURN path LIMIT 5
```

3. **按类别统计**

```cypher
MATCH (n:Concept)
RETURN n.category as category, count(*) as count
ORDER BY count DESC
```

4. **查看高权重关系**

```cypher
MATCH (n1)-[r]-(n2)
WHERE r.weight > 0.5
RETURN n1, r, n2
ORDER BY r.weight DESC
LIMIT 20
```

---

## 总结

### 主要成就

1. 实体数量优化：115 → 90（-21.7%）
2. 关系数量优化：775 → 695（-10.3%）
3. 类别分布改进："其他"从 84.3%降至 31.1%
4. 数据质量提升：移除乱码、空值、重复、自环
5. 实体消歧：合并 16 对相似实体
6. 关系简化：简化 31 个复杂关系类型
7. 重新分类：14 个实体获得更准确的类别

### 知识图谱特点

- 核心节点连接良好 (平均 15.44 个连接)
- 传播路径完整清晰
- 类别分布合理
- 数据质量高

### 访问方式

- **Neo4j Browser**: http://localhost:7474
- **用户名**: neo4j
- **密码**: 12345678

---

**报告生成时间**: 2025-11-15
**知识图谱版本**: Final v1.0
