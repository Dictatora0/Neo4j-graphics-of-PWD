import matplotlib.pyplot as plt
import networkx as nx
from neo4j import GraphDatabase
import sys

def visualize_neo4j_graph(uri="bolt://localhost:7687", user="neo4j", password="", query="MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100"):
    """
    Connect to Neo4j database, execute query, and visualize the graph.
    If connection fails, show sample graph.

    Args:
        uri (str): Neo4j database URI
        user (str): Username
        password (str): Password
        query (str): Cypher query
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))

        def get_graph_data(tx):
            result = tx.run(query)
            nodes = {}
            edges = []
            for record in result:
                n = record['n']
                r = record['r']
                m = record['m']

                # Add nodes
                if n.id not in nodes:
                    nodes[n.id] = {'label': list(n.labels)[0] if n.labels else 'Node', 'properties': dict(n)}
                if m.id not in nodes:
                    nodes[m.id] = {'label': list(m.labels)[0] if m.labels else 'Node', 'properties': dict(m)}

                # Add edge
                edges.append((n.id, m.id, {'type': r.type, 'properties': dict(r)}))

            return nodes, edges

        with driver.session() as session:
            nodes, edges = session.read_transaction(get_graph_data)

        if not nodes:
            print("No data found from query. Showing sample graph.")
            create_sample_graph()
            return

    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        print("Showing sample graph instead.")
        create_sample_graph()
        return

    # Create NetworkX graph
    G = nx.DiGraph()
    for node_id, node_data in nodes.items():
        G.add_node(node_id, label=node_data['label'], **node_data['properties'])
    for edge in edges:
        G.add_edge(edge[0], edge[1], **edge[2])

    # Visualize
    visualize_graph(G)

    driver.close()

def create_sample_graph():
    """Create a sample graph for demonstration."""
    G = nx.DiGraph()
    
    # Add sample nodes
    nodes_data = {
        1: {'label': 'Person', 'name': 'Alice'},
        2: {'label': 'Person', 'name': 'Bob'},
        3: {'label': 'Movie', 'title': 'The Matrix'},
        4: {'label': 'Person', 'name': 'Charlie'},
    }
    
    for node_id, data in nodes_data.items():
        G.add_node(node_id, **data)
    
    # Add sample edges
    edges_data = [
        (1, 2, {'type': 'KNOWS'}),
        (2, 3, {'type': 'ACTED_IN'}),
        (1, 3, {'type': 'LIKES'}),
        (4, 1, {'type': 'FRIEND_OF'}),
    ]
    
    for u, v, data in edges_data:
        G.add_edge(u, v, **data)
    
    visualize_graph(G)

def visualize_graph(G):
    """Visualize the graph using matplotlib."""
    pos = nx.spring_layout(G)
    labels = {node: data.get('label', 'Node') for node, data in G.nodes(data=True)}
    edge_labels = {(u, v): data.get('type', '') for u, v, data in G.edges(data=True)}

    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, with_labels=True, labels=labels, node_color='lightblue', node_size=500, font_size=8, font_weight='bold')
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6)
    plt.title("Neo4j Database Graph Visualization")
    plt.axis('off')
    plt.show()

if __name__ == "__main__":
    # Default values
    URI = "bolt://localhost:7687"
    USER = "neo4j"
    PASSWORD = ""
    QUERY = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50"

    # Allow command line arguments
    if len(sys.argv) > 1:
        URI = sys.argv[1]
    if len(sys.argv) > 2:
        USER = sys.argv[2]
    if len(sys.argv) > 3:
        PASSWORD = sys.argv[3]
    if len(sys.argv) > 4:
        QUERY = sys.argv[4]

    visualize_neo4j_graph(URI, USER, PASSWORD, QUERY)
