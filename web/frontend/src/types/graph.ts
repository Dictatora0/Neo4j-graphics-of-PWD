/**
 * 知识图谱类型定义
 */

export interface Node {
  id: string;
  name: string;
  category: string;
  importance?: number;
  total_degree?: number;
  properties?: Record<string, any>;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  weight?: number;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: Node[];
  edges: Edge[];
  total_nodes: number;
  total_edges: number;
}

export interface NodeDetail {
  node: Node;
  neighbors: Node[];
  relationships: Edge[];
}

export interface SearchResult {
  nodes: Node[];
  total: number;
  query: string;
}

export interface StatsData {
  total_nodes: number;
  total_edges: number;
  avg_degree?: number;
  node_distribution: Record<string, number>;
  edge_distribution: Record<string, number>;
  top_nodes: Node[];
  density?: number;
}

export interface PathResult {
  paths: string[][];
  total_paths: number;
}

// Cytoscape.js 元素类型
export interface CytoscapeNode {
  data: {
    id: string;
    label: string;
    category: string;
    importance?: number;
    total_degree?: number;
  };
}

export interface CytoscapeEdge {
  data: {
    id: string;
    source: string;
    target: string;
    label: string;
    weight?: number;
  };
}

export type CytoscapeElement = CytoscapeNode | CytoscapeEdge;
