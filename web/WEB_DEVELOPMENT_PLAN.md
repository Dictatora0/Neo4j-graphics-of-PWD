# 知识图谱 Web 前端开发规划

## 项目概述

开发一个交互式 Web 应用，用于展示和探索松材线虫病知识图谱，支持可视化浏览、智能搜索、路径分析等功能。

---

## 技术架构

### 前端技术栈

| 技术             | 版本   | 用途           |
| ---------------- | ------ | -------------- |
| **React**        | 18.x   | UI 框架        |
| **TypeScript**   | 5.x    | 类型安全       |
| **Vite**         | 5.x    | 构建工具       |
| **TailwindCSS**  | 3.x    | 样式框架       |
| **shadcn/ui**    | Latest | UI 组件库      |
| **Cytoscape.js** | 3.x    | 图谱可视化引擎 |
| **React Query**  | 5.x    | 数据状态管理   |
| **Zustand**      | 4.x    | 全局状态管理   |
| **Lucide React** | Latest | 图标库         |
| **Recharts**     | 2.x    | 数据图表       |

### 后端技术栈

| 技术                    | 版本   | 用途        |
| ----------------------- | ------ | ----------- |
| **FastAPI**             | 0.109+ | Web 框架    |
| **Neo4j Python Driver** | 5.x    | 数据库连接  |
| **Pydantic**            | 2.x    | 数据验证    |
| **CORS Middleware**     | -      | 跨域支持    |
| **Uvicorn**             | Latest | ASGI 服务器 |

---

## 功能模块设计

### 1. 图谱可视化模块

**功能**：

- 交互式力导向图布局
- 节点点击查看详情
- 关系高亮显示
- 缩放、平移、全屏
- 节点分类颜色编码
- 关系类型样式差异

**技术实现**：

- Cytoscape.js + React 集成
- 自定义节点样式（chiikawa 风格可选）
- 布局算法：force-directed, hierarchical, circular

### 2. 搜索与筛选模块

**功能**：

- 全文搜索节点
- 按类别筛选（9 类实体）
- 按关系类型筛选（17 类关系）
- 按重要性筛选（1-5 分）
- 搜索历史记录

**技术实现**：

- 模糊匹配算法
- 实时搜索建议
- 高级筛选面板

### 3. 节点详情模块

**功能**：

- 节点基本信息
- 关联关系列表
- 相邻节点展示
- 来源文献引用
- 重要性评分显示

**技术实现**：

- 侧边栏展示
- 动态加载邻居节点
- 关系分组显示

### 4. 路径分析模块

**功能**：

- 最短路径查询
- 关系路径可视化
- 传播链分析
- 影响因素追溯

**技术实现**：

- Neo4j Cypher 路径查询
- 路径高亮渲染
- 多路径对比

### 5. 统计面板模块

**功能**：

- 节点类型分布（饼图）
- 关系类型分布（柱状图）
- 核心节点排行（表格）
- 图谱连通性指标
- 实时统计更新

**技术实现**：

- Recharts 可视化
- 实时数据聚合
- 响应式图表

### 6. 数据导出模块

**功能**：

- 导出当前视图为图片
- 导出子图为 JSON
- 导出查询结果为 CSV
- 生成知识报告

**技术实现**：

- Canvas 截图 API
- 数据序列化
- 文件下载处理

---

## API 接口设计

### 基础数据接口

#### 1. 获取图谱数据

```http
GET /api/graph
Query Parameters:
  - limit: int (默认100)
  - node_type: str (可选)
  - relation_type: str (可选)
Response: {nodes: [...], edges: [...]}
```

#### 2. 搜索节点

```http
GET /api/nodes/search
Query Parameters:
  - q: str (搜索关键词)
  - type: str (可选，节点类型)
  - min_importance: int (可选，最小重要性)
Response: {nodes: [...], total: int}
```

#### 3. 获取节点详情

```http
GET /api/nodes/{node_id}
Response: {
  id: str,
  name: str,
  category: str,
  importance: int,
  neighbors: [...],
  relationships: [...]
}
```

#### 4. 获取节点邻居

```http
GET /api/nodes/{node_id}/neighbors
Query Parameters:
  - depth: int (默认1)
Response: {nodes: [...], edges: [...]}
```

#### 5. 路径查询

```http
POST /api/graph/path
Body: {
  source: str,
  target: str,
  max_length: int
}
Response: {paths: [...]}
```

#### 6. 统计数据

```http
GET /api/stats
Response: {
  total_nodes: int,
  total_edges: int,
  node_distribution: {...},
  edge_distribution: {...},
  top_nodes: [...]
}
```

---

## 项目目录结构

```
web/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # Neo4j连接
│   │   ├── models.py          # Pydantic模型
│   │   ├── routers/           # API路由
│   │   │   ├── graph.py       # 图谱接口
│   │   │   ├── nodes.py       # 节点接口
│   │   │   ├── stats.py       # 统计接口
│   │   │   └── search.py      # 搜索接口
│   │   └── services/          # 业务逻辑
│   │       ├── graph_service.py
│   │       ├── search_service.py
│   │       └── stats_service.py
│   ├── requirements.txt       # Python依赖
│   └── README.md
│
├── frontend/                   # 前端应用
│   ├── public/
│   ├── src/
│   │   ├── components/        # React组件
│   │   │   ├── Graph/         # 图谱可视化
│   │   │   │   ├── GraphViewer.tsx
│   │   │   │   ├── NodeDetails.tsx
│   │   │   │   └── GraphControls.tsx
│   │   │   ├── Search/        # 搜索模块
│   │   │   │   ├── SearchBar.tsx
│   │   │   │   └── FilterPanel.tsx
│   │   │   ├── Stats/         # 统计面板
│   │   │   │   ├── StatsDashboard.tsx
│   │   │   │   └── Charts.tsx
│   │   │   └── Layout/        # 布局组件
│   │   │       ├── Header.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── Footer.tsx
│   │   ├── hooks/             # 自定义Hooks
│   │   │   ├── useGraphData.ts
│   │   │   ├── useSearch.ts
│   │   │   └── useStats.ts
│   │   ├── services/          # API服务
│   │   │   └── api.ts
│   │   ├── store/             # 状态管理
│   │   │   └── graphStore.ts
│   │   ├── types/             # TypeScript类型
│   │   │   └── graph.ts
│   │   ├── utils/             # 工具函数
│   │   │   └── graphUtils.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── README.md
│
├── docker/                     # Docker配置
│   ├── docker-compose.yml
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
│
├── WEB_DEVELOPMENT_PLAN.md     # 本文档
└── README.md                   # Web模块说明
```

---

## 开发阶段

### Phase 1: 基础架构搭建（第 1 周）

- [x] 创建项目分支
- [ ] 搭建 FastAPI 后端框架
- [ ] 搭建 React 前端框架
- [ ] 配置 Neo4j 连接
- [ ] 实现基础 API 接口
- [ ] 实现前后端通信

### Phase 2: 核心功能开发（第 2-3 周）

- [ ] 实现图谱可视化（Cytoscape.js）
- [ ] 实现节点搜索功能
- [ ] 实现节点详情展示
- [ ] 实现统计面板
- [ ] 添加交互功能（点击、缩放）

### Phase 3: 高级功能开发（第 4 周）

- [ ] 实现路径分析功能
- [ ] 实现高级筛选
- [ ] 实现数据导出
- [ ] 优化性能（懒加载、缓存）
- [ ] 添加响应式设计

### Phase 4: 优化与测试（第 5 周）

- [ ] UI/UX 优化
- [ ] 性能优化
- [ ] 错误处理完善
- [ ] 单元测试
- [ ] 部署配置（Docker）

---

## 设计规范

### 配色方案

- **主色调**：蓝色系 (#2563eb, #3b82f6)
- **辅助色**：绿色系 (#10b981) - 成功状态
- **警告色**：橙色系 (#f59e0b)
- **错误色**：红色系 (#ef4444)
- **中性色**：灰色系 (#6b7280, #f3f4f6)

### 节点配色（按类别）

- **病原 (pathogen)**：#ef4444 (红色)
- **寄主 (host)**：#10b981 (绿色)
- **媒介 (vector)**：#f59e0b (橙色)
- **症状 (symptom)**：#8b5cf6 (紫色)
- **防治 (treatment)**：#3b82f6 (蓝色)
- **环境 (environment)**：#06b6d4 (青色)
- **地点 (location)**：#ec4899 (粉色)
- **机制 (mechanism)**：#6366f1 (靛蓝)
- **化合物 (compound)**：#84cc16 (黄绿)

### 关系样式

- **线宽**：根据关系权重（1-3px）
- **箭头**：有向关系显示箭头
- **颜色**：与源节点颜色一致，半透明

---

## 性能优化策略

### 前端优化

1. **虚拟化渲染**：大图谱使用视口裁剪
2. **懒加载**：按需加载节点详情
3. **防抖节流**：搜索输入、缩放操作
4. **缓存策略**：React Query 缓存 API 数据
5. **代码分割**：路由级别的代码分割

### 后端优化

1. **查询优化**：使用 Neo4j 索引
2. **分页加载**：大数据集分页返回
3. **缓存层**：Redis 缓存热点数据
4. **连接池**：Neo4j 连接池管理
5. **异步处理**：FastAPI 异步接口

---

## 部署方案

### Docker 部署

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      NEO4J_URI: neo4j://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: 12345678
    depends_on:
      - neo4j

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000

  neo4j:
    image: neo4j:5.15
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/12345678
```

### 生产环境

- **前端**：Vercel / Netlify
- **后端**：Railway / Render
- **数据库**：Neo4j Aura (云托管)

---

## 测试策略

### 前端测试

- **单元测试**：Vitest + React Testing Library
- **组件测试**：Storybook
- **E2E 测试**：Playwright

### 后端测试

- **单元测试**：pytest
- **API 测试**：pytest + httpx
- **集成测试**：pytest + Neo4j testcontainers

---

## 文档规划

1. **用户手册**：如何使用 Web 应用
2. **API 文档**：FastAPI 自动生成（Swagger UI）
3. **开发文档**：组件开发指南
4. **部署文档**：生产环境部署步骤

---

## 时间规划

| 阶段    | 时间      | 交付物              |
| ------- | --------- | ------------------- |
| Phase 1 | 第 1 周   | 基础框架 + API 接口 |
| Phase 2 | 第 2-3 周 | 核心功能 + 可视化   |
| Phase 3 | 第 4 周   | 高级功能 + 优化     |
| Phase 4 | 第 5 周   | 测试 + 部署         |

---

## 参考资源

- [Cytoscape.js 文档](https://js.cytoscape.org/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [React 官方文档](https://react.dev/)
- [TailwindCSS 文档](https://tailwindcss.com/)
- [shadcn/ui 组件库](https://ui.shadcn.com/)
