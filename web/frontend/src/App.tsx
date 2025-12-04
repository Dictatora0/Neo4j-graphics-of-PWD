import { useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { BarChart3, X } from "lucide-react";
import GraphViewer from "./components/GraphViewer";
import SearchBar from "./components/SearchBar";
import FilterPanel, { type FilterState } from "./components/FilterPanel";
import StatsPanel from "./components/StatsPanel";
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
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<FilterState | null>(null);
  const [showStatsPanel, setShowStatsPanel] = useState(false);

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
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => statsAPI.getStatistics(),
  });

  const handleNodeClick = (node: Node) => {
    setSelectedNode(node);
    console.log("Selected node:", node);
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
  };

  const handleFilter = (newFilters: FilterState) => {
    setFilters(newFilters);
  };

  const handleResetFilter = () => {
    setFilters(null);
  };

  // 计算筛选后的节点 IDs
  const filteredNodeIds = filters
    ? graphData?.nodes
        .filter((node) => {
          const categoryMatch =
            filters.categories.length === 0 ||
            filters.categories.includes(node.category);
          const importanceMatch =
            !node.importance ||
            (node.importance >= filters.minImportance &&
              node.importance <= filters.maxImportance);
          return categoryMatch && importanceMatch;
        })
        .map((n) => n.id)
    : undefined;

  // 获取所有类别
  const categories = graphData
    ? Array.from(new Set(graphData.nodes.map((n) => n.category)))
    : [];

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
    <div className="flex flex-col h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-gray-50">
      {/* 顶部导航栏 */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                松材线虫病知识图谱
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                PWD Knowledge Graph Visualization System
              </p>
            </div>
            <div className="flex items-center gap-4">
              {stats && (
                <div className="flex gap-6 text-sm bg-gradient-to-r from-blue-50 to-purple-50 px-4 py-2 rounded-lg">
                  <div>
                    <span className="text-gray-600">节点:</span>
                    <span className="ml-2 font-bold text-blue-600">
                      {stats.total_nodes}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">关系:</span>
                    <span className="ml-2 font-bold text-purple-600">
                      {stats.total_edges}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">平均度数:</span>
                    <span className="ml-2 font-bold text-green-600">
                      {stats.avg_degree?.toFixed(2) || "N/A"}
                    </span>
                  </div>
                </div>
              )}
              <button
                onClick={() => setShowStatsPanel(!showStatsPanel)}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all shadow-md hover:shadow-lg"
              >
                <BarChart3 className="w-4 h-4" />
                <span>统计面板</span>
              </button>
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

      {/* 工具栏 */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 px-6 py-3">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <SearchBar
              onSearch={handleSearch}
              onClear={handleClearSearch}
              placeholder="搜索节点名称..."
            />
          </div>
          <FilterPanel
            categories={categories}
            onFilter={handleFilter}
            onReset={handleResetFilter}
          />
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧统计面板 */}
        {showStatsPanel && graphData && (
          <aside className="w-96 bg-white/80 backdrop-blur-md border-r border-gray-200/50 p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">数据统计</h2>
              <button
                onClick={() => setShowStatsPanel(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <StatsPanel data={graphData} stats={stats} />
          </aside>
        )}

        {/* 图谱可视化 */}
        <main className="flex-1 p-4">
          {graphData && (
            <GraphViewer
              data={graphData}
              onNodeClick={handleNodeClick}
              searchQuery={searchQuery}
              filteredNodeIds={filteredNodeIds}
              className="w-full h-full"
            />
          )}
        </main>

        {/* 右侧边栏 - 节点详情 */}
        {selectedNode && (
          <aside className="w-80 bg-white/80 backdrop-blur-md border-l border-gray-200/50 p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">节点详情</h2>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
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
                  <span className="inline-block px-3 py-1 bg-gradient-to-r from-blue-100 to-purple-100 text-blue-700 rounded-full text-sm font-medium">
                    {selectedNode.category}
                  </span>
                </p>
              </div>
              {selectedNode.importance && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    重要性
                  </label>
                  <div className="mt-2 flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <svg
                        key={star}
                        className={`w-5 h-5 ${
                          star <= selectedNode.importance!
                            ? "text-yellow-400 fill-yellow-400"
                            : "text-gray-300"
                        }`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                    <span className="ml-2 text-sm text-gray-600">
                      {selectedNode.importance}/5
                    </span>
                  </div>
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
