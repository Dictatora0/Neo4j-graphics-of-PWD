#!/usr/bin/env python3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import requests
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "12345678")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

def _call_llm(prompt: str, system: str = "") -> Optional[str]:
    """简单的 LLM 包装函数,用于社区主题摘要
    
    说明:
    - 温度设为 0.1,尽量保证摘要在多次运行之间稳定
    - 这里不做重试,失败直接返回 None,由调用方走规则摘要兜底
    """
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "temperature": 0.1,
            "top_p": 0.9,
            "top_k": 40,
        }
        resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
        resp.raise_for_status()
        return (resp.json().get("response", "") or "").strip()
    except Exception:
        return None

def _summarize_community(cid: int, members: List[Dict]) -> Dict:
    # 从 GDS 返回的成员列表中拆出名称和类型,后续用于构造“社区特征概要”
    names = [m.get("name", "") for m in members if m.get("name")]
    types = [m.get("type", "") for m in members]
    freq = {}
    for t in types:
        if not t:
            continue
        freq[t] = freq.get(t, 0) + 1
    # 统计各类型出现次数,拼成一行便于 LLM 把握“社区是什么类型为主”
    type_desc = ", ".join([f"{k}:{v}" for k, v in sorted(freq.items(), key=lambda x: -x[1])])
    # 只取前 20 个节点名喂给 LLM,避免提示词过长
    top_nodes = names[:20]
    system = "你是生物学知识图谱专家，为社区生成中文主题摘要。"
    user = (
        f"社区ID: {cid}\n"
        f"节点类型分布: {type_desc}\n"
        f"代表节点: {', '.join(top_nodes)}\n\n"
        "请给出:\n"
        "1) 主题标题(不超过20字)\n"
        "2) 社区摘要(150-250字)\n"
        "3) 3-6个关键词\n"
        "仅返回JSON: {\"title\":..., \"summary\":..., \"keywords\":[...]}"
    )
    # 调用上面的简单 LLM 包装,让下游只关心结果文本
    resp = _call_llm(user, system)
    if not resp:
        return {"title": f"社区{cid}", "summary": "", "keywords": []}
    text = resp.strip()
    # 兼容部分模型自动包上一层 ```json / ``` 代码块的情况
    if text.startswith("```json"):
        text = text[7:].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    try:
        # 尝试按约定的 JSON 结构解析,失败则退回到"纯文本摘要"模式
        data = json.loads(text.strip('`').strip())
        title = str(data.get("title", f"社区{cid}")).strip()
        summary = str(data.get("summary", "")).strip()
        keywords = data.get("keywords", []) or []
        if not isinstance(keywords, list):
            keywords = [str(keywords)]
        return {"title": title, "summary": summary, "keywords": keywords}
    except Exception:
        return {"title": f"社区{cid}", "summary": text[:300], "keywords": []}

def _ensure_theme_indexes(session):
    """确保 Theme 节点上存在基本索引,提升后续主题查询性能
    
    出错直接忽略,避免因为图数据库版本兼容性问题影响主流程
    """
    try:
        session.run("CREATE INDEX theme_name IF NOT EXISTS FOR (t:Theme) ON (t.name)")
    except Exception:
        pass

def run():
    """主入口: 基于 Neo4j + GDS 进行社区检测,并为每个社区生成 Theme 主题节点
    
    步骤概览:
    1) 使用 gds.graph.project.cypher 将当前图投影为 GDS 内存图
    2) 运行 Louvain 社区检测,写回 communityId
    3) 按 communityId 聚合节点,调用 LLM 生成摘要
    4) 为每个社区创建 Theme 节点并建立 BELONGS_TO 关系
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        # 如果之前已经存在同名 GDS 图,先尝试丢弃;失败直接忽略,保持幂等
        try:
            session.run("CALL gds.graph.drop($name, false)", name="pwd_graph")
        except Exception:
            pass
        # 使用 Cypher 方式将现有 Neo4j 图投影为 GDS 图,带上关系权重
        session.run(
            """
            CALL gds.graph.project.cypher(
              $name,
              'MATCH (n) RETURN id(n) AS id, labels(n) AS labels',
              'MATCH (n)-[r]->(m) RETURN id(n) AS source, id(m) AS target, type(r) AS type, r.weight AS weight'
            )
            """,
            name="pwd_graph",
        )
        # 在投影图上运行 Louvain 社区检测,并把社区编号写回节点属性 communityId
        session.run(
            """
            CALL gds.louvain.write($name, {relationshipWeightProperty:'weight', writeProperty:'communityId'})
            """,
            name="pwd_graph",
        )
        # 将同一 communityId 的节点聚合为一个成员列表,后面逐个送入 LLM 生成摘要
        records = session.run(
            """
            MATCH (n)
            WITH n.communityId AS community, collect({name:n.name, type:n.type, degree:n.total_degree}) AS members
            RETURN community, members ORDER BY community
            """
        )
        communities = [(r["community"], r["members"]) for r in records]
        _ensure_theme_indexes(session)
        created = 0
        linked = 0
        for cid, members in communities:
            summary = _summarize_community(cid, members)
            title = summary.get("title") or f"社区{cid}"
            name = f"{title}"
            session.run(
                """
                MERGE (t:Theme {communityId:$cid})
                ON CREATE SET t.name=$name, t.type='Theme', t.created_at=$ts, t.summary=$summary, t.keywords=$keywords
                ON MATCH SET t.name=$name, t.summary=$summary, t.keywords=$keywords
                """,
                cid=cid,
                name=name,
                ts=datetime.now().isoformat(),
                summary=summary.get("summary", ""),
                keywords=summary.get("keywords", []),
            )
            created += 1
            for m in members:
                n = m.get("name")
                if not n:
                    continue
                session.run(
                    """
                    MATCH (a {name:$n})
                    MATCH (t:Theme {communityId:$cid})
                    MERGE (a)-[:BELONGS_TO]->(t)
                    """,
                    n=n,
                    cid=cid,
                )
                linked += 1
        print(f"创建主题节点: {created}")
        print(f"建立归属关系: {linked}")
    driver.close()

if __name__ == "__main__":
    run()
