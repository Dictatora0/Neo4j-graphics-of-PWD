import { Filter, X } from "lucide-react";
import { useState } from "react";

interface FilterPanelProps {
  categories: string[];
  onFilter: (filters: FilterState) => void;
  onReset: () => void;
}

export interface FilterState {
  categories: string[];
  minImportance: number;
  maxImportance: number;
}

export default function FilterPanel({
  categories,
  onFilter,
  onReset,
}: FilterPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [minImportance, setMinImportance] = useState(1);
  const [maxImportance, setMaxImportance] = useState(5);

  const handleCategoryToggle = (category: string) => {
    const newCategories = selectedCategories.includes(category)
      ? selectedCategories.filter((c) => c !== category)
      : [...selectedCategories, category];
    setSelectedCategories(newCategories);
  };

  const handleApply = () => {
    onFilter({
      categories: selectedCategories,
      minImportance,
      maxImportance,
    });
  };

  const handleReset = () => {
    setSelectedCategories([]);
    setMinImportance(1);
    setMaxImportance(5);
    onReset();
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        <Filter className="w-4 h-4" />
        <span>筛选</span>
        {selectedCategories.length > 0 && (
          <span className="ml-1 px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full text-xs">
            {selectedCategories.length}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-20">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">筛选选项</h3>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* 类别筛选 */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  节点类别
                </label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {categories.map((category) => (
                    <label
                      key={category}
                      className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded"
                    >
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(category)}
                        onChange={() => handleCategoryToggle(category)}
                        className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                      />
                      <span className="text-sm">{category}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* 重要性筛选 */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  重要性范围
                </label>
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <input
                      type="number"
                      min="1"
                      max="5"
                      value={minImportance}
                      onChange={(e) => setMinImportance(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <span className="text-xs text-gray-500 mt-1 block">
                      最小值
                    </span>
                  </div>
                  <span className="text-gray-400">-</span>
                  <div className="flex-1">
                    <input
                      type="number"
                      min="1"
                      max="5"
                      value={maxImportance}
                      onChange={(e) => setMaxImportance(Number(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <span className="text-xs text-gray-500 mt-1 block">
                      最大值
                    </span>
                  </div>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2">
                <button
                  onClick={handleReset}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
                >
                  重置
                </button>
                <button
                  onClick={() => {
                    handleApply();
                    setIsOpen(false);
                  }}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
                >
                  应用
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
