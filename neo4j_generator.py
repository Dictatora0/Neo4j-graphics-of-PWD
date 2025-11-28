"""
Neo4j导入文件生成模块
将清洗后的实体和关系转换为Neo4j可导入的格式
"""

import pandas as pd
import os
from typing import Optional


class Neo4jGenerator:
    """Neo4j导入文件生成器"""
    
    def __init__(self, output_dir: str = "./output/neo4j_import"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_nodes_csv(self, entities_df: pd.DataFrame) -> str:
        """生成节点CSV文件"""
        # 准备节点数据
        nodes_df = entities_df[['id', 'name', 'type']].copy()
        nodes_df.columns = ['id', 'name', 'label']
        
        # 保存CSV
        nodes_path = os.path.join(self.output_dir, 'nodes.csv')
        nodes_df.to_csv(nodes_path, index=False, encoding='utf-8-sig')
        
        print(f"节点文件已生成: {nodes_path}")
        print(f"  共 {len(nodes_df)} 个节点")
        print(f"\n  节点类型分布:")
        for label, count in nodes_df['label'].value_counts().items():
            print(f"    - {label}: {count}")
        
        return nodes_path
    
    def generate_relations_csv(self, relations_df: pd.DataFrame, 
                               entities_df: pd.DataFrame) -> str:
        """生成关系CSV文件"""
        # 创建实体名称到ID的映射
        entity_to_id = dict(zip(entities_df['name'], entities_df['id']))
        
        # 映射head和tail到ID
        relations_data = []
        
        for _, row in relations_df.iterrows():
            head_id = entity_to_id.get(row['head'])
            tail_id = entity_to_id.get(row['tail'])
            
            if head_id and tail_id:
                relations_data.append({
                    'start_id': head_id,
                    'relation': row['relation'],
                    'end_id': tail_id,
                    'confidence': row['confidence']
                })
        
        rels_df = pd.DataFrame(relations_data)
        
        # 保存CSV
        rels_path = os.path.join(self.output_dir, 'relations.csv')
        rels_df.to_csv(rels_path, index=False, encoding='utf-8-sig')
        
        print(f"\n关系文件已生成: {rels_path}")
        print(f"  共 {len(rels_df)} 个关系")
        print(f"\n  关系类型分布:")
        for relation, count in rels_df['relation'].value_counts().items():
            print(f"    - {relation}: {count}")
        
        return rels_path
    
    def generate_cypher_script(self, nodes_path: str, rels_path: str) -> str:
        """生成Cypher导入脚本"""
        cypher_script = """// Neo4j 知识图谱导入脚本
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
"""
        
        # 生成简化版本（不依赖APOC）
        cypher_script_simple = """// Neo4j 知识图谱导入脚本（简化版，不依赖APOC）
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
"""
        
        # 保存脚本
        script_path = os.path.join(self.output_dir, 'import.cypher')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(cypher_script_simple)
        
        script_path_apoc = os.path.join(self.output_dir, 'import_with_apoc.cypher')
        with open(script_path_apoc, 'w', encoding='utf-8') as f:
            f.write(cypher_script)
        
        print(f"\nCypher 脚本已生成:")
        print(f"  - {script_path} (标准版)")
        print(f"  - {script_path_apoc} (APOC版)")
        
        return script_path
    
    def generate_python_import_script(self) -> str:
        """生成Python自动导入脚本"""
        python_script = """#!/usr/bin/env python3
'''
Neo4j 自动导入脚本
使用Python的neo4j驱动自动执行导入
'''

from neo4j import GraphDatabase
import os

# Neo4j 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"  # 请修改为您的密码

def import_to_neo4j(uri, user, password, cypher_file):
    '''执行Cypher脚本导入数据'''
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        # 读取Cypher脚本
        with open(cypher_file, 'r', encoding='utf-8') as f:
            cypher_script = f.read()
        
        # 分割脚本为独立语句
        statements = [s.strip() for s in cypher_script.split(';') if s.strip() and not s.strip().startswith('//')]
        
        with driver.session() as session:
            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"执行语句 {i}/{len(statements)}...")
                    try:
                        result = session.run(statement)
                        print("完成")
                    except Exception as e:
                        print(f"✗ 错误: {e}")
        
        print("\\n导入完成！")
        
    finally:
        driver.close()

if __name__ == "__main__":
    cypher_file = "./output/neo4j_import/import.cypher"
    
    if not os.path.exists(cypher_file):
        print(f"错误: 找不到文件 {cypher_file}")
        exit(1)
    
    print(f"开始导入数据到 Neo4j...")
    print(f"连接: {NEO4J_URI}")
    print(f"用户: {NEO4J_USER}")
    print()
    
    import_to_neo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, cypher_file)
"""
        
        script_path = os.path.join(self.output_dir, 'import_to_neo4j.py')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(python_script)
        
        # 设置可执行权限
        os.chmod(script_path, 0o755)
        
        print(f"\nPython 导入脚本已生成: {script_path}")
        
        return script_path
    
    def generate_all(self, entities_df: pd.DataFrame, relations_df: pd.DataFrame):
        """生成所有Neo4j导入文件"""
        print("=" * 60)
        print("开始生成 Neo4j 导入文件")
        print("=" * 60)
        
        # 生成节点和关系CSV
        nodes_path = self.generate_nodes_csv(entities_df)
        rels_path = self.generate_relations_csv(relations_df, entities_df)
        
        # 生成Cypher脚本
        cypher_path = self.generate_cypher_script(nodes_path, rels_path)
        
        # 生成Python导入脚本
        python_path = self.generate_python_import_script()
        
        print("\n" + "=" * 60)
        print("所有文件已生成完毕！")
        print("=" * 60)
        print(f"\n输出目录: {self.output_dir}")
        print("\n使用方法:")
        print("1. 将 nodes.csv 和 relations.csv 复制到 Neo4j 的 import 目录")
        print("2. 在 Neo4j Browser 中执行 import.cypher 脚本")
        print("   或者运行: python import_to_neo4j.py")


if __name__ == "__main__":
    # 读取清洗后的数据
    entities_df = pd.read_csv("./output/entities_clean.csv", encoding='utf-8-sig')
    relations_df = pd.read_csv("./output/relations_clean.csv", encoding='utf-8-sig')
    
    # 生成Neo4j导入文件
    generator = Neo4jGenerator()
    generator.generate_all(entities_df, relations_df)

