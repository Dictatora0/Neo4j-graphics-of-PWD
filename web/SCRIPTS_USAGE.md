# 启动脚本使用指南

## 📜 脚本列表

### 1. `start.sh` - 启动服务

**功能：**

- 自动检测端口占用（8000, 5173）
- 智能释放冲突端口（询问用户确认）
- 检查 Neo4j 数据库连接
- 检查 Python 和 Node.js 依赖
- 自动安装缺失的依赖
- 后台启动前后端服务
- 显示服务访问地址

**使用方法：**

```bash
cd web
./start.sh
```

**输出示例：**

```
╔════════════════════════════════════════════════════════╗
║  🚀 知识图谱 Web 应用已启动                           ║
╠════════════════════════════════════════════════════════╣
║  ✓ 后端服务: http://localhost:8000          ║
║    API 文档: http://localhost:8000/docs      ║
║  ✓ 前端应用: http://localhost:5173          ║
║  ✓ Neo4j 浏览器: http://localhost:7474     ║
╠════════════════════════════════════════════════════════╣
║  停止服务: ./stop.sh                                   ║
║  查看日志: tail -f /tmp/pwd-*.log                      ║
╚════════════════════════════════════════════════════════╝
```

---

### 2. `stop.sh` - 停止服务

**功能：**

- 优雅停止前后端服务
- 清理 PID 文件
- 可选择是否保留日志

**使用方法：**

```bash
./stop.sh              # 询问是否保留日志
./stop.sh --keep-logs  # 自动保留日志
```

---

### 3. `status.sh` - 查看状态

**功能：**

- 实时显示所有服务状态
- 显示进程 PID、内存、CPU 占用
- 健康检查（后端 API）
- 显示日志文件路径和大小

**使用方法：**

```bash
./status.sh
```

**输出示例：**

```
━━━ 后端 FastAPI 服务 ━━━
  状态: ● 运行中
  端口: 8000
  PID:  12345
  内存: 85.2MB
  CPU:  2.1%
  API:  http://localhost:8000
  文档: http://localhost:8000/docs
  健康: ✓ 正常
  日志: /tmp/pwd-backend.log (2.3M)
```

---

### 4. `restart.sh` - 重启服务

**功能：**

- 停止所有服务（保留日志）
- 等待 2 秒
- 重新启动所有服务

**使用方法：**

```bash
./restart.sh
```

---

## 🔧 端口配置

| 服务       | 端口 | 说明            |
| ---------- | ---- | --------------- |
| 前端       | 5173 | Vite 开发服务器 |
| 后端       | 8000 | FastAPI 服务    |
| Neo4j Bolt | 7687 | 数据库连接      |
| Neo4j HTTP | 7474 | Web 管理界面    |

---

## 📝 日志文件

所有服务日志保存在 `/tmp/` 目录：

```bash
# 查看后端日志
tail -f /tmp/pwd-backend.log

# 查看前端日志
tail -f /tmp/pwd-frontend.log

# 同时查看所有日志
tail -f /tmp/pwd-*.log
```

---

## ⚠️ 常见问题

### 1. 端口被占用

**问题：**

```
⚠ 端口 8000 被进程占用 (PID: 12345, Command: python)
```

**解决：**

- 脚本会自动询问是否终止占用进程
- 选择 `Y` 自动释放端口
- 选择 `N` 手动处理

### 2. Neo4j 未运行

**问题：**

```
✗ Neo4j 未运行 (端口 7687)
```

**解决：**

```bash
# 启动 Neo4j
neo4j start

# 或使用 Neo4j Desktop
```

### 3. 依赖缺失

**问题：**

```
⚠ 缺少 Python 依赖，正在安装...
```

**解决：**

- 脚本会自动安装
- 也可手动安装：

  ```bash
  cd web/backend
  pip install -r requirements.txt

  cd ../frontend
  npm install
  ```

### 4. 服务启动失败

**排查步骤：**

1. 查看状态

   ```bash
   ./status.sh
   ```

2. 查看日志

   ```bash
   tail -n 50 /tmp/pwd-backend.log
   tail -n 50 /tmp/pwd-frontend.log
   ```

3. 手动启动测试

   ```bash
   # 后端
   cd web/backend
   uvicorn app.main:app --reload --port 8000

   # 前端
   cd web/frontend
   npm run dev
   ```

---

## 🎯 使用流程

### 首次启动

```bash
cd web

# 1. 确保 Neo4j 运行
neo4j status

# 2. 启动服务
./start.sh

# 3. 检查状态
./status.sh

# 4. 访问应用
open http://localhost:5173
```

### 日常使用

```bash
# 启动
./start.sh

# 查看状态
./status.sh

# 停止
./stop.sh

# 重启
./restart.sh
```

---

## 🛠️ 手动控制

### 只启动后端

```bash
cd web/backend
uvicorn app.main:app --reload --port 8000 &
```

### 只启动前端

```bash
cd web/frontend
npm run dev &
```

### 只停止后端

```bash
kill $(lsof -ti:8000)
```

### 只停止前端

```bash
kill $(lsof -ti:5173)
```

---

## 📊 性能监控

### 实时监控

```bash
# 持续监控服务状态
watch -n 2 ./status.sh

# 实时查看日志
tail -f /tmp/pwd-*.log
```

### 资源占用

```bash
# 查看进程详情
ps aux | grep -E 'uvicorn|vite|node'

# 查看端口占用
lsof -i :8000
lsof -i :5173
```

---

## 🔐 安全提示

1. **生产环境**：这些脚本用于开发环境，生产环境请使用 systemd、PM2 或 Docker
2. **日志轮转**：长期运行需要配置日志轮转，避免日志文件过大
3. **权限控制**：脚本包含 `kill` 命令，请谨慎使用

---

## 📚 更多信息

- 详细文档：[WEB_DEVELOPMENT_PLAN.md](./WEB_DEVELOPMENT_PLAN.md)
- API 文档：http://localhost:8000/docs（服务启动后）
- 前端 README：[frontend/README.md](./frontend/README.md)
- 后端 README：[backend/README.md](./backend/README.md)
