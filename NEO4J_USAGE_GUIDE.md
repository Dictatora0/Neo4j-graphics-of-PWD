# Neo4j 知识图谱使用指南

## 快速开始

### 1. 启动 Neo4j

```bash
# 如果Neo4j已运行，跳过此步骤
# 否则运行：
neo4j start
```

### 2. 访问 Neo4j Browser

打开浏览器访问：**http://localhost:7474**

用户名: `neo4j`
密码: `12345678`

### 3. 导入样式（可选但推荐）

1. 点击左下角的**齿轮图标**（设置）
2. 选择**样式**
3. 复制 `neo4j_style.grass` 文件的内容
4. 粘贴到样式编辑器
5. 点击**保存**

## 常用查询

### 基础查询

#### 查看所有节点

```cypher
MATCH (n) RETURN n LIMIT 25
```

#### 查看所有关系

```cypher
MATCH p=()-[r]->() RETURN p LIMIT 25
```

#### 查看特定类型的节点

```cypher
MATCH (n:Pathogen) RETURN n
MATCH (n:Disease) RETURN n
MATCH (n:Vector) RETURN n
MATCH (n:Host) RETURN n
```

### 关系查询

#### 查看所有寄生关系

```cypher
MATCH p=()-[r:PARASITIZES]->() RETURN p
```

#### 查看所有传播关系

```cypher
MATCH p=()-[r:TRANSMITS]->() RETURN p
```

#### 查看所有影响关系

```cypher
MATCH p=()-[r:AFFECTS]->() RETURN p
```

### 路径查询

#### 查看松材线虫病的传播路径

```cypher
MATCH p=(disease:Disease {name: 'pine wilt disease'})-[*1..3]->(n)
RETURN p LIMIT 50
```

#### 查看松材线虫的相关信息

```cypher
MATCH p=(pathogen:Pathogen {name: 'bursaphelenchus xylophilus'})-[*1..2]->(n)
RETURN p LIMIT 50
```

#### 查看天牛与松树的关系

```cypher
MATCH p=(vector:Vector)-[*1..3]-(host:Host)
RETURN p LIMIT 50
```

### 统计查询

#### 查看度数最高的节点

```cypher
MATCH (n)
RETURN n.name as name, n.type as type, n.total_degree as degree
ORDER BY degree DESC
LIMIT 10
```

#### 查看关系类型分布

```cypher
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(*) as count
ORDER BY count DESC
```

#### 查看节点类型分布

```cypher
MATCH (n)
RETURN n.type as node_type, count(*) as count
ORDER BY count DESC
```

#### 查看权重分布

```cypher
MATCH ()-[r]->()
RETURN type(r) as relationship_type,
       avg(r.weight) as avg_weight,
       max(r.weight) as max_weight,
       min(r.weight) as min_weight
ORDER BY avg_weight DESC
```

### 高级查询

#### 查看最短路径

```cypher
MATCH (start {name: 'pine wilt disease'}),
      (end {name: 'pinus thunbergii'})
MATCH p = shortestPath((start)-[*]-(end))
RETURN p
```

#### 查看所有可达节点

```cypher
MATCH (start {name: 'bursaphelenchus xylophilus'})
MATCH p = (start)-[*1..5]->(n)
RETURN DISTINCT n.name as reachable_node, n.type as type
```

#### 查看共现网络

```cypher
MATCH (a)-[r:CO_OCCURS_WITH]-(b)
WHERE a.name IN ['pine wilt disease', 'bursaphelenchus xylophilus', 'monochamus alternatus']
RETURN a, r, b
```

## 可视化优化

### 节点颜色编码

| 类型       | 颜色 | 含义               |
| ---------- | ---- | ------------------ |
| Pathogen   | 红色 | 病原体（松材线虫） |
| Disease    | 橙色 | 疾病（松材线虫病） |
| Vector     | 青色 | 媒介（天牛）       |
| Host       | 绿色 | 寄主（松树）       |
| Location   | 黄色 | 地点               |
| Technology | 蓝色 | 技术/方法          |
| Control    | 浅绿 | 防治措施           |

### 关系颜色编码

| 关系           | 颜色 | 宽度 | 含义 |
| -------------- | ---- | ---- | ---- |
| PARASITIZES    | 红色 | 粗   | 寄生 |
| TRANSMITS      | 橙色 | 粗   | 传播 |
| CAUSES         | 红色 | 粗   | 引起 |
| INFECTS        | 红色 | 粗   | 感染 |
| AFFECTS        | 黄色 | 中   | 影响 |
| FEEDS_ON       | 青色 | 中   | 取食 |
| CARRIES        | 青色 | 中   | 携带 |
| CONTROLS       | 绿色 | 中   | 防治 |
| MONITORS       | 蓝色 | 中   | 监测 |
| CO_OCCURS_WITH | 灰色 | 细   | 共现 |

## 数据统计

### 当前数据规模

- **节点数**: 59 个
- **关系数**: 416 条
- **关系类型**: 26 种

### 节点类型分布

- Host (寄主): 16 个
- Location (地点): 10 个
- Vector (媒介): 5 个
- Technology (技术): 5 个
- Control (防治): 3 个
- Disease (疾病): 1 个
- Pathogen (病原体): 1 个
- Other (其他): 18 个

### 关系类型分布（前 10）

1. CO_OCCURS_WITH (共现): 321 条
2. PARASITIZES (寄生): 17 条
3. TRANSMITS (传播): 13 条
4. AFFECTS (影响): 9 条
5. RELATED_TO (相关): 8 条
6. DISTRIBUTED_IN (分布): 4 条
7. INFECTS (感染): 4 条
8. TREATS (治疗): 4 条
9. CAUSES (引起): 4 条
10. USED_FOR (用于): 3 条

## 关键节点

### 度数最高的节点

1. **pine wilt disease** (松材线虫病) - 度数: 61
2. **bursaphelenchus xylophilus** (松材线虫) - 度数: 50
3. **monochamus alternatus** (褐梗天牛) - 度数: 45
4. **pinus thunbergii** (黑松) - 度数: 45
5. **leaf** (叶片) - 度数: 41

## 查询技巧

### 1. 使用参数化查询

```cypher
MATCH (n {name: $node_name})
RETURN n
```

在参数面板中设置 `$node_name` 的值。

### 2. 使用 LIMIT 限制结果

大型查询时总是使用 LIMIT：

```cypher
MATCH p=()-[r]->() RETURN p LIMIT 100
```

### 3. 使用 EXPLAIN 分析查询性能

```cypher
EXPLAIN MATCH (n) RETURN n
```

### 4. 使用 PROFILE 获取详细性能信息

```cypher
PROFILE MATCH (n) RETURN n
```

## 常见问题

### Q: 如何导出查询结果？

A: 在 Neo4j Browser 中，查询结果下方有"下载"按钮，可以导出为 CSV 或 JSON。

### Q: 如何修改节点或关系的属性？

A: 使用 SET 语句：

```cypher
MATCH (n {name: 'pine wilt disease'})
SET n.description = '由松材线虫引起的松树疾病'
RETURN n
```

### Q: 如何删除节点或关系？

A: 使用 DELETE 语句：

```cypher
MATCH (n {name: 'node_to_delete'})
DETACH DELETE n
```

### Q: 如何创建新的节点或关系？

A: 使用 CREATE 或 MERGE 语句：

```cypher
CREATE (n:NewType {name: 'new_node', property: 'value'})
RETURN n
```

## 更多资源

- [Neo4j 官方文档](https://neo4j.com/docs/)
- [Cypher 查询语言指南](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Browser 用户指南](https://neo4j.com/docs/browser-manual/current/)

## 下一步

1. 已导入数据到 Neo4j
2. 已应用样式配置
3. 建议：在 Neo4j Browser 中探索数据
4. 建议：根据需要调整样式
5. 建议：创建自定义查询和报告
