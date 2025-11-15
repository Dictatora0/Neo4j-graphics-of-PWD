#!/usr/bin/env python3
"""
Fix semantic and logical issues detected in the database.
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("Fixing Database Semantic and Logical Issues")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 1. Correct Invalid Relationship
    # ========================================================================
    print("\n🔧 1. Correcting Invalid Relationship...")
    print("   - Deleting: (bursaphelenchus xylophilus)-[:防治]->(诱捕器)")
    
    # Delete the incorrect relationship
    session.run("""
        MATCH (p:病原体 {name: 'bursaphelenchus xylophilus'})-[r:防治]->(t:防治 {name: '诱捕器'})
        DELETE r
    """)
    
    print("   + Creating: (诱捕器)-[:防治]->(monochamus alternatus)")
    # Create the correct relationship (Trap controls the Vector)
    session.run("""
        MATCH (t:防治 {name: '诱捕器'})
        MATCH (v:媒介 {name: 'monochamus alternatus'})
        MERGE (t)-[r:防治]->(v)
        SET r.weight = 0.8, r.type = '防治'
    """)
    print("   ✅ Done.")

    # ========================================================================
    # 2. Link Orphaned Hosts
    # ========================================================================
    print("\n🔧 2. Linking Orphaned Hosts...")
    orphaned_hosts = ['杂木林', '松林', '青松', '麻栎林']
    pathogen = 'bursaphelenchus xylophilus'
    
    for host in orphaned_hosts:
        print(f"   + Creating: ({host})-[:寄生于]->({pathogen})")
        session.run("""
            MATCH (h:寄主 {name: $host_name})
            MATCH (p:病原体 {name: $pathogen_name})
            MERGE (h)-[r:寄生于]->(p)
            SET r.weight = 0.6, r.type = '寄生于'
        """, host_name=host, pathogen_name=pathogen)
    print("   ✅ Done.")

    # ========================================================================
    # 3. Delete Orphaned Vector
    # ========================================================================
    print("\n🔧 3. Deleting Orphaned Vector...")
    orphaned_vector = '李䮲結量'
    print(f"   - Deleting node: {orphaned_vector}")
    session.run("MATCH (v:媒介 {name: $vector_name}) DETACH DELETE v", vector_name=orphaned_vector)
    print("   ✅ Done.")

    # ========================================================================
    # 4. Reclassify "Other" Entities
    # ========================================================================
    print("\n🔧 4. Reclassifying 'Other' Entities...")
    entities_to_reclassify = [
        '林业', '元宝槭林', '古树名木', '树木落叶情况', '林分尺度', '温带落叶阔叶林'
    ]
    
    for entity in entities_to_reclassify:
        print(f"   - Updating '{entity}': Other -> 寄主")
        session.run("""
            MATCH (n:其他 {name: $entity_name})
            SET n.category = '寄主'
            REMOVE n:其他
            SET n:寄主
        """, entity_name=entity)
    print("   ✅ Done.")

    # ========================================================================
    # 5. Verification
    # ========================================================================
    print("\n" + "="*80)
    print("Verification of Fixes")
    print("="*80)

    # Check if invalid relationship exists
    result = session.run("MATCH (p:病原体)-[r:防治]->(t:防治) RETURN count(r) as count").single()['count']
    print(f"  [Check 1] Invalid (Pathogen)-[:防治]->(Control) relationships: {result} {'✅' if result == 0 else '❌'}")

    # Check if new relationship exists
    result = session.run("MATCH (t:防治)-[r:防治]->(v:媒介) WHERE t.name='诱捕器' RETURN count(r) as count").single()['count']
    print(f"  [Check 1] Correct (Trap)-[:防治]->(Vector) relationship exists: {result > 0} {'✅' if result > 0 else '❌'}")

    # Check for orphaned hosts
    result = session.run("MATCH (h:寄主) WHERE NOT (h)--(:病原体) AND NOT (h)--(:媒介) RETURN count(h) as count").single()['count']
    print(f"  [Check 2] Orphaned hosts remaining: {result} {'✅' if result == 0 else '❌'}")

    # Check for orphaned vector
    result = session.run("MATCH (v:媒介 {name: '李䮲結量'}) RETURN count(v) as count").single()['count']
    print(f"  [Check 3] Orphaned vector '{orphaned_vector}' deleted: {result == 0} {'✅' if result == 0 else '❌'}")

    # Check reclassification
    result = session.run("MATCH (n:寄主) WHERE n.name IN $entities RETURN count(n) as count", entities=entities_to_reclassify).single()['count']
    print(f"  [Check 4] Reclassified entities now in '寄主' category: {result}/{len(entities_to_reclassify)} {'✅' if result == len(entities_to_reclassify) else '❌'}")

driver.close()

print("\n" + "="*80)
print("✓ Semantic Fixes Applied Successfully!")
print("="*80)
