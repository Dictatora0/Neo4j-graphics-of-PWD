import { useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import GraphViewer from "./components/GraphViewer";
import { graphAPI, statsAPI } from "./services/api";
import type { Node } from "./types/graph";

// 创建 QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function KnowledgeGraphApp() {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [limit, setLimit] = useState(50);
  const [showAll, setShowAll] = useState(false);

  // 获取图谱数据
  const {
    data: graphData,
    isLoading: graphLoading,
    error: graphError,
  } = useQuery({
    queryKey: ["graph", limit, showAll],
    queryFn: () => graphAPI.getGraph({ limit, exclude_other: !showAll }),
  });

  // 获取统计数据
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: () => statsAPI.getStatistics(),
  });

  const handleNodeClick = (node: Node) => {
    setSelectedNode(node);
    console.log("Selected node:", node);
  };

  if (graphLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载知识图谱...</p>
        </div>
      </div>
    );
  }

  if (graphError) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center text-red-600">
          <h2 className="text-xl font-semibold mb-2">加载失败</h2>
          <p>无法连接到后端API，请确保服务正在运行</p>
          <p className="text-sm mt-2">http://localhost:8000</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                松材线虫病知识图谱
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                PWD Knowledge Graph Visualization
              </p>
            </div>
            <div className="flex items-center gap-4">
              {stats && (
                <div className="flex gap-6 text-sm">
                  <div>
                    <span className="text-gray-500">节点:</span>
                    <span className="ml-2 font-semibold text-primary-600">
                      {stats.total_nodes}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">关系:</span>
                    <span className="ml-2 font-semibold text-primary-600">
                      {stats.total_edges}
                    </span>
                  </div>
                </div>
              )}
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={showAll}
                  onChange={(e) => setShowAll(e.target.checked)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span>显示所有节点</span>
              </label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value={20}>20 个节点</option>
                <option value={50}>50 个节点</option>
                <option value={100}>100 个节点</option>
                <option value={200}>200 个节点</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 图谱可视化 */}
        <main className="flex-1 p-4">
          {graphData && (
            <GraphViewer
              data={graphData}
              onNodeClick={handleNodeClick}
              className="w-full h-full"
            />
          )}
        </main>

        {/* 右侧边栏 - 节点详情 */}
        {selectedNode && (
          <aside className="w-80 bg-white border-l border-gray-200 p-6 overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">节点详情</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-500">
                  名称
                </label>
                <p className="mt-1 text-base font-medium">
                  {selectedNode.name}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">
                  类别
                </label>
                <p className="mt-1">
                  <span className="inline-block px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm">
                    {selectedNode.category}
                  </span>
                </p>
              </div>
              {selectedNode.importance && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    重要性
                  </label>
                  <p className="mt-1 text-base">
                    {selectedNode.importance} / 5
                  </p>
                </div>
              )}
              {selectedNode.total_degree && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    连接数
                  </label>
                  <p className="mt-1 text-base">{selectedNode.total_degree}</p>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <KnowledgeGraphApp />
    </QueryClientProvider>
  );
}

export default App;
