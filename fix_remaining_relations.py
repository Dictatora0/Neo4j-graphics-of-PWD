#!/usr/bin/env python3
"""
修复图谱中剩余的少数语义不理想关系

修复内容（基于当前 Neo4j 中的数据）：
1) bursaphelenchus xylophilus PARASITIZES pine wood nematode associated bacteria
   -> 保留为两个病原体之间的关联关系：
      pine wood nematode associated bacteria RELATED_TO bursaphelenchus xylophilus
   - 若该 RELATED_TO 已存在，则仅删除 PARASITIZES

2) pine wilt disease AFFECTS trap
   -> 改为弱关联：pine wilt disease RELATED_TO trap

3) monochamus alternatus BEHAVIOR_OF leaf
   -> 改为弱关联：monochamus alternatus RELATED_TO leaf

运行方式：
  python fix_remaining_relations.py
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def run_fix_and_report(session, description: str, query: str) -> None:
    print("\n" + "=" * 80)
    print(f"修复: {description}")
    print("=" * 80)
    result = session.run(query)
    record = result.single()
    if record is None:
        print("  ⚠ 无返回结果")
        return
    for key, value in record.items():
        print(f"  {key}: {value}")


def main() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("=" * 80)
        print("修复剩余语义关系")
        print("=" * 80)

        # 1) 线虫与伴生菌：删除 PARASITIZES，并确保存在 RELATED_TO（从菌 -> 线虫）
        query1 = """
        MATCH (p:Pathogen {name:'bursaphelenchus xylophilus'})
              -[r:PARASITIZES]->
              (b:Pathogen {name:'pine wood nematode associated bacteria'})
        WITH p, b, r
        MERGE (b)-[rt:RELATED_TO]->(p)
        ON CREATE SET rt.weight = r.weight
        WITH r
        DELETE r
        RETURN count(r) AS deleted_parasitizes
        """
        run_fix_and_report(
            session,
            "bursaphelenchus xylophilus PARASITIZES pine wood nematode associated bacteria",
            query1,
        )

        # 2) 疾病影响诱捕器：改为 RELATED_TO
        query2 = """
        MATCH (d:Disease {name:'pine wilt disease'})
              -[r:AFFECTS]->
              (c:Control {name:'trap'})
        WITH d, c, r
        MERGE (d)-[rt:RELATED_TO]->(c)
        ON CREATE SET rt.weight = r.weight
        WITH r
        DELETE r
        RETURN count(r) AS deleted_affects_trap
        """
        run_fix_and_report(
            session,
            "pine wilt disease AFFECTS trap -> RELATED_TO",
            query2,
        )

        # 3) 天牛 BEHAVIOR_OF 叶片症状：改为 RELATED_TO
        query3 = """
        MATCH (v:Vector {name:'monochamus alternatus'})
              -[r:BEHAVIOR_OF]->
              (s:Symptom {name:'leaf'})
        WITH v, s, r
        MERGE (v)-[rt:RELATED_TO]->(s)
        ON CREATE SET rt.weight = r.weight
        WITH r
        DELETE r
        RETURN count(r) AS deleted_behavior_of
        """
        run_fix_and_report(
            session,
            "monochamus alternatus BEHAVIOR_OF leaf -> RELATED_TO",
            query3,
        )

        print("\n" + "=" * 80)
        print("修复完成，可以重新导出或在 Neo4j Browser 中查看效果。")
        print("=" * 80)

    driver.close()


if __name__ == "__main__":
    main()
