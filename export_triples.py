#!/usr/bin/env python3
"""
Export the entire Neo4j database to a triples CSV file.
"""
import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"
OUTPUT_FILE = "output/triples_export.csv"

print("="*80)
print("Exporting Knowledge Graph to Triples CSV")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

triples = []

with driver.session() as session:
    print("\nQuerying database...")
    result = session.run("""
        MATCH (n1)-[r]->(n2)
        RETURN n1.name AS node_1, r.type AS relationship, n2.name AS node_2, r.weight as weight
        ORDER BY node_1, relationship, node_2
    """)
    
    records = list(result)
    print(f"   Found {len(records)} relationships to export.")

    if records:
        # Convert to DataFrame
        df = pd.DataFrame([dict(record) for record in records])
        
        # Reorder columns for clarity
        df = df[['node_1', 'relationship', 'node_2', 'weight']]
        
        print(f"\nSaving to {OUTPUT_FILE}...")
        # Save to CSV with UTF-8 BOM encoding for Excel compatibility
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print("   Export complete.")
    else:
        print("   No relationships found in the database.")

driver.close()

print("\n" + "="*80)
print("Export finished.")
print("="*80)
print(f"\nThe exported file is located at: {OUTPUT_FILE}")
print("   You can now open this CSV file in Excel or any spreadsheet editor to review the triples.")
