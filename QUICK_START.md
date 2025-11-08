# 快速使用指南

## ✅ 当前状态

知识图谱已成功导入 Neo4j！

- **节点数量**: 1,021 个
- **关系数量**: 401 条
- **数据质量**: 已修正和优化
- **访问地址**: http://localhost:7474

---

## 🎯 立即开始

### 1. 打开 Neo4j Browser

在浏览器中访问：http://localhost:7474

默认登录信息：

- 用户名：`neo4j`
- 密码：`12345678`

### 2. 执行第一个查询

在 Neo4j Browser 的查询框中输入并执行：

```cypher
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
RETURN d, r, n
LIMIT 50
```

点击执行按钮，您将看到松材线虫病的关系网络可视化！

### 3. 查看数据统计

```cypher
MATCH (n)
RETURN labels(n)[0] AS 类型, count(n) AS 数量
ORDER BY 数量 DESC
```

---

## 📚 推荐查询顺序

### 第 1 步：了解数据结构

```cypher
// 查看所有节点类型
MATCH (n)
RETURN DISTINCT labels(n)[0] AS 节点类型
ORDER BY 节点类型
```

```cypher
// 查看所有关系类型
MATCH ()-[r]->()
RETURN DISTINCT type(r) AS 关系类型
ORDER BY 关系类型
```

### 第 2 步：探索核心实体

```cypher
// 查看所有疾病
MATCH (d:Disease)
RETURN d.name AS 疾病
LIMIT 10
```

```cypher
// 查看所有病原体
MATCH (p:Pathogen)
RETURN p.name AS 病原体
LIMIT 10
```

```cypher
// 查看所有宿主
MATCH (h:Host)
RETURN h.name AS 宿主
LIMIT 20
```

### 第 3 步：分析关系网络

```cypher
// 松材线虫病的完整网络（可视化）
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
RETURN d, r, n
```

```cypher
// 传播链分析
MATCH (d:Disease {name: '松材线虫病'})-[:hasPathogen]->(p:Pathogen)
MATCH (d)-[:hasVector]->(v:Vector)
MATCH (d)-[:hasHost]->(h:Host)
RETURN d.name AS 疾病, p.name AS 病原体, v.name AS 媒介, h.name AS 宿主
```

### 第 4 步：高级分析

```cypher
// 找出最重要的实体（中心性分析）
MATCH (n)-[r]-()
WITH n, count(r) AS degree
WHERE degree > 5
RETURN labels(n)[0] AS 类型, n.name AS 实体, degree AS 连接数
ORDER BY degree DESC
LIMIT 20
```

---

## 🎨 可视化技巧

### 调整图形布局

在 Neo4j Browser 中：

1. 点击左下角的设置图标 ⚙️
2. 调整节点颜色、大小
3. 选择不同的布局算法

### 保存查询

1. 点击查询框旁边的星标 ⭐
2. 给查询命名
3. 下次可以快速调用

### 导出结果

1. 执行查询后，点击右上角的导出图标
2. 可以导出为 CSV、JSON 或图片

---

## 📖 常用查询模板

### 查询特定实体的所有关系

```cypher
MATCH (n {name: '实体名称'})-[r]-(m)
RETURN n, r, m
```

### 查询两个实体之间的路径

```cypher
MATCH path = shortestPath(
  (a {name: '实体A'})-[*]-(b {name: '实体B'})
)
RETURN path
```

### 按条件过滤

```cypher
MATCH (h:Host)
WHERE h.name CONTAINS '松'
RETURN h.name
```

### 统计和聚合

```cypher
MATCH (d:Disease)-[:hasHost]->(h:Host)
RETURN d.name AS 疾病, count(h) AS 宿主数量
ORDER BY 宿主数量 DESC
```

---

## 🔗 更多资源

### 本地文档

- `output/IMPORT_SUMMARY.md` - 详细的导入报告
- `output/neo4j_import/queries.cypher` - 完整查询示例集合
- `README.md` - 项目完整文档
- `TROUBLESHOOTING.md` - 故障排除

### 查询文件使用

打开 `output/neo4j_import/queries.cypher`，复制其中的查询到 Neo4j Browser 执行。

文件包含 10 大类查询：

1. 数据概览查询
2. 核心实体查询
3. 松材线虫病核心查询
4. 传播链分析
5. 路径查询
6. 统计分析查询
7. 高级查询
8. 数据质量检查
9. 导出查询
10. 可视化查询

### Neo4j 官方资源

- Neo4j Browser 指南：Help → Browser User Guide
- Cypher 语法：Help → Cypher Help
- 官方文档：https://neo4j.com/docs/

---

## 💡 使用技巧

### 1. 限制结果数量

在查询末尾添加 `LIMIT N`，避免返回过多结果：

```cypher
MATCH (n)-[r]-(m)
RETURN n, r, m
LIMIT 50
```

### 2. 使用变量简化查询

```cypher
// 定义变量
:param disease_name => '松材线虫病'

// 使用变量
MATCH (d:Disease {name: $disease_name})-[r]-(n)
RETURN d, r, n
```

### 3. 组合多个条件

```cypher
MATCH (d:Disease)-[r:hasHost]->(h:Host)
WHERE d.name = '松材线虫病'
  AND r.confidence > 0.7
RETURN h.name, r.confidence
ORDER BY r.confidence DESC
```

### 4. 保存常用查询

在 Neo4j Browser 中：

- 点击查询框旁的 ⭐ 收藏常用查询
- 使用 `:play cypher` 学习 Cypher 语法

---

## 🚀 下一步

1. **探索数据**：尝试不同的查询，发现有趣的模式
2. **导出分析**：将查询结果导出为 CSV 进行进一步分析
3. **扩展数据**：添加更多文献，运行 `python main.py`
4. **构建应用**：基于知识图谱开发问答系统或可视化应用

---

## 📞 需要帮助？

- 查看 `TROUBLESHOOTING.md` 解决常见问题
- Neo4j Browser 中点击 Help 查看帮助
- 查看 `output/kg_builder.log` 日志文件

---

**祝您探索愉快！** 🎉
