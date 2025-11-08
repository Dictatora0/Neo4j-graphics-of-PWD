// Neo4j 知识图谱导入脚本
// 松材线虫病知识图谱

// 1. 清空现有数据（可选，谨慎使用）
// MATCH (n) DETACH DELETE n;

// 2. 创建约束和索引
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;

// 3. 导入节点
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL
MERGE (n:Entity {id: toInteger(row.id)})
SET n.name = row.name,
    n.type = row.label
WITH n, row.label AS label
CALL apoc.create.addLabels(n, [label]) YIELD node
RETURN count(*) AS nodesCreated;

// 4. 导入关系
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
WITH a, b, row
CALL apoc.create.relationship(a, row.relation, {confidence: toFloat(row.confidence)}, b) YIELD rel
RETURN count(*) AS relationshipsCreated;

// 5. 验证导入结果
MATCH (n)
RETURN labels(n)[0] AS NodeType, count(n) AS Count
ORDER BY Count DESC;

MATCH ()-[r]->()
RETURN type(r) AS RelationType, count(r) AS Count
ORDER BY Count DESC;

// 6. 示例查询

// 查询松材线虫病的病原体
MATCH (d:Disease {name: '松材线虫病'})-[r:hasPathogen]->(p:Pathogen)
RETURN d.name AS Disease, p.name AS Pathogen;

// 查询松材线虫病的宿主
MATCH (d:Disease {name: '松材线虫病'})-[r:hasHost]->(h:Host)
RETURN d.name AS Disease, h.name AS Host;

// 查询松材线虫病的传播媒介
MATCH (d:Disease {name: '松材线虫病'})-[r:hasVector]->(v:Vector)
RETURN d.name AS Disease, v.name AS Vector;

// 查询松材线虫病的症状
MATCH (d:Disease {name: '松材线虫病'})-[r:hasSymptom]->(s:Symptom)
RETURN d.name AS Disease, s.name AS Symptom;

// 查询松材线虫病的防治措施
MATCH (d:Disease {name: '松材线虫病'})-[r:controlledBy]->(c:ControlMeasure)
RETURN d.name AS Disease, c.name AS ControlMeasure;

// 查询松材线虫病的地理分布
MATCH (d:Disease {name: '松材线虫病'})-[r:occursIn]->(reg:Region)
RETURN d.name AS Disease, reg.name AS Region;

// 查询完整的传播链
MATCH path = (d:Disease)-[:hasPathogen]->(p:Pathogen)-[:transmits|infects*1..2]->(h:Host)
RETURN path;

// 查询特定宿主的威胁因素
MATCH (h:Host {name: '马尾松'})<-[r]-(n)
RETURN h.name AS Host, type(r) AS Relation, labels(n)[1] AS SourceType, n.name AS Source;

// 统计每个实体的连接数（度中心性）
MATCH (n)
OPTIONAL MATCH (n)-[r]-()
RETURN n.name AS Entity, n.type AS Type, count(r) AS Degree
ORDER BY Degree DESC
LIMIT 20;
