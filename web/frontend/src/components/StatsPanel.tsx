import { BarChart3, PieChart, TrendingUp, Network } from "lucide-react";
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import type { GraphData, StatsData } from "../types/graph";

interface StatsPanelProps {
  data: GraphData;
  stats?: StatsData;
}

const COLORS = [
  "#FF6B6B",
  "#4ECDC4",
  "#95E1D3",
  "#FFE66D",
  "#A8E6CF",
  "#95B8D1",
  "#FF8C42",
  "#87CEEB",
];

export default function StatsPanel({ data, stats }: StatsPanelProps) {
  // 计算类别分布
  const categoryData = data.nodes.reduce((acc, node) => {
    const category = node.category || "Other";
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const pieData = Object.entries(categoryData).map(([name, value]) => ({
    name,
    value,
  }));

  const barData = Object.entries(categoryData).map(([name, value]) => ({
    category: name,
    count: value,
  }));

  // 计算重要性分布
  const importanceData = [1, 2, 3, 4, 5].map((level) => ({
    level: `${level}星`,
    count: data.nodes.filter((n) => n.importance === level).length,
  }));

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-4 text-white">
          <div className="flex items-center justify-between mb-2">
            <Network className="w-8 h-8 opacity-80" />
            <span className="text-2xl font-bold">
              {stats?.total_nodes || data.nodes.length}
            </span>
          </div>
          <p className="text-sm opacity-90">总节点数</p>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg p-4 text-white">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="w-8 h-8 opacity-80" />
            <span className="text-2xl font-bold">
              {stats?.total_edges || data.edges.length}
            </span>
          </div>
          <p className="text-sm opacity-90">总关系数</p>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-4 text-white">
          <div className="flex items-center justify-between mb-2">
            <BarChart3 className="w-8 h-8 opacity-80" />
            <span className="text-2xl font-bold">
              {stats?.avg_degree?.toFixed(2) || "N/A"}
            </span>
          </div>
          <p className="text-sm opacity-90">平均度数</p>
        </div>

        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg p-4 text-white">
          <div className="flex items-center justify-between mb-2">
            <PieChart className="w-8 h-8 opacity-80" />
            <span className="text-2xl font-bold">
              {Object.keys(categoryData).length}
            </span>
          </div>
          <p className="text-sm opacity-90">节点类别</p>
        </div>
      </div>

      {/* 类别分布饼图 */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">类别分布</h3>
        <ResponsiveContainer width="100%" height={200}>
          <RechartsPie>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) =>
                `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`
              }
              outerRadius={70}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip />
          </RechartsPie>
        </ResponsiveContainer>
      </div>

      {/* 类别统计柱状图 */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          节点数量统计
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="category"
              angle={-45}
              textAnchor="end"
              height={80}
              tick={{ fontSize: 11 }}
            />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 重要性分布 */}
      <div className="bg-white rounded-lg p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">重要性分布</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={importanceData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="level" type="category" />
            <Tooltip />
            <Bar dataKey="count" fill="#10b981" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
