/**
 * API 服务层
 */
import axios from "axios";
import type {
  GraphData,
  NodeDetail,
  SearchResult,
  StatsData,
  PathResult,
} from "../types/graph";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// 图谱API
export const graphAPI = {
  // 获取图谱数据
  async getGraph(params?: {
    limit?: number;
    node_type?: string;
    relation_type?: string;
  }): Promise<GraphData> {
    const response = await api.get<GraphData>("/api/graph/", { params });
    return response.data;
  },

  // 获取子图
  async getSubgraph(nodeName: string, depth: number = 1): Promise<GraphData> {
    const response = await api.get<GraphData>(
      `/api/graph/subgraph/${nodeName}`,
      {
        params: { depth },
      }
    );
    return response.data;
  },

  // 查找路径
  async findPath(
    source: string,
    target: string,
    maxLength: number = 5
  ): Promise<PathResult> {
    const response = await api.post<PathResult>("/api/graph/path", {
      source,
      target,
      max_length: maxLength,
    });
    return response.data;
  },
};

// 节点API
export const nodesAPI = {
  // 获取节点列表
  async listNodes(params?: {
    limit?: number;
    offset?: number;
    category?: string;
    min_importance?: number;
  }): Promise<any[]> {
    const response = await api.get("/api/nodes/", { params });
    return response.data;
  },

  // 获取节点详情
  async getNodeDetail(nodeId: string): Promise<NodeDetail> {
    const response = await api.get<NodeDetail>(`/api/nodes/${nodeId}`);
    return response.data;
  },

  // 获取节点邻居
  async getNodeNeighbors(
    nodeId: string,
    depth: number = 1
  ): Promise<GraphData> {
    const response = await api.get<GraphData>(
      `/api/nodes/${nodeId}/neighbors`,
      {
        params: { depth },
      }
    );
    return response.data;
  },
};

// 搜索API
export const searchAPI = {
  // 搜索节点
  async searchNodes(params: {
    q: string;
    category?: string;
    min_importance?: number;
    limit?: number;
  }): Promise<SearchResult> {
    const response = await api.get<SearchResult>("/api/search/", { params });
    return response.data;
  },

  // 获取搜索建议
  async getSuggestions(q: string, limit: number = 5): Promise<any[]> {
    const response = await api.get("/api/search/suggest", {
      params: { q, limit },
    });
    return response.data;
  },
};

// 统计API
export const statsAPI = {
  // 获取统计数据
  async getStatistics(): Promise<StatsData> {
    const response = await api.get<StatsData>("/api/stats/");
    return response.data;
  },

  // 获取节点分布
  async getNodeDistribution(): Promise<Record<string, number>> {
    const response = await api.get("/api/stats/distribution/nodes");
    return response.data;
  },

  // 获取关系分布
  async getEdgeDistribution(): Promise<Record<string, number>> {
    const response = await api.get("/api/stats/distribution/edges");
    return response.data;
  },

  // 获取核心节点
  async getTopNodes(limit: number = 10): Promise<any[]> {
    const response = await api.get("/api/stats/top-nodes", {
      params: { limit },
    });
    return response.data;
  },
};

export default api;
