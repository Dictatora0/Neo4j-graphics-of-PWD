/**
 * 图谱可视化组件
 * 使用 Cytoscape.js 实现交互式知识图谱
 */
import { useEffect, useRef, useState } from "react";
import cytoscape, { type Core, type NodeSingular } from "cytoscape";
import { Download, Maximize2, ZoomIn, ZoomOut, Layers } from "lucide-react";
import type { GraphData, Node } from "../types/graph";

interface GraphViewerProps {
  data: GraphData;
  onNodeClick?: (node: Node) => void;
  searchQuery?: string;
  filteredNodeIds?: string[];
  className?: string;
}

// 节点类别颜色映射 - 匹配Neo4j标签和数据库颜色
const NODE_COLORS: Record<string, string> = {
  Pathogen: "#FF6B6B", // 红色 - 病原
  Disease: "#FF8C42", // 橙色 - 疾病
  Vector: "#4ECDC4", // 青色 - 媒介
  Host: "#95E1D3", // 浅绿色 - 寄主
  Control: "#A8E6CF", // 绿色 - 防治
  Technology: "#95B8D1", // 蓝灰色 - 技术
  Location: "#FFE66D", // 黄色 - 地点
  Environment: "#87CEEB", // 天蓝色 - 环境
  Other: "#C7CEEA", // 淡紫色 - 其他
  default: "#6b7280", // 灰色 - 默认
};

const LAYOUTS = [
  { name: "cose", label: "力导向" },
  { name: "circle", label: "环形" },
  { name: "grid", label: "网格" },
  { name: "concentric", label: "同心圆" },
  { name: "breadthfirst", label: "层次" },
];

export default function GraphViewer({
  data,
  onNodeClick,
  searchQuery,
  filteredNodeIds,
  className = "",
}: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [currentLayout, setCurrentLayout] = useState("cose");
  const [showLayoutMenu, setShowLayoutMenu] = useState(false);

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
            "background-color": (ele: NodeSingular) => {
              const category = ele.data("category") as string;
              return NODE_COLORS[category] || NODE_COLORS.default;
            },
            label: "data(label)",
            width: (ele: NodeSingular) => {
              const degree = ele.data("total_degree") || 1;
              return Math.max(30, Math.min(80, degree * 3));
            },
            height: (ele: NodeSingular) => {
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
        {
          selector: "node.highlighted",
          style: {
            "border-width": 4,
            "border-color": "#f59e0b",
            "z-index": 999,
          },
        },
        {
          selector: "node.neighbor",
          style: {
            "border-width": 3,
            "border-color": "#10b981",
            opacity: 1,
          },
        },
        {
          selector: "node.searched",
          style: {
            "border-width": 5,
            "border-color": "#ef4444",
            "z-index": 1000,
          },
        },
        {
          selector: "node.filtered",
          style: {
            opacity: 0.3,
          },
        },
        {
          selector: "edge.neighbor",
          style: {
            "line-color": "#10b981",
            "target-arrow-color": "#10b981",
            width: 3,
            opacity: 1,
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

      // 高亮邻居节点
      cy.elements().removeClass("highlighted neighbor");
      node.addClass("highlighted");
      node.neighborhood().addClass("neighbor");

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

    // 点击空白处取消高亮
    cy.on("tap", (event) => {
      if (event.target === cy) {
        cy.elements().removeClass("highlighted neighbor");
      }
    });

    // 清理
    return () => {
      cy.destroy();
    };
  }, [data, onNodeClick]);

  // 搜索功能
  useEffect(() => {
    if (!cyRef.current) return;

    cyRef.current.elements().removeClass("searched");

    if (searchQuery && searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      cyRef.current.nodes().forEach((node) => {
        const label = node.data("label").toLowerCase();
        if (label.includes(query)) {
          node.addClass("searched");
        }
      });
    }
  }, [searchQuery]);

  // 筛选功能
  useEffect(() => {
    if (!cyRef.current) return;

    cyRef.current.nodes().removeClass("filtered");

    if (filteredNodeIds && filteredNodeIds.length > 0) {
      cyRef.current.nodes().forEach((node) => {
        if (!filteredNodeIds.includes(node.id())) {
          node.addClass("filtered");
        }
      });
    }
  }, [filteredNodeIds]);

  // 切换布局
  const handleLayoutChange = (layoutName: string) => {
    if (!cyRef.current) return;

    setCurrentLayout(layoutName);
    setShowLayoutMenu(false);

    const layout = cyRef.current.layout({
      name: layoutName as any,
      padding: 30,
      animate: true,
      animationDuration: 500,
    } as any);

    layout.run();
    setTimeout(() => cyRef.current?.fit(), 600);
  };

  // 导出图片
  const handleExport = () => {
    if (!cyRef.current) return;

    const png = cyRef.current.png({
      scale: 2,
      full: true,
      bg: "#ffffff",
    });

    const link = document.createElement("a");
    link.download = `knowledge-graph-${Date.now()}.png`;
    link.href = png;
    link.click();
  };

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
          <Maximize2 className="w-5 h-5" />
        </button>

        <button
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
          className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
          title="放大"
        >
          <ZoomIn className="w-5 h-5" />
        </button>

        <button
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.2)}
          className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
          title="缩小"
        >
          <ZoomOut className="w-5 h-5" />
        </button>

        <button
          onClick={handleExport}
          className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
          title="导出图片"
        >
          <Download className="w-5 h-5" />
        </button>

        <div className="relative">
          <button
            onClick={() => setShowLayoutMenu(!showLayoutMenu)}
            className="bg-white hover:bg-gray-100 p-2 rounded-lg shadow-md transition-colors"
            title="切换布局"
          >
            <Layers className="w-5 h-5" />
          </button>

          {showLayoutMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowLayoutMenu(false)}
              />
              <div className="absolute right-full mr-2 top-0 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-20 whitespace-nowrap">
                {LAYOUTS.map((layout) => (
                  <button
                    key={layout.name}
                    onClick={() => handleLayoutChange(layout.name)}
                    className={`w-full px-4 py-2 text-left hover:bg-gray-100 transition-colors ${
                      currentLayout === layout.name
                        ? "bg-blue-50 text-blue-600"
                        : ""
                    }`}
                  >
                    {layout.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
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
