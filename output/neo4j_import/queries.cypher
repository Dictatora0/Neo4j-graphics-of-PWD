// ============================================================
// 松材线虫病知识图谱 - Cypher 查询示例
// ============================================================
// 
// 📖 如何使用本脚本
// ============================================================
// 1. 启动 Neo4j 数据库
//    - 命令行: neo4j start
//    - 或使用 Neo4j Desktop
//
// 2. 打开 Neo4j Browser
//    - 访问: http://localhost:7474
//    - 默认用户名: neo4j
//    - 默认密码: 12345678 (根据你的配置修改)
//
// 3. 执行查询
//    - 方法一: 在 Browser 中逐条复制查询语句，粘贴到顶部输入框，点击运行
//    - 方法二: 使用 Ctrl+Enter (Windows/Linux) 或 Cmd+Enter (Mac) 快速执行
//    - 方法三: 使用 :play 命令加载整个脚本（如果支持）
//
// 4. 查看结果
//    - 图形视图: 适合查看关系网络
//    - 表格视图: 适合查看统计数据
//    - 文本视图: 适合查看原始数据
//
// 5. 保存查询
//    - 点击查询框右侧的"保存"按钮
//    - 或使用 :save 命令
//
// ============================================================

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

// 查看所有防控措施
MATCH (c:ControlMeasure)
RETURN c.name AS 防控措施
ORDER BY c.name;

// 查看所有地区
MATCH (r:Region)
RETURN r.name AS 地区
ORDER BY r.name;



// 查看所有症状
MATCH (s:Symptom)
RETURN s.name AS 症状
ORDER BY s.name;

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
RETURN d.name AS 疾病, reg.name AS 地区, r.confidence AS 置信度
ORDER BY reg.name;

// 查看松材线虫病的所有关系类型（完整概览）
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
RETURN type(r) AS 关系类型, 
       labels(n)[0] AS 目标实体类型, 
       count(*) AS 数量,
       collect(n.name)[0..5] AS 示例实体
ORDER BY 数量 DESC;

// 查询松材线虫病的症状（完整列表）
MATCH (d:Disease {name: '松材线虫病'})-[r:hasSymptom]->(s:Symptom)
RETURN d.name AS 疾病, s.name AS 症状, r.confidence AS 置信度
ORDER BY r.confidence DESC;

// 查询松材线虫病受哪些环境因素影响
MATCH (d:Disease {name: '松材线虫病'})-[r:affectedBy]->(e:EnvironmentalFactor)
RETURN d.name AS 疾病, e.name AS 环境因素, r.confidence AS 置信度
ORDER BY e.name;

// ------------------------------------------------------------
// 4. 症状分析
// ------------------------------------------------------------

// 查看所有症状及其关联的疾病
MATCH (d:Disease)-[r:hasSymptom]->(s:Symptom)
RETURN d.name AS 疾病, s.name AS 症状, r.confidence AS 置信度
ORDER BY d.name, s.name;

// 统计每种症状出现的疾病数量
MATCH (d:Disease)-[:hasSymptom]->(s:Symptom)
RETURN s.name AS 症状, count(DISTINCT d) AS 疾病数量
ORDER BY 疾病数量 DESC;

// 查询松材线虫病的完整症状列表（按严重程度排序）
MATCH (d:Disease {name: '松材线虫病'})-[r:hasSymptom]->(s:Symptom)
RETURN s.name AS 症状, r.confidence AS 置信度
ORDER BY r.confidence DESC;

// ------------------------------------------------------------
// 5. 环境因素分析
// ------------------------------------------------------------

// 查看所有环境因素及其影响的疾病
MATCH (d:Disease)-[r:affectedBy]->(e:EnvironmentalFactor)
RETURN d.name AS 疾病, e.name AS 环境因素, r.confidence AS 置信度
ORDER BY d.name, e.name;

// 统计每种环境因素影响的疾病数量
MATCH (d:Disease)-[:affectedBy]->(e:EnvironmentalFactor)
RETURN e.name AS 环境因素, count(DISTINCT d) AS 疾病数量
ORDER BY 疾病数量 DESC;

// 查询受特定环境因素影响的所有疾病
MATCH (d:Disease)-[:affectedBy]->(e:EnvironmentalFactor {name: '湿度'})
RETURN d.name AS 疾病, e.name AS 环境因素;

// ------------------------------------------------------------
// 6. 传播链分析
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

// 查询完整的知识链：疾病 → 所有相关信息（推荐）
MATCH (d:Disease {name: '松材线虫病'})
OPTIONAL MATCH (d)-[:hasPathogen]->(p:Pathogen)
OPTIONAL MATCH (d)-[:hasVector]->(v:Vector)
OPTIONAL MATCH (d)-[:hasHost]->(h:Host)
OPTIONAL MATCH (d)-[:hasSymptom]->(s:Symptom)
OPTIONAL MATCH (d)-[:controlledBy]->(c:ControlMeasure)
OPTIONAL MATCH (d)-[:occursIn]->(r:Region)
OPTIONAL MATCH (d)-[:affectedBy]->(e:EnvironmentalFactor)
RETURN d.name AS 疾病,
       collect(DISTINCT p.name) AS 病原体,
       collect(DISTINCT v.name) AS 传播媒介,
       collect(DISTINCT h.name) AS 宿主,
       collect(DISTINCT s.name) AS 症状,
       collect(DISTINCT c.name) AS 防控措施,
       collect(DISTINCT r.name) AS 发生地区,
       collect(DISTINCT e.name) AS 环境因素;

// 查询病原体如何感染宿主（通过媒介）
MATCH path = (p:Pathogen)<-[:hasPathogen]-(d:Disease)-[:hasVector]->(v:Vector)-[:hasHost]->(h:Host)
WHERE d.name = '松材线虫病'
RETURN path
LIMIT 10;

// 查询完整的传播链（包含症状和环境因素）
MATCH (d:Disease {name: '松材线虫病'})-[:hasPathogen]->(p:Pathogen)
MATCH (d)-[:hasVector]->(v:Vector)
MATCH (d)-[:hasHost]->(h:Host)
MATCH (d)-[:hasSymptom]->(s:Symptom)
MATCH (d)-[:affectedBy]->(e:EnvironmentalFactor)
RETURN d.name AS 疾病,
       p.name AS 病原体,
       collect(DISTINCT v.name) AS 传播媒介,
       collect(DISTINCT h.name) AS 宿主,
       collect(DISTINCT s.name) AS 症状,
       collect(DISTINCT e.name) AS 环境因素;

// 查询传播路径：病原体 → 媒介 → 宿主
MATCH path = (p:Pathogen)<-[:hasPathogen]-(d:Disease {name: '松材线虫病'})-[:hasVector]->(v:Vector)
MATCH (d)-[:hasHost]->(h:Host)
RETURN p.name AS 病原体, v.name AS 传播媒介, h.name AS 宿主
LIMIT 20;

// ------------------------------------------------------------
// 7. 路径查询
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
// 8. 统计分析查询
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

// 统计松材线虫病的完整信息
MATCH (d:Disease {name: '松材线虫病'})
OPTIONAL MATCH (d)-[:hasPathogen]->(p:Pathogen)
OPTIONAL MATCH (d)-[:hasVector]->(v:Vector)
OPTIONAL MATCH (d)-[:hasHost]->(h:Host)
OPTIONAL MATCH (d)-[:hasSymptom]->(s:Symptom)
OPTIONAL MATCH (d)-[:affectedBy]->(e:EnvironmentalFactor)
RETURN d.name AS 疾病,
       count(DISTINCT p) AS 病原体数量,
       count(DISTINCT v) AS 传播媒介数量,
       count(DISTINCT h) AS 宿主数量,
       count(DISTINCT s) AS 症状数量,
       count(DISTINCT e) AS 环境因素数量;

// 统计每个实体类型的平均连接度
MATCH (n)
OPTIONAL MATCH (n)-[r]-()
WITH labels(n)[0] AS type, n, count(r) AS degree
RETURN type, 
       count(n) AS 实体数量,
       avg(degree) AS 平均连接度,
       max(degree) AS 最大连接度,
       min(degree) AS 最小连接度
ORDER BY 平均连接度 DESC;

// ------------------------------------------------------------
// 9. 高级查询
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
OPTIONAL MATCH (d)-[:controlledBy]->(c:ControlMeasure)
WHERE r.name CONTAINS '浙江' OR r.name CONTAINS '江苏' OR r.name CONTAINS '山东' OR r.name = '中国' OR r.name = '泰山'
RETURN r.name AS 地区, d.name AS 疾病, collect(c.name) AS 防控措施
ORDER BY r.name;

// 查询具有完整信息的疾病（包含病原体、宿主、媒介、症状）
MATCH (d:Disease)
OPTIONAL MATCH (d)-[:hasPathogen]->(p:Pathogen)
OPTIONAL MATCH (d)-[:hasHost]->(h:Host)
OPTIONAL MATCH (d)-[:hasVector]->(v:Vector)
OPTIONAL MATCH (d)-[:hasSymptom]->(s:Symptom)
WITH d, 
     count(DISTINCT p) AS p_count,
     count(DISTINCT h) AS h_count,
     count(DISTINCT v) AS v_count,
     count(DISTINCT s) AS s_count
WHERE p_count > 0 AND h_count > 0 AND v_count > 0 AND s_count > 0
RETURN d.name AS 疾病,
       p_count AS 病原体数,
       h_count AS 宿主数,
       v_count AS 媒介数,
       s_count AS 症状数
ORDER BY (p_count + h_count + v_count + s_count) DESC;

// 查询受多种环境因素影响的疾病
MATCH (d:Disease)-[:affectedBy]->(e:EnvironmentalFactor)
WITH d, count(DISTINCT e) AS env_count, collect(e.name) AS env_factors
WHERE env_count >= 2
RETURN d.name AS 疾病, env_count AS 环境因素数量, env_factors AS 环境因素列表
ORDER BY env_count DESC;

// ------------------------------------------------------------
// 10. 数据质量检查
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
// 11. 导出查询
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

// 导出松材线虫病的完整知识图谱（JSON格式）
MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
WITH d, collect({
  type: type(r),
  target: n.name,
  targetType: labels(n)[0],
  confidence: r.confidence
}) AS relations
RETURN {
  disease: d.name,
  relations: relations
} AS knowledge_graph;

// ------------------------------------------------------------
// 12. 可视化查询
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
// 13. 实用查询技巧
// ------------------------------------------------------------

// 技巧1: 使用变量保存常用查询结果
// 在查询框顶部定义变量，然后在后续查询中使用
// :param diseaseName => '松材线虫病'
// MATCH (d:Disease {name: $diseaseName})-[r]-(n) RETURN d, r, n;

// 技巧2: 使用 WITH 子句进行中间计算
// MATCH (d:Disease)-[:hasHost]->(h:Host)
// WITH d, count(h) AS host_count
// WHERE host_count > 10
// RETURN d.name, host_count;

// 技巧3: 使用 OPTIONAL MATCH 处理可能不存在的关系
// MATCH (d:Disease {name: '松材线虫病'})
// OPTIONAL MATCH (d)-[:hasSymptom]->(s:Symptom)
// RETURN d.name, collect(s.name) AS symptoms;

// 技巧4: 使用 UNWIND 展开集合
// MATCH (d:Disease {name: '松材线虫病'})-[r:hasHost]->(h:Host)
// WITH collect(h.name) AS hosts
// UNWIND hosts AS host
// RETURN host;

// 技巧5: 使用 CASE 进行条件判断
// MATCH (d:Disease)-[r:hasSymptom]->(s:Symptom)
// RETURN d.name,
//        CASE 
//          WHEN count(s) > 5 THEN '症状丰富'
//          WHEN count(s) > 2 THEN '症状中等'
//          ELSE '症状较少'
//        END AS 症状丰富度;

// ------------------------------------------------------------
// 14. 快速查询索引
// ------------------------------------------------------------

// 快速查询1: 查看数据概览
// 执行: 第1节 - 数据概览查询

// 快速查询2: 查看松材线虫病的所有信息
// 执行: 第3节 - 松材线虫病核心查询

// 快速查询3: 查看症状列表
// 执行: 第4节 - 症状分析

// 快速查询4: 查看环境因素
// 执行: 第5节 - 环境因素分析

// 快速查询5: 可视化知识图谱
// 执行: 第12节 - 可视化查询

// ------------------------------------------------------------
// 15. 常见问题排查
// ------------------------------------------------------------

// 问题1: 查询返回空结果
// 解决: 检查实体名称是否正确（区分大小写）
// 示例: MATCH (d:Disease {name: '松材线虫病'}) RETURN d;

// 问题2: 查询执行缓慢
// 解决: 添加 LIMIT 限制结果数量，或使用索引
// 示例: MATCH (n) RETURN n LIMIT 100;

// 问题3: 关系方向错误
// 解决: 检查关系方向，使用双向匹配 [r]- 或指定方向 [r]->
// 示例: MATCH (a)-[r]-(b) RETURN a, r, b;

// 问题4: 中文显示乱码
// 解决: 确保 Neo4j Browser 使用 UTF-8 编码

// ------------------------------------------------------------
// 16. 性能优化建议
// ------------------------------------------------------------

// 1. 为常用查询字段创建索引
// CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name);
// CREATE INDEX symptom_name IF NOT EXISTS FOR (s:Symptom) ON (s.name);

// 2. 使用 PROFILE 分析查询性能
// PROFILE MATCH (d:Disease {name: '松材线虫病'})-[r]-(n) RETURN d, r, n;

// 3. 使用 EXPLAIN 查看查询计划
// EXPLAIN MATCH (d:Disease)-[:hasHost]->(h:Host) RETURN d, h;

// 4. 限制结果数量，避免返回过多数据
// MATCH (n) RETURN n LIMIT 100;

// 5. 使用 WHERE 子句尽早过滤数据
// MATCH (d:Disease)
// WHERE d.name = '松材线虫病'
// MATCH (d)-[r]-(n)
// RETURN d, r, n;

// ------------------------------------------------------------
// 17. 导出数据
// ------------------------------------------------------------

// 导出为 CSV 格式（在 Browser 中点击下载按钮）
// MATCH (n)
// RETURN labels(n)[0] AS type, n.name AS name
// ORDER BY type, name;

// 导出为 JSON 格式
// MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
// RETURN {
//   disease: d.name,
//   relations: collect({
//     type: type(r),
//     target: n.name,
//     targetType: labels(n)[0]
//   })
// } AS result;

// ------------------------------------------------------------
// 📖 使用提示
// ------------------------------------------------------------
// 
// 1. 在 Neo4j Browser 中，图形化显示的查询最好限制结果数量（使用 LIMIT）
// 2. 对于数据分析，使用表格视图查看结果
// 3. 可以组合多个条件进行复杂查询
// 4. 使用 WHERE 子句添加过滤条件
// 5. 使用 ORDER BY 对结果排序
// 6. 使用 PROFILE 或 EXPLAIN 分析查询性能
// 7. 保存常用查询以便快速访问
// 8. 使用参数化查询提高安全性
//
// 💡 快捷键:
//   - Ctrl+Enter / Cmd+Enter: 执行查询
//   - Ctrl+Up / Cmd+Up: 历史查询
//   - Ctrl+L / Cmd+L: 清空查询框
//
// 🔗 相关资源:
//   - Neo4j 官方文档: https://neo4j.com/docs/
//   - Cypher 查询语言: https://neo4j.com/docs/cypher-manual/
//   - Neo4j Browser 指南: https://neo4j.com/developer/neo4j-browser/

// ============================================================
// 查询脚本完成
// ============================================================
// 
// 本脚本包含 17 个查询类别，共 50+ 个实用查询示例
// 涵盖了数据概览、核心查询、症状分析、环境因素分析、
// 传播链分析、路径查询、统计分析、高级查询、数据质量检查、
// 导出查询、可视化查询等各个方面
//
// 建议从第1节开始，逐步探索知识图谱的各个维度
//
// ============================================================
// 📊 当前数据库状态
// ============================================================
// 
// 节点总数: 44 个
// 关系总数: 43 条
// 
// 节点类型分布:
//   - Host: 13 个
//   - Symptom: 11 个
//   - ControlMeasure: 11 个
//   - EnvironmentalFactor: 3 个
//   - Region: 2 个
//   - Vector: 2 个
//   - Disease: 1 个（松材线虫病）
//   - Pathogen: 1 个
// 
// 关系类型分布:
//   - hasHost: 13 条
//   - hasSymptom: 11 条
//   - controlledBy: 11 条
//   - affectedBy: 3 条
//   - hasVector: 2 条
//   - occursIn: 2 条
//   - hasPathogen: 1 条
// 
// 松材线虫病连接: 43 条关系（所有关系都连接到松材线虫病）
// 
// 数据质量: ✅ 优秀（无孤立节点、无自环、无错误关系类型）
//
// ============================================================

