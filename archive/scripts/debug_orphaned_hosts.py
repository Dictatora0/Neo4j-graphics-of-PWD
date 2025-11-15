#!/usr/bin/env python3
"""
Debug script to identify remaining orphaned hosts.
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("Debugging Orphaned Hosts")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 1. List all current hosts
    # ========================================================================
    print("\n📋 Listing all current nodes with label '寄主'...")
    result = session.run("MATCH (h:寄主) RETURN h.name as name ORDER BY h.name")
    all_hosts = [record['name'] for record in result]
    print(f"   Found {len(all_hosts)} hosts:")
    for i in range(0, len(all_hosts), 3):
        print("     - " + " | ".join(all_hosts[i:i+3]))

    # ========================================================================
    # 2. Identify orphaned hosts
    # ========================================================================
    print("\n🔍 Identifying which hosts are orphaned...")
    result = session.run("""
        MATCH (h:寄主)
        WHERE NOT (h)--(:病原体) AND NOT (h)--(:媒介)
        RETURN h.name as name
    """)
    
    orphaned_hosts = [record['name'] for record in result]
    
    if not orphaned_hosts:
        print("   ✅ No orphaned hosts found.")
    else:
        print(f"   ❌ Found {len(orphaned_hosts)} orphaned hosts:")
        for host in orphaned_hosts:
            print(f"     - {host}")

    # ========================================================================
    # 3. Analyze connections for previously reclassified hosts
    # ========================================================================
    print("\n🔬 Analyzing connections for newly classified hosts...")
    reclassified_hosts = [
        '林业', '元宝槭林', '古树名木', '树木落叶情况', '林分尺度', '温带落叶阔叶林'
    ]

    for host in reclassified_hosts:
        if host in all_hosts:
            result = session.run("""
                MATCH (h:寄主 {name: $host_name})
                RETURN size((h)--()) as degree
            """, host_name=host).single()
            degree = result['degree'] if result else 0
            status = "(Orphaned)" if host in orphaned_hosts else f"({degree} connections)"
            print(f"   - {host}: {status}")

driver.close()

print("\n" + "="*80)
print("✓ Debugging complete.")
print("="*80)
