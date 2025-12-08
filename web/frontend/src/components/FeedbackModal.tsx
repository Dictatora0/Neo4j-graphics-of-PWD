import { useState } from "react";
import { X, AlertCircle, CheckCircle2 } from "lucide-react";
import { feedbackAPI } from "../services/api";

export type FeedbackType =
  | "relation_direction"
  | "relation_type"
  | "entity_merge"
  | "missing_relation";

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: FeedbackType;
  data: {
    sourceNode?: string;
    targetNode?: string;
    relationType?: string;
    entityName?: string;
  };
}

export default function FeedbackModal({
  isOpen,
  onClose,
  type,
  data,
}: FeedbackModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    correctedType: "",
    suggestedCanonical: "",
    missingTarget: "",
    missingType: "",
    comment: "",
  });

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const payload = {
        user_id: "web_user", // 可以改为实际用户ID
        comment: formData.comment,
        timestamp: new Date().toISOString(),
      };

      switch (type) {
        case "relation_direction":
          await feedbackAPI.submitRelationDirectionError({
            ...payload,
            source: data.sourceNode!,
            target: data.targetNode!,
            relation_type: data.relationType!,
          });
          break;

        case "relation_type":
          await feedbackAPI.submitRelationTypeError({
            ...payload,
            source: data.sourceNode!,
            target: data.targetNode!,
            incorrect_type: data.relationType!,
            correct_type: formData.correctedType,
          });
          break;

        case "entity_merge":
          await feedbackAPI.submitEntityMerge({
            ...payload,
            entity1: data.entityName!,
            entity2: formData.suggestedCanonical,
          });
          break;

        case "missing_relation":
          await feedbackAPI.submitMissingRelation({
            ...payload,
            source: data.sourceNode!,
            target: formData.missingTarget,
            relation_type: formData.missingType,
          });
          break;
      }

      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
        setFormData({
          correctedType: "",
          suggestedCanonical: "",
          missingTarget: "",
          missingType: "",
          comment: "",
        });
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const getTitle = () => {
    switch (type) {
      case "relation_direction":
        return "关系方向纠错";
      case "relation_type":
        return "关系类型纠错";
      case "entity_merge":
        return "实体合并建议";
      case "missing_relation":
        return "报告缺失关系";
      default:
        return "反馈";
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">{getTitle()}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center">
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-lg font-medium text-gray-900">提交成功！</p>
            <p className="text-sm text-gray-500 mt-2">感谢您的反馈</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            {/* 当前信息显示 */}
            <div className="bg-gray-50 p-3 rounded text-sm">
              {data.sourceNode && (
                <p>
                  <span className="font-medium">来源：</span>
                  {data.sourceNode}
                </p>
              )}
              {data.targetNode && (
                <p>
                  <span className="font-medium">目标：</span>
                  {data.targetNode}
                </p>
              )}
              {data.relationType && (
                <p>
                  <span className="font-medium">关系类型：</span>
                  {data.relationType}
                </p>
              )}
              {data.entityName && (
                <p>
                  <span className="font-medium">实体：</span>
                  {data.entityName}
                </p>
              )}
            </div>

            {/* 根据类型显示不同表单 */}
            {type === "relation_type" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  正确的关系类型
                </label>
                <input
                  type="text"
                  value={formData.correctedType}
                  onChange={(e) =>
                    setFormData({ ...formData, correctedType: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="例如：防治、感染、传播..."
                  required
                />
              </div>
            )}

            {type === "entity_merge" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  标准名称或合并目标
                </label>
                <input
                  type="text"
                  value={formData.suggestedCanonical}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      suggestedCanonical: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="例如：Bursaphelenchus xylophilus"
                  required
                />
              </div>
            )}

            {type === "missing_relation" && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    目标实体
                  </label>
                  <input
                    type="text"
                    value={formData.missingTarget}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        missingTarget: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="缺失关系指向的实体"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    关系类型
                  </label>
                  <input
                    type="text"
                    value={formData.missingType}
                    onChange={(e) =>
                      setFormData({ ...formData, missingType: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="例如：感染、传播..."
                    required
                  />
                </div>
              </>
            )}

            {/* 备注 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                备注说明（可选）
              </label>
              <textarea
                value={formData.comment}
                onChange={(e) =>
                  setFormData({ ...formData, comment: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="请描述您发现的问题或建议..."
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "提交中..." : "提交"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
