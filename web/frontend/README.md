# PWD Knowledge Graph - Frontend

松材线虫病知识图谱可视化前端应用

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### 构建生产版本

```bash
npm run build
```

## 🛠️ 技术栈

- **React 19** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **TailwindCSS** - 样式框架
- **Cytoscape.js** - 图谱可视化引擎
- **React Query** - 数据状态管理
- **Axios** - HTTP 客户端

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/       # React组件
│   │   └── GraphViewer.tsx    # 图谱可视化组件
│   ├── services/         # API服务
│   │   └── api.ts       # 后端API封装
│   ├── types/           # TypeScript类型定义
│   │   └── graph.ts     # 图谱数据类型
│   ├── App.tsx          # 主应用组件
│   └── main.tsx         # 应用入口
├── public/              # 静态资源
└── index.html           # HTML模板
```

## 🎨 功能特性

### 已实现

- ✅ 知识图谱交互式可视化
- ✅ 节点点击查看详情
- ✅ 图谱缩放、平移控制
- ✅ 节点数量筛选
- ✅ 实时统计数据显示
- ✅ 响应式布局设计

### 开发中

- 🚧 高级搜索功能
- 🚧 路径分析可视化
- 🚧 数据导出功能
- 🚧 统计图表面板

## 🔧 配置

### 环境变量

创建 `.env` 文件：

```env
VITE_API_URL=http://localhost:8000
```

## 📝 React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.node.json", "./tsconfig.app.json"],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from "eslint-plugin-react-x";
import reactDom from "eslint-plugin-react-dom";

export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs["recommended-typescript"],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.node.json", "./tsconfig.app.json"],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```
