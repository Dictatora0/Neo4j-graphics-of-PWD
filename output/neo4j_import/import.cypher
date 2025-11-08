// Neo4j 知识图谱导入脚本（简化版，不依赖APOC）
// 松材线虫病知识图谱

// 1. 清空现有数据（可选，谨慎使用）
// MATCH (n) DETACH DELETE n;

// 2. 创建约束和索引
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;

// 3. 导入节点 - Disease
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'Disease'
CREATE (n:Entity:Disease {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - Pathogen
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'Pathogen'
CREATE (n:Entity:Pathogen {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - Host
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'Host'
CREATE (n:Entity:Host {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - Vector
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'Vector'
CREATE (n:Entity:Vector {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - Symptom
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'Symptom'
CREATE (n:Entity:Symptom {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - ControlMeasure
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'ControlMeasure'
CREATE (n:Entity:ControlMeasure {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - Region
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'Region'
CREATE (n:Entity:Region {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 导入节点 - EnvironmentalFactor
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row WHERE row.id IS NOT NULL AND row.label = 'EnvironmentalFactor'
CREATE (n:Entity:EnvironmentalFactor {
    id: toInteger(row.id),
    name: row.name,
    type: row.label
});

// 4. 创建索引加速查询
CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);

// 5. 导入关系 - hasPathogen
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'hasPathogen'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:hasPathogen {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - hasHost
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'hasHost'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:hasHost {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - hasVector
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'hasVector'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:hasVector {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - hasSymptom
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'hasSymptom'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:hasSymptom {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - controlledBy
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'controlledBy'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:controlledBy {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - occursIn
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'occursIn'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:occursIn {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - affectedBy
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'affectedBy'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:affectedBy {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - transmits
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'transmits'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:transmits {confidence: toFloat(row.confidence)}]->(b);

// 导入关系 - infects
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
WITH row WHERE row.start_id IS NOT NULL AND row.end_id IS NOT NULL AND row.relation = 'infects'
MATCH (a:Entity {id: toInteger(row.start_id)})
MATCH (b:Entity {id: toInteger(row.end_id)})
CREATE (a)-[:infects {confidence: toFloat(row.confidence)}]->(b);

// 6. 验证导入结果
MATCH (n)
RETURN labels(n)[1] AS NodeType, count(n) AS Count
ORDER BY Count DESC;

MATCH ()-[r]->()
RETURN type(r) AS RelationType, count(r) AS Count
ORDER BY Count DESC;
