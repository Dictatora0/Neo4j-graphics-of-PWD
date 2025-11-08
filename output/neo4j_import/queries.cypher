// ============================================================
// 松材线虫病知识图谱 - Cypher 查询示例
// ============================================================
// 在 Neo4j Browser 中逐条复制执行以下查询
// 访问地址: http://localhost:7474

// ------------------------------------------------------------
// 1. 数据概览查询
// ------------------------------------------------------------

// 查看所有节点类型和数量
MATCH (n)
RETURN labels(n)[0] AS 类型, count(n) AS 数量
ORDER BY 数量 DESC;

// 查看所有关系类型和数量
MATCH ()-[r]->()
RETURN type(r) AS 关系类型, count(r) AS 数量
ORDER BY 数量 DESC;

// ------------------------------------------------------------
// 2. 核心实体查询
// ------------------------------------------------------------

// 查看所有疾病
MATCH (d:Disease)
RETURN d.name AS 疾病名称
LIMIT 20;

// 查看所有病原体
MATCH (p:Pathogen)
RETURN p.name AS 病原体名称
LIMIT 20;

// 查看所有宿主植物
MATCH (h:Host)
RETURN h.name AS 宿主名称
LIMIT 20;

// 查看所有传播媒介
MATCH (v:Vector)
RETURN v.name AS 传播媒介
LIMIT 20;

// ------------------------------------------------------------
// 3. 松材线虫病核心查询
// ------------------------------------------------------------

// 查看松材线虫病的完整关系网络（可视化）
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
RETURN d, r, n
LIMIT 50;

// 查询松材线虫病的病原体
MATCH (d:Disease {name: '松材线虫病'})-[r:hasPathogen]->(p:Pathogen)
RETURN d.name AS 疾病, p.name AS 病原体, r.confidence AS 置信度;

// 查询松材线虫病的宿主植物
MATCH (d:Disease {name: '松材线虫病'})-[r:hasHost]->(h:Host)
RETURN d.name AS 疾病, h.name AS 宿主, r.confidence AS 置信度
ORDER BY r.confidence DESC
LIMIT 20;

// 查询松材线虫病的传播媒介
MATCH (d:Disease {name: '松材线虫病'})-[r:hasVector]->(v:Vector)
RETURN d.name AS 疾病, v.name AS 传播媒介, r.confidence AS 置信度
ORDER BY r.confidence DESC;

// 查询松材线虫病的防控措施
MATCH (d:Disease {name: '松材线虫病'})-[r:controlledBy]->(c:ControlMeasure)
RETURN d.name AS 疾病, c.name AS 防控措施, r.confidence AS 置信度
ORDER BY r.confidence DESC;

// 查询松材线虫病的发生地区
MATCH (d:Disease {name: '松材线虫病'})-[r:occursIn]->(reg:Region)
RETURN d.name AS 疾病, reg.name AS 地区;

// ------------------------------------------------------------
// 4. 传播链分析
// ------------------------------------------------------------

// 查询完整的传播链：疾病 → 病原体 + 媒介 + 宿主
MATCH (d:Disease {name: '松材线虫病'})-[:hasPathogen]->(p:Pathogen)
MATCH (d)-[:hasVector]->(v:Vector)
MATCH (d)-[:hasHost]->(h:Host)
RETURN d.name AS 疾病, 
       p.name AS 病原体, 
       v.name AS 传播媒介, 
       h.name AS 宿主
LIMIT 10;

// 查询病原体如何感染宿主（通过媒介）
MATCH path = (p:Pathogen)<-[:hasPathogen]-(d:Disease)-[:hasVector]->(v:Vector)-[:hasHost]->(h:Host)
WHERE d.name = '松材线虫病'
RETURN path
LIMIT 10;

// ------------------------------------------------------------
// 5. 路径查询
// ------------------------------------------------------------

// 查询从疾病到宿主的所有路径（1-3 跳）
MATCH path = (d:Disease {name: '松材线虫病'})-[*1..3]-(h:Host)
RETURN path
LIMIT 10;

// 查询两个实体之间的最短路径
MATCH path = shortestPath(
  (d:Disease {name: '松材线虫病'})-[*]-(h:Host {name: '马尾松'})
)
RETURN path;

// ------------------------------------------------------------
// 6. 统计分析查询
// ------------------------------------------------------------

// 查找连接最多的实体（中心性分析）
MATCH (n)-[r]-()
WITH n, count(r) AS degree
WHERE degree > 5
RETURN labels(n)[0] AS 类型, 
       n.name AS 实体名称, 
       degree AS 连接度
ORDER BY degree DESC
LIMIT 20;

// 统计每种疾病的宿主数量
MATCH (d:Disease)-[:hasHost]->(h:Host)
RETURN d.name AS 疾病, count(DISTINCT h) AS 宿主数量
ORDER BY 宿主数量 DESC
LIMIT 10;

// 统计每种宿主受到的疾病威胁
MATCH (d:Disease)-[:hasHost]->(h:Host)
RETURN h.name AS 宿主, count(DISTINCT d) AS 疾病数量
ORDER BY 疾病数量 DESC
LIMIT 10;

// 统计每个传播媒介传播的疾病数量
MATCH (d:Disease)-[:hasVector]->(v:Vector)
RETURN v.name AS 传播媒介, count(DISTINCT d) AS 疾病数量
ORDER BY 疾病数量 DESC;

// ------------------------------------------------------------
// 7. 高级查询
// ------------------------------------------------------------

// 查询同时感染多种宿主的疾病
MATCH (d:Disease)-[:hasHost]->(h:Host)
WITH d, count(h) AS host_count, collect(h.name) AS hosts
WHERE host_count > 3
RETURN d.name AS 疾病, host_count AS 宿主数量, hosts AS 宿主列表
ORDER BY host_count DESC;

// 查询有共同宿主的疾病（可能有交叉感染风险）
MATCH (d1:Disease)-[:hasHost]->(h:Host)<-[:hasHost]-(d2:Disease)
WHERE d1.name < d2.name
RETURN d1.name AS 疾病1, d2.name AS 疾病2, collect(h.name) AS 共同宿主
LIMIT 10;

// 查询特定地区的疾病及其防控措施
MATCH (d:Disease)-[:occursIn]->(r:Region)
MATCH (d)-[:controlledBy]->(c:ControlMeasure)
WHERE r.name CONTAINS '浙江' OR r.name CONTAINS '江苏'
RETURN r.name AS 地区, d.name AS 疾病, collect(c.name) AS 防控措施;

// ------------------------------------------------------------
// 8. 数据质量检查
// ------------------------------------------------------------

// 检查孤立节点（没有任何关系的节点）
MATCH (n)
WHERE NOT (n)-[]-()
RETURN labels(n)[0] AS 类型, n.name AS 实体名称
LIMIT 20;

// 检查自环关系
MATCH (n)-[r]->(n)
RETURN labels(n)[0] AS 类型, n.name AS 实体, type(r) AS 关系类型;

// 检查重复关系
MATCH (a)-[r1]->(b)
MATCH (a)-[r2]->(b)
WHERE id(r1) < id(r2) AND type(r1) = type(r2)
RETURN a.name AS 起点, type(r1) AS 关系, b.name AS 终点, count(*) AS 重复数量
LIMIT 10;

// ------------------------------------------------------------
// 9. 导出查询
// ------------------------------------------------------------

// 导出所有实体
MATCH (n)
RETURN id(n) AS id, 
       labels(n)[0] AS type, 
       n.name AS name
ORDER BY type, name;

// 导出所有关系
MATCH (a)-[r]->(b)
RETURN a.name AS from, 
       type(r) AS relation, 
       b.name AS to, 
       r.confidence AS confidence
ORDER BY r.confidence DESC;

// 导出松材线虫病的完整信息
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
RETURN d.name AS 疾病,
       type(r) AS 关系类型,
       labels(n)[0] AS 相关实体类型,
       n.name AS 相关实体名称,
       r.confidence AS 置信度
ORDER BY 关系类型, 置信度 DESC;

// ------------------------------------------------------------
// 10. 可视化查询
// ------------------------------------------------------------

// 可视化松材线虫病的一级关系（推荐）
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
RETURN d, r, n;

// 可视化完整的传播生态系统
MATCH (d:Disease {name: '松材线虫病'})-[r1]-(n1)
OPTIONAL MATCH (n1)-[r2]-(n2)
WHERE labels(n1)[0] IN ['Pathogen', 'Vector', 'Host']
RETURN d, r1, n1, r2, n2
LIMIT 100;

// 可视化高度连接的实体网络
MATCH (n)-[r]-()
WITH n, count(r) AS degree
WHERE degree > 10
MATCH (n)-[r]-(m)
RETURN n, r, m
LIMIT 50;

// ------------------------------------------------------------
// 使用提示
// ------------------------------------------------------------
// 1. 在 Neo4j Browser 中，图形化显示的查询最好限制结果数量（使用 LIMIT）
// 2. 对于数据分析，使用表格视图查看结果
// 3. 可以组合多个条件进行复杂查询
// 4. 使用 WHERE 子句添加过滤条件
// 5. 使用 ORDER BY 对结果排序

// ============================================================
// 查询完成
// ============================================================

