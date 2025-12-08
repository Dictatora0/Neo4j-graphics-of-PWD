# 前端新功能说明

## 新增功能

### 1. 人机回环纠错功能 (Human-in-the-Loop Feedback)

**位置**：节点详情面板 → 底部"反馈与纠错"区域

**功能**：

- **建议实体合并**：当发现两个实体应该合并时（如"松材线虫"和"线虫"）
- **报告缺失关系**：当发现两个实体之间应该存在关系但图谱中缺失时

**实现文件**：

- `src/components/FeedbackModal.tsx` - 反馈表单模态框
- `src/services/api.ts` - 添加了 `feedbackAPI`

**支持的反馈类型**：

- `relation_direction` - 关系方向错误
- `relation_type` - 关系类型错误
- `entity_merge` - 实体合并建议
- `missing_relation` - 缺失关系

**数据流**：

1. 用户在节点详情面板点击纠错按钮
2. 弹出反馈表单模态框
3. 用户填写纠错信息（必填项 + 可选备注）
4. 提交到后端 API `/api/feedback/*`
5. 数据保存到 `output/human_feedback.jsonl`
6. 后续可用于 Prompt 优化或模型微调

---

### 2. 多模态图片展示功能 (Multimodal Image Gallery)

**位置**：节点详情面板 → "相关图片"区域

**功能**：

- 自动加载与选中概念相关的图片（最多显示 4 张缩略图）
- 点击图片可放大查看
- 显示图片描述(caption)、来源 PDF 和页码

**实现文件**：

- `src/components/ImageGallery.tsx` - 图片展示组件
- `src/services/api.ts` - 添加了 `multimodalAPI`

**API 接口**：

- `GET /api/multimodal/concept/{name}/images` - 获取概念的图片列表
- `GET /api/multimodal/image/{path}` - 获取图片文件
- `GET /api/multimodal/stats` - 获取多模态数据统计

**前置条件**：

- 需要在 `config/config.yaml` 中启用图片抽取：
  ```yaml
  pdf:
    enable_image_captions: true
    caption_model: llava:7b
  ```
- 运行图谱构建时会生成 `output/image_captions.json`
- 使用 `multimodal_graph_builder.py` 建立图片-概念关系

**错误处理**：

- 图片加载失败时显示占位符
- 没有图片时不显示图片区域
- API 错误时静默失败（不影响其他功能）

---

## 使用示例

### 纠错流程示例

1. 用户浏览图谱，点击节点"松材线虫"
2. 在节点详情面板查看信息
3. 发现应该有"松材线虫"→"马尾松"的感染关系但图谱中缺失
4. 点击"报告缺失关系"按钮
5. 填写表单：
   - 目标实体：马尾松
   - 关系类型：感染
   - 备注：文献第 3 页提到...
6. 提交成功

### 图片查看流程示例

1. 用户点击节点"松褐天牛"
2. 节点详情面板自动加载相关图片（如果有）
3. 显示 2-4 张缩略图
4. 点击任一图片查看大图
5. 可查看图片描述和来源信息

---

## 技术栈

- **状态管理**：React Hooks (`useState`)
- **数据获取**：TanStack Query (React Query)
- **图标**：Lucide React
- **样式**：Tailwind CSS
- **类型**：TypeScript

---

## 后续改进建议

1. **关系纠错按钮**：在 GraphViewer 的边(edge)上添加右键菜单，直接纠错关系方向/类型
2. **批量反馈**：允许用户一次性提交多个反馈
3. **反馈统计面板**：显示当前用户的反馈历史和统计
4. **图片搜索**：按图片内容搜索相关概念
5. **用户认证**：集成真实的用户系统，替换 hardcoded 的 `web_user`

---

## 测试建议

### 测试纠错功能

1. 启动后端：`cd web && ./start.sh`
2. 打开浏览器：http://localhost:5173
3. 选择任意节点
4. 点击"建议实体合并"或"报告缺失关系"
5. 填写表单并提交
6. 检查 `output/human_feedback.jsonl` 是否有新记录

### 测试图片展示

1. 确保已启用图片抽取并生成了图片数据
2. 选择有相关图片的概念节点
3. 查看节点详情面板是否显示图片
4. 点击图片测试放大查看功能

---

最后更新：2024-12-08
