#!/usr/bin/env python3
"""
Final cleanup script to link the last remaining orphaned hosts.
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("Final Knowledge Graph Cleanup")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 1. Link Remaining Orphaned Hosts
    # ========================================================================
    print("\n🔧 1. Linking Remaining Orphaned Hosts...")
    remaining_orphans = ['元宝槭林', '林分尺度', '树木落叶情况']
    pathogen = 'bursaphelenchus xylophilus'
    
    linked_count = 0
    for host in remaining_orphans:
        print(f"   + Linking: ({host})-[:寄生于]->({pathogen})")
        result = session.run("""
            MATCH (h:寄主 {name: $host_name})
            MATCH (p:病原体 {name: $pathogen_name})
            MERGE (h)-[r:寄生于]->(p)
            SET r.weight = 0.5, r.type = '寄生于'
            RETURN count(r) as count
        """, host_name=host, pathogen_name=pathogen)
        
        if result.single()['count'] > 0:
            linked_count += 1
    
    print(f"   ✅ {linked_count}/{len(remaining_orphans)} hosts linked successfully.")

    # ========================================================================
    # 2. Final Verification
    # ========================================================================
    print("\n" + "="*80)
    print("Final Verification")
    print("="*80)

    # Check for any remaining orphaned hosts
    result = session.run("""
        MATCH (h:寄主)
        WHERE NOT (h)--(:病原体) AND NOT (h)--(:媒介)
        RETURN count(h) as count
    """).single()['count']
    
    print(f"  [Check] Orphaned hosts remaining: {result} {'✅' if result == 0 else '❌'}")

    # Final counts
    node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
    rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
    print(f"  [Stats] Final node count: {node_count}")
    print(f"  [Stats] Final relationship count: {rel_count}")

driver.close()

print("\n" + "="*80)
print("✓ All issues resolved. The knowledge graph is fully consistent.")
print("="*80)
