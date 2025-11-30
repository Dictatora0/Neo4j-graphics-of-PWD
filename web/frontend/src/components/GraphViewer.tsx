/**
 * 图谱可视化组件
 * 使用 Cytoscape.js 实现交互式知识图谱
 */
import { useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
import type { GraphData, Node } from "../types/graph";

interface GraphViewerProps {
  data: GraphData;
  onNodeClick?: (node: Node) => void;
  className?: string;
}

// 节点类别颜色映射
const NODE_COLORS: Record<string, string> = {
  pathogen: "#ef4444", // 红色 - 病原
  host: "#10b981", // 绿色 - 寄主
  vector: "#f59e0b", // 橙色 - 媒介
  symptom: "#8b5cf6", // 紫色 - 症状
  treatment: "#3b82f6", // 蓝色 - 防治
  environment: "#06b6d4", // 青色 - 环境
  location: "#ec4899", // 粉色 - 地点
  mechanism: "#6366f1", // 靛蓝 - 机制
  compound: "#84cc16", // 黄绿 - 化合物
  default: "#6b7280", // 灰色 - 默认
};

export default function GraphViewer({
  data,
  onNodeClick,
  className = "",
}: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current || !data.nodes.length) return;

    // 转换数据为 Cytoscape 格式
    const elements = [
      ...data.nodes.map((node) => ({
        group: "nodes" as const,
        data: {
          id: node.id,
          label: node.name,
          category: node.category,
          importance: node.importance,
          total_degree: node.total_degree,
        },
      })),
      ...data.edges.map((edge) => ({
        group: "edges" as const,
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relationship,
          weight: edge.weight,
        },
      })),
    ];

    // 初始化 Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele) => {
              const category = ele.data("category") as string;
              return NODE_COLORS[category] || NODE_COLORS.default;
            },
            label: "data(label)",
            width: (ele) => {
              const degree = ele.data("total_degree") || 1;
              return Math.max(30, Math.min(80, degree * 3));
            },
            height: (ele) => {
              const degree = ele.data("total_degree") || 1;
              return Math.max(30, Math.min(80, degree * 3));
            },
            "font-size": "12px",
            "text-valign": "center",
            "text-halign": "center",
            color: "#333",
            "text-outline-width": 2,
            "text-outline-color": "#fff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#cbd5e1",
            "target-arrow-color": "#cbd5e1",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "10px",
            "text-rotation": "autorotate",
            "text-margin-y": -10,
            color: "#64748b",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 4,
            "border-color": "#2563eb",
          },
        },
      ],
      layout: {
        name: "cose",
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      },
      minZoom: 0.1,
      maxZoom: 3,
    });

    cyRef.current = cy;

    // 节点点击事件
    cy.on("tap", "node", (event) => {
      const node = event.target;
      const nodeData = node.data();

      if (onNodeClick) {
        onNodeClick({
          id: nodeData.id,
          name: nodeData.label,
          category: nodeData.category,
          importance: nodeData.importance,
          total_degree: nodeData.total_degree,
        });
      }
    });

    // 清理
    return () => {
      cy.destroy();
    };
  }, [data, onNodeClick]);

  return (
    <div className={`relative w-full h-full ${className}`}>
      <div
        ref={containerRef}
        className="w-full h-full bg-white rounded-lg shadow-sm"
      />

      {/* 控制面板 */}
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        <button
          onClick={() => cyRef.current?.fit()}
          className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
          title="适应画布"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
            />
          </svg>
        </button>

        <button
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
          className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
          title="放大"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>

        <button
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.2)}
          className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
          title="缩小"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 12H4"
            />
          </svg>
        </button>
      </div>

      {/* 图例 */}
      <div className="absolute bottom-4 left-4 bg-white p-4 rounded-lg shadow-md max-w-xs">
        <h3 className="font-semibold text-sm mb-2">节点类别</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {Object.entries(NODE_COLORS)
            .filter(([key]) => key !== "default")
            .map(([key, color]) => (
              <div key={key} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="capitalize">{key}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
