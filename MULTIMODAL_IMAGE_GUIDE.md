# 📸 多模态图片提取功能指南

## 功能概述

v2.6.3 版本新增**多模态图片提取和描述生成**功能，可以从 PDF 文献中自动提取图片并使用视觉语言模型(VLM)生成专业描述，将图片知识融入知识图谱。

### 核心能力

- ✅ **自动图片提取**: 从每个 PDF 提取高质量图片（过滤小图标）
- ✅ **智能图片描述**: 使用 LLaVA VLM 生成领域专业描述
- ✅ **知识图谱融合**: 将图片描述无缝融入文本，供 LLM 提取概念

---

## 快速开始

### 1. 安装 VLM 模型

```bash
chmod +x setup_multimodal.sh
./setup_multimodal.sh
```

这将：

- 检查 Ollama 服务状态
- 下载 LLaVA 模型（约 4.7GB，首次运行）
- 测试 VLM 功能

**手动下载**（可选）：

```bash
ollama pull llava:7b
```

---

### 2. 配置启用

编辑`config/config.yaml`:

```yaml
pdf:
  # 图片描述配置
  enable_image_captions: true # 启用图片提取
  image_output_dir: ./output/pdf_images
  max_images_per_pdf: 20 # 每个PDF最多提取20张
  min_image_size: 300 # 最小尺寸300px（过滤小图标）

  # VLM模型配置
  caption_model: llava:7b # 轻量级VLM（推荐）
  caption_provider: ollama # 使用本地Ollama
  caption_prompt: "你是植物病理学专家。请描述图片中与松材线虫病、松树病害、昆虫媒介（天牛）、显微镜观察相关的内容。重点关注：病原体形态、病害症状、寄主植物、传播媒介。"
```

---

### 3. 运行 Pipeline

```bash
./start.sh
```

流程：

1. **Step 1**: 提取 PDF 文本
2. **Step 1.5**: 提取图片 + VLM 生成描述 ← **新增**
3. 图片描述融入文本
4. 文本分块
5. LLM 提取概念（包含图片知识）
6. 知识图谱构建

---

## 工作原理

### 图片提取流程

```
PDF文件
  ↓
[ImageExtractor]
  ├─ 扫描所有页面
  ├─ 过滤小图片 (< 300px)
  ├─ 保存到 output/pdf_images/
  └─ 限制每个PDF最多20张
  ↓
[VisionLanguageModel - LLaVA]
  ├─ 加载图片
  ├─ 使用领域Prompt
  └─ 生成专业描述
  ↓
[融合到文本]
  └─ 在PDF文本末尾添加"## 图片内容"章节
  ↓
[LLM提取概念]
  └─ 从文本+图片描述中提取知识三元组
```

### 图片描述示例

**原始图片**: 显微镜下的松材线虫

**VLM 生成描述**:

> **图 1**（第 3 页）：显微镜下观察到的松材线虫（_Bursaphelenchus xylophilus_）成虫形态。线虫呈线状，体长约 1mm，可见头部口针结构和卷曲的尾部。这是松材线虫病的病原体，通过松褐天牛传播。

### 知识融合格式

```markdown
[原始 PDF 文本...]

## 图片内容

以下是文献中的图片描述，包含重要的视觉信息：

**图 1**（第 3 页）：显微镜下观察到的松材线虫（_Bursaphelenchus xylophilus_）成虫形态...

**图 2**（第 5 页）：受松材线虫病侵染的马尾松针叶变褐症状...

**图 3**（第 7 页）：松褐天牛（_Monochamus alternatus_）成虫，体长约 2.5cm...
```

---

## 配置详解

### 图片提取参数

| 参数                    | 默认值                | 说明                           |
| ----------------------- | --------------------- | ------------------------------ |
| `enable_image_captions` | `false`               | 是否启用图片描述生成           |
| `image_output_dir`      | `./output/pdf_images` | 图片保存目录                   |
| `max_images_per_pdf`    | `20`                  | 每个 PDF 最多提取图片数        |
| `min_image_size`        | `300`                 | 最小图片尺寸（像素），过滤图标 |

### VLM 模型选择

| 模型          | 大小  | 优势              | 适用场景           |
| ------------- | ----- | ----------------- | ------------------ |
| `llava:7b`    | 4.7GB | ✅ 轻量级，速度快 | **推荐**：内存有限 |
| `llava:13b`   | 7.3GB | 更准确            | 高配置服务器       |
| `qwen2-vl:7b` | 4.9GB | 中文优化          | 中文 PDF 为主      |

### Prompt 优化

根据领域定制：

```yaml
# 病理学领域
caption_prompt: "描述图片中的病害症状、病原体、传播媒介..."

# 生态学领域
caption_prompt: "描述图片中的物种、生境、空间分布..."

# 材料学领域
caption_prompt: "描述图片中的材料结构、微观形态、测试结果..."
```

---

## 性能优化

### 内存管理

图片提取会增加内存占用：

```yaml
pdf:
  max_images_per_pdf: 15 # 减少图片数量
  min_image_size: 400 # 提高尺寸阈值
```

### 速度优化

VLM 推理较慢（~3 秒/图）：

```yaml
pdf:
  enable_image_captions: false # 首次运行可暂时关闭
```

建议：

- 首次运行先关闭图片功能，快速构建基础图谱
- 二次运行启用图片，增量补充视觉知识

### 并发控制

VLM 与 LLM 共用 Ollama，避免冲突：

- 图片描述生成是串行的（一张一张处理）
- VLM 处理完后才进入 LLM 提取阶段

---

## 输出示例

### 目录结构

```
output/
├── pdf_images/          # 提取的图片
│   ├── 文献1_p3_img1.jpg
│   ├── 文献1_p5_img2.jpg
│   └── 文献2_p2_img1.jpg
├── extracted_texts/     # 增强后的文本（含图片描述）
├── concepts.csv         # 包含图片知识的概念
└── relationships.csv
```

### 知识图谱增强

**无图片提取**:

```
概念: 松材线虫病, 马尾松, 松褐天牛
关系: 松材线虫病 -> 侵染 -> 马尾松
```

**有图片提取**:

```
概念: 松材线虫病, 马尾松, 松褐天牛, 线虫口针结构, 针叶变褐症状, 天牛成虫形态
关系:
  - 松材线虫病 -> 侵染 -> 马尾松
  - 松褐天牛 -> 传播 -> 松材线虫病
  - 针叶变褐症状 -> 表现于 -> 马尾松
  - 线虫口针结构 -> 属于 -> 松材线虫
```

**知识丰富度提升**: ~30-40%

---

## 故障排查

### 1. VLM 初始化失败

**错误**: `Ollama VLM 未找到模型 llava:7b`

**解决**:

```bash
ollama pull llava:7b
```

### 2. 图片提取为空

**原因**: PDF 中没有符合尺寸的图片

**检查**:

```yaml
pdf:
  min_image_size: 200 # 降低阈值
```

### 3. 描述生成超时

**原因**: VLM 推理耗时长

**优化**:

```yaml
llm:
  timeout: 900 # 增加到15分钟
```

### 4. 内存不足

**症状**: Ollama 崩溃

**解决**:

```yaml
pdf:
  max_images_per_pdf: 10 # 减少图片数
  enable_image_captions: false # 临时关闭
```

---

## 高级用法

### 自定义图片过滤

编辑`multimodal_extractor.py`:

```python
class ImageExtractor:
    def extract_images_from_pdf(self, pdf_path: str):
        # 自定义过滤逻辑
        if image.width < 400 or image.height < 400:
            continue  # 跳过小图

        if image.width / image.height > 5:
            continue  # 跳过横幅图（可能是页眉）
```

### 批量图片预处理

提前提取所有图片，离线处理：

```python
from multimodal_extractor import ImageExtractor

extractor = ImageExtractor()
for pdf_file in pdf_files:
    images = extractor.extract_images_from_pdf(pdf_file)
    # 手动标注、筛选...
```

---

## 相关文档

- [PDF 提取指南](PDF_CACHE_GUIDE.md)
- [内存优化指南](MEMORY_OPTIMIZATION.md)
- [完整优化总结](FINAL_OPTIMIZATION_SUMMARY.md)

---

## 更新历史

- **v2.6.3** (2025-12-01): 新增多模态图片提取功能
  - 集成 LLaVA VLM 支持
  - 自动图片提取和描述生成
  - 知识融合到主流程

---

**💡 提示**: 图片提取是可选功能，首次运行建议关闭以快速验证基础流程，后续再启用以增强知识图谱。
