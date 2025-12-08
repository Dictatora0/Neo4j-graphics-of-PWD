import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Image as ImageIcon, X, ZoomIn } from "lucide-react";
import { multimodalAPI } from "../services/api";

interface ImageGalleryProps {
  conceptName: string;
}

interface ConceptImage {
  path: string;
  caption?: string;
  source_pdf?: string;
  page_num?: number;
}

export default function ImageGallery({ conceptName }: ImageGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<ConceptImage | null>(null);

  const {
    data: images,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["concept-images", conceptName],
    queryFn: () => multimodalAPI.getConceptImages(conceptName),
    enabled: !!conceptName,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !images || images.length === 0) {
    return null; // 没有图片时不显示
  }

  return (
    <>
      <div className="mt-4">
        <div className="flex items-center gap-2 mb-2">
          <ImageIcon className="w-4 h-4 text-gray-500" />
          <label className="text-sm font-medium text-gray-700">
            相关图片 ({images.length})
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {images.slice(0, 4).map((image: ConceptImage, index: number) => (
            <div
              key={index}
              className="relative group cursor-pointer"
              onClick={() => setSelectedImage(image)}
            >
              <img
                src={multimodalAPI.getImageUrl(image.path)}
                alt={image.caption || `图片 ${index + 1}`}
                className="w-full h-24 object-cover rounded border border-gray-200 group-hover:border-blue-400 transition-colors"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23e5e7eb' width='100' height='100'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af'%3E无法加载%3C/text%3E%3C/svg%3E";
                }}
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                <ZoomIn className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
          ))}
        </div>

        {images.length > 4 && (
          <p className="text-xs text-gray-500 mt-2">
            还有 {images.length - 4} 张图片...
          </p>
        )}
      </div>

      {/* 图片查看器 */}
      {selectedImage && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300"
            >
              <X className="w-6 h-6" />
            </button>

            <img
              src={multimodalAPI.getImageUrl(selectedImage.path)}
              alt={selectedImage.caption || "图片"}
              className="max-w-full max-h-[80vh] rounded"
            />

            {selectedImage.caption && (
              <div className="mt-4 bg-white p-4 rounded">
                <p className="text-sm text-gray-700">{selectedImage.caption}</p>
                {selectedImage.source_pdf && (
                  <p className="text-xs text-gray-500 mt-2">
                    来源：{selectedImage.source_pdf}
                    {selectedImage.page_num &&
                      ` (第 ${selectedImage.page_num} 页)`}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
