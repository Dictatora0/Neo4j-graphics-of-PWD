// Neo4j 数据库备份
// 时间: 2025-11-14 20:58:56
// 节点数: 44, 关系数: 43

// ========== 节点 ==========
CREATE (:ControlMeasure {name: '化学防治', id: 1});
CREATE (:ControlMeasure {name: '检疫', id: 2});
CREATE (:ControlMeasure {name: '清理病死树', id: 3});
CREATE (:ControlMeasure {name: '焚烧', id: 4});
CREATE (:ControlMeasure {name: '熏蒸', id: 5});
CREATE (:ControlMeasure {name: '生物防治', id: 6});
CREATE (:ControlMeasure {name: '监测', id: 7});
CREATE (:ControlMeasure {name: '营林措施', id: 8});
CREATE (:ControlMeasure {name: '诱捕器', id: 9});
CREATE (:ControlMeasure {name: '除害处理', id: 10});
CREATE (:ControlMeasure {name: '隔离带', id: 11});
CREATE (:Disease {name: '松材线虫病', id: 12});
CREATE (:EnvironmentalFactor {name: '日照', id: 13});
CREATE (:EnvironmentalFactor {name: '海拔', id: 14});
CREATE (:EnvironmentalFactor {name: '湿度', id: 15});
CREATE (:Host {name: '云南松', id: 16});
CREATE (:Host {name: '华山松', id: 17});
CREATE (:Host {name: '思茅松', id: 18});
CREATE (:Host {name: '日本黑松', id: 19});
CREATE (:Host {name: '樟子松', id: 20});
CREATE (:Host {name: '油松', id: 21});
CREATE (:Host {name: '湿地松', id: 22});
CREATE (:Host {name: '火炬松', id: 23});
CREATE (:Host {name: '白皮松', id: 24});
CREATE (:Host {name: '红松', id: 25});
CREATE (:Host {name: '赤松', id: 26});
CREATE (:Host {name: '马尾松', id: 27});
CREATE (:Host {name: '黑松', id: 28});
CREATE (:Pathogen {name: '松材线虫', id: 29});
CREATE (:Region {name: '中国', id: 30});
CREATE (:Region {name: '泰山', id: 31});
CREATE (:Symptom {name: '整株枯死', id: 32});
CREATE (:Symptom {name: '材色变化', id: 33});
CREATE (:Symptom {name: '枝条枯萎', id: 34});
CREATE (:Symptom {name: '枯死', id: 35});
CREATE (:Symptom {name: '树干失水', id: 36});
CREATE (:Symptom {name: '树脂分泌停止', id: 37});
CREATE (:Symptom {name: '萎蔫', id: 38});
CREATE (:Symptom {name: '蓝变', id: 39});
CREATE (:Symptom {name: '针叶变色', id: 40});
CREATE (:Symptom {name: '针叶褐变', id: 41});
CREATE (:Symptom {name: '针叶黄化', id: 42});
CREATE (:Vector {name: '天牛', id: 43});
CREATE (:Vector {name: '松褐天牛', id: 44});

// ========== 关系 ==========
MATCH (a {id: 12}), (b {id: 30})
CREATE (a)-[:occursIn {confidence: 0.72}]->(b);
MATCH (a {id: 12}), (b {id: 31})
CREATE (a)-[:occursIn {confidence: 0.72}]->(b);
MATCH (a {id: 12}), (b {id: 16})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 17})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 18})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 19})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 20})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 21})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 22})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 23})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 24})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 25})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 26})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 27})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 28})
CREATE (a)-[:hasHost {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 29})
CREATE (a)-[:hasPathogen {confidence: 0.95}]->(b);
MATCH (a {id: 12}), (b {id: 1})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 2})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 3})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 4})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 5})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 6})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 7})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 8})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 9})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 10})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 11})
CREATE (a)-[:controlledBy {confidence: 0.65}]->(b);
MATCH (a {id: 12}), (b {id: 43})
CREATE (a)-[:hasVector {confidence: 0.7}]->(b);
MATCH (a {id: 12}), (b {id: 44})
CREATE (a)-[:hasVector {confidence: 0.95}]->(b);
MATCH (a {id: 12}), (b {id: 13})
CREATE (a)-[:affectedBy {confidence: 0.7}]->(b);
MATCH (a {id: 12}), (b {id: 14})
CREATE (a)-[:affectedBy {confidence: 0.7}]->(b);
MATCH (a {id: 12}), (b {id: 15})
CREATE (a)-[:affectedBy {confidence: 0.7}]->(b);
MATCH (a {id: 12}), (b {id: 32})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 33})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 34})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 35})
CREATE (a)-[:hasSymptom {confidence: 0.9}]->(b);
MATCH (a {id: 12}), (b {id: 36})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 37})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 38})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 39})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 40})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 41})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
MATCH (a {id: 12}), (b {id: 42})
CREATE (a)-[:hasSymptom {confidence: 0.8}]->(b);
