# 多模态功能设置指南

## ✅ 已完成的配置

### 1. 配置文件更新

**文件**：`config/config.yaml`

**更改**：

```yaml
pdf:
  enable_image_captions: true # ✅ 已启用（之前是 false）
  caption_model: llava:7b
  image_output_dir: ./output/pdf_images
  max_images_per_pdf: 20
```

### 2. 模型下载

**命令**：`ollama pull llava:7b`

**状态**：

- 🔄 正在下载中（约 4.1GB）
- ⏱️ 预计时间：4-5 分钟
- 📍 进度：可在终端查看

**验证下载完成**：

```bash
ollama list | grep llava
```

应该看到：

```
llava:7b    ...    4.7 GB    ...
```

---

## 🚀 使用流程

### 步骤 1：等待模型下载完成

```bash
# 检查下载状态
ollama list

# 应该看到 llava:7b 在列表中
```

### 步骤 2：运行知识图谱构建

```bash
# 清除之前的结果（可选）
rm -rf output/pdf_images output/image_captions.json

# 启动构建
bash start.sh --batch-size 5 --batch-mode manual
```

**现在会额外做什么**：

- 从 PDF 中提取图片
- 使用 llava:7b 为每张图片生成描述
- 保存到 `output/pdf_images/` 和 `output/image_captions.json`

### 步骤 3：构建多模态图谱

构建完成后，运行多模态图谱构建脚本：

```python
from multimodal_graph_builder import MultimodalGraphBuilder
from concept_extractor import ConceptExtractor
import pandas as pd

# 初始化
builder = MultimodalGraphBuilder()
concept_extractor = ConceptExtractor()

# 加载图片描述
images_df = builder.load_image_captions("output/image_captions.json")
print(f"加载了 {len(images_df)} 张图片")

# 从图片描述中抽取概念
image_concepts_df = builder.extract_concepts_from_captions(
    images_df,
    concept_extractor
)

# 加载主图概念
concepts_df = pd.read_csv("output/concepts.csv")

# 建立图片-概念关系
image_concept_rels_df = builder.build_image_concept_relationships(
    image_concepts_df,
    concepts_df
)

# 导出
builder.export_to_csv(images_df, image_concept_rels_df)
print("✅ 多模态数据已导出")
```

或者使用命令行（如果有集成脚本）：

```bash
python build_multimodal_graph.py
```

### 步骤 4：导入 Neo4j

```bash
python import_to_neo4j_final.py
```

确保导入时也导入 Image 节点和 ILLUSTRATED_BY 关系。

### 步骤 5：启动 Web 应用

```bash
cd web
./start.sh
```

访问 http://localhost:5173，点击任意节点，查看节点详情面板中的"相关图片"区域。

---

## 📊 预期输出

### 文件结构

```
output/
├── pdf_images/           # 提取的图片
│   ├── paper1_page3_img1.png
│   ├── paper1_page5_img2.png
│   └── ...
├── image_captions.json   # 图片描述
├── images.csv            # 图片节点数据
└── image_concept_relationships.csv  # 图片-概念关系
```

### image_captions.json 格式

```json
[
  {
    "path": "output/pdf_images/paper1_page3_img1.png",
    "caption": "显微镜下的松材线虫，体长约1mm，呈线状...",
    "source_pdf": "paper1.pdf",
    "page_num": 3
  },
  ...
]
```

### 前端效果

- 选中节点"松材线虫"
- 节点详情面板显示：
  - 基本信息
  - **相关图片(2)**：2 张缩略图
  - 反馈与纠错按钮

---

## ⚙️ 性能优化

### 如果内存不足

```yaml
pdf:
  max_images_per_pdf: 10 # 减少到 10 张
  parallel_workers: 2 # 降低并发数
```

### 如果处理太慢

- 使用更小的批次：`bash start.sh --batch-size 3`
- 先处理少量 PDF 测试
- 考虑只启用关键 PDF 的图片抽取

---

## 🔧 故障排查

### 模型下载失败

```bash
# 检查 Ollama 服务
pgrep ollama

# 如果未运行
ollama serve &

# 重新下载
ollama pull llava:7b
```

### 图片抽取失败

```bash
# 检查日志
tail -f output/kg_builder.log

# 常见问题：
# 1. PDF 没有图片
# 2. 图片尺寸太小（被 min_image_size 过滤）
# 3. Ollama 服务未运行或 llava 模型未加载
```

### 前端不显示图片

1. 检查 API 是否返回数据：

   ```bash
   curl http://localhost:8000/api/multimodal/stats
   ```

2. 检查图片文件是否存在：

   ```bash
   ls output/pdf_images/
   ```

3. 检查浏览器控制台是否有错误

---

## 📈 当前状态

- ✅ 配置文件已启用图片抽取
- 🔄 llava:7b 模型正在下载
- ⏸️ 待模型下载完成后即可运行

**下一步**：等待 llava:7b 下载完成，然后运行 `bash start.sh`

---

最后更新：2024-12-08
