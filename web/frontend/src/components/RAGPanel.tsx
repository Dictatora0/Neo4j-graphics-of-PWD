import { useState } from "react";
import {
  MessageSquare,
  Send,
  Loader2,
  Lightbulb,
  CheckCircle,
} from "lucide-react";

interface RAGPanelProps {
  onHighlightNodes?: (nodeIds: string[]) => void;
}

interface SearchResult {
  answer: string;
  relevant_nodes: Array<{
    id: string;
    name: string;
    category: string;
    similarity: number;
  }>;
  relevant_edges: Array<{
    source: string;
    target: string;
    type: string;
  }>;
  confidence: number;
  sources: string[];
}

export default function RAGPanel({ onHighlightNodes }: RAGPanelProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exampleQueries = [
    "松材线虫病的主要传播媒介是什么？",
    "如何防治松材线虫病？",
    "松材线虫病有哪些症状？",
    "哪些松树品种容易感染松材线虫病？",
  ];

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(
        "http://localhost:8000/api/rag/local-search",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: query.trim(),
            top_k: 5,
            expand_depth: 1,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "查询失败");
      }

      const data: SearchResult = await response.json();
      setResult(data);

      // 高亮相关节点
      if (onHighlightNodes && data.relevant_nodes.length > 0) {
        const nodeIds = data.relevant_nodes.map((n) => n.id);
        onHighlightNodes(nodeIds);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "查询失败");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white/80 backdrop-blur-md">
      {/* 标题 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">知识问答</h3>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          基于 GraphRAG 的智能问答系统
        </p>
      </div>

      {/* 输入区域 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex gap-2">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="请输入您的问题..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={2}
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* 示例问题 */}
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
            <Lightbulb className="w-3 h-3" />
            示例问题：
          </p>
          <div className="flex flex-wrap gap-2">
            {exampleQueries.map((example, index) => (
              <button
                key={index}
                onClick={() => setQuery(example)}
                className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 结果区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {result && (
          <>
            {/* 答案 */}
            <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-gray-900">系统回答</h4>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-500">
                      置信度: {(result.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {result.answer}
              </p>
            </div>

            {/* 相关概念 */}
            {result.relevant_nodes.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2 text-sm">
                  相关概念 ({result.relevant_nodes.length})
                </h4>
                <div className="space-y-2">
                  {result.relevant_nodes.map((node, index) => (
                    <div
                      key={index}
                      className="p-2 bg-gray-50 rounded border border-gray-200"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm text-gray-900">
                          {node.name}
                        </span>
                        <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                          {node.category}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-blue-600 h-1.5 rounded-full"
                            style={{ width: `${node.similarity * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">
                          {(node.similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 信息来源 */}
            {result.sources.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2 text-sm">
                  信息来源
                </h4>
                <div className="flex flex-wrap gap-1">
                  {result.sources.map((source, index) => (
                    <span
                      key={index}
                      className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded"
                    >
                      {source}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {!result && !error && !loading && (
          <div className="text-center text-gray-400 py-8">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">输入问题开始智能问答</p>
          </div>
        )}
      </div>
    </div>
  );
}
