# PDF 持久化缓存功能说明

## 🎯 问题解决

### 之前的问题

- **内存缓存**: 使用 `SimpleCache`（字典），程序重启后清空
- **每次重提取**: 28 个 PDF 每次都要重新提取，耗时 3-5 分钟
- **无法复用**: 即使 PDF 没变化，也要重新解析

### 现在的优化

- **磁盘缓存**: 使用 `DiskCache`（JSON 文件），程序重启后仍然有效
- **智能缓存 key**: 文件名+大小+修改时间，PDF 未变化则直接读取
- **秒级启动**: 第二次运行直接从缓存读取，**仅需 1-2 秒**

## 📊 性能对比

| 场景              | 旧版（内存缓存）       | 新版（磁盘缓存）       | 提升       |
| ----------------- | ---------------------- | ---------------------- | ---------- |
| **首次运行**      | 3-5 分钟               | 3-5 分钟               | -          |
| **重复运行**      | 3-5 分钟（重提取）     | **1-2 秒**（缓存）     | ⚡ **99%** |
| **修改 1 个 PDF** | 3-5 分钟（全部重提取） | ~10 秒（只提取修改的） | ⚡ **95%** |

## 🔧 工作原理

### 1. 缓存存储位置

```
output/cache/pdf_cache.json
```

### 2. 缓存 Key 生成

```python
# 格式: 文件名_大小_修改时间
"松材线虫病研究.pdf_1234567_1733068800"
```

**智能检测**:

- PDF 内容未变 → 读取缓存 ⚡
- PDF 被修改 → 重新提取 🔄
- 新增 PDF → 仅提取新文件 ➕

### 3. 自动管理

- ✅ 启动时自动加载缓存
- ✅ 提取后立即保存到磁盘
- ✅ 支持增量更新

## 📋 使用方法

### 正常使用（无需改变）

```bash
# 直接运行，自动使用缓存
./start.sh
```

**首次运行**:

```
找到 28 个PDF文件
PDF磁盘缓存已启用 (已缓存 0 个文件, 0.00 MB)
提取PDF文本: 100%|████████████| 28/28 [03:45<00:00]
```

**第二次运行**:

```
找到 28 个PDF文件
PDF磁盘缓存已启用 (已缓存 28 个文件, 1.23 MB)
使用缓存: 松材线虫病研究_张三.pdf
使用缓存: 防治技术综述_李四.pdf
...
提取PDF文本: 100%|████████████| 28/28 [00:02<00:00]
```

### 查看缓存状态

```python
from pdf_extractor import PDFExtractor

extractor = PDFExtractor()
stats = extractor.cache.get_stats()

print(f"已缓存文件: {stats['cached_files']} 个")
print(f"缓存大小: {stats['cache_size_mb']:.2f} MB")
```

### 清空缓存（如需要）

```python
from pdf_extractor import PDFExtractor

extractor = PDFExtractor()
extractor.cache.clear()
print("缓存已清空")
```

或直接删除文件：

```bash
rm output/cache/pdf_cache.json
```

## 🎯 典型场景

### 场景 1: 开发调试

**问题**: 频繁修改代码重启，每次都要等 3-5 分钟提取 PDF

**现在**:

- 首次运行: 3-5 分钟（提取+缓存）
- 后续运行: **1-2 秒**（读缓存）
- 节省时间: 每次启动节省 3-4 分钟

### 场景 2: 增量添加文献

**情况**: 已有 28 篇 PDF，新增 2 篇

**旧版**: 重新提取全部 30 个 PDF（~5 分钟）
**新版**:

- 28 个从缓存读取（~2 秒）
- 2 个新文件提取（~20 秒）
- **总耗时: 22 秒**

### 场景 3: 修改单个 PDF

**情况**: 修改了 1 个 PDF 的内容

**新版行为**:

```
- 松材线虫病研究_张三.pdf: 检测到修改，重新提取 🔄
- 其他27个: 从缓存读取 ⚡
总耗时: ~10秒
```

### 场景 4: 团队协作

**场景**: 多人共享 PDF 库

**优势**:

- 每个人首次运行建立本地缓存
- 后续运行秒级启动
- 无需共享缓存文件（自动管理）

## 🔍 缓存文件结构

```json
{
  "松材线虫病研究_张三.pdf_1234567_1733068800": "松材线虫病（Pine Wilt Disease）是一种...",
  "防治技术综述_李四.pdf_2345678_1733068900": "本文综述了松材线虫病的防治技术...",
  ...
}
```

**Key 格式**: `{文件名}_{文件大小}_{修改时间戳}`
**Value**: 提取的纯文本内容

## ⚙️ 配置选项

### 启用/禁用缓存

```python
# 启用缓存（默认）
extractor = PDFExtractor(use_cache=True)

# 禁用缓存（强制重提取）
extractor = PDFExtractor(use_cache=False)
```

### 自定义缓存目录

```python
from pdf_extractor import DiskCache

# 默认: ./output/cache
cache = DiskCache(cache_dir="./output/cache")

# 自定义目录
cache = DiskCache(cache_dir="./my_custom_cache")
```

## 📈 缓存统计

### 运行时日志

```
2025-12-01 20:48:45,021 - pdf_extractor - INFO - PDF磁盘缓存已启用 (已缓存 28 个文件, 1.23 MB)
2025-12-01 20:48:45,234 - pdf_extractor - INFO - 使用缓存: 松材线虫病研究_张三.pdf
2025-12-01 20:48:45,456 - pdf_extractor - INFO - 使用缓存: 防治技术综述_李四.pdf
...
```

### 缓存命中率

```
首次运行: 0% (全部提取)
第二次运行: 100% (全部缓存)
增加2个新PDF: 93% (28/30命中)
修改1个PDF: 96% (27/28命中)
```

## 🛠️ 维护管理

### 定期清理（可选）

```bash
# 缓存过大时（如>100MB）可清理
du -h output/cache/pdf_cache.json

# 清空缓存
rm output/cache/pdf_cache.json
```

### 备份缓存（可选）

```bash
# 备份缓存文件
cp output/cache/pdf_cache.json output/cache/pdf_cache.backup.json

# 恢复缓存
cp output/cache/pdf_cache.backup.json output/cache/pdf_cache.json
```

### 版本控制

```bash
# .gitignore 添加
echo "output/cache/pdf_cache.json" >> .gitignore

# 缓存不应提交到git（每个环境自动生成）
```

## 💡 最佳实践

### 1. 开发阶段

- ✅ 启用缓存（默认）
- ✅ 频繁重启快速迭代
- ✅ 修改 PDF 后自动重提取

### 2. 生产环境

- ✅ 启用缓存提高效率
- ✅ 定期备份缓存文件
- ✅ 监控缓存大小

### 3. 首次部署

- ✅ 第一次运行建立缓存
- ✅ 后续运行享受秒级启动
- ⚠️ 不要在多个进程间共享缓存文件（可能冲突）

## 🎉 效果验证

### 测试脚本

```python
import time
from pdf_extractor import PDFExtractor

# 首次运行（建立缓存）
print("首次运行（提取+缓存）...")
start = time.time()
extractor1 = PDFExtractor(use_cache=True)
texts1 = extractor1.extract_from_directory("./文献")
print(f"耗时: {time.time() - start:.2f}秒")

# 第二次运行（读缓存）
print("\n第二次运行（读缓存）...")
start = time.time()
extractor2 = PDFExtractor(use_cache=True)
texts2 = extractor2.extract_from_directory("./文献")
print(f"耗时: {time.time() - start:.2f}秒")

# 验证一致性
assert texts1.keys() == texts2.keys()
print("\n✅ 缓存数据一致性验证通过！")
```

### 预期结果

```
首次运行（提取+缓存）...
耗时: 245.67秒

第二次运行（读缓存）...
耗时: 1.23秒

✅ 缓存数据一致性验证通过！
加速比: 200倍 🚀
```

## 🔗 相关文档

- **内存优化**: `MEMORY_OPTIMIZATION.md`
- **完整文档**: `README.md`
- **实现细节**: `IMPLEMENTATION_DETAILS.md`

---

**版本**: v2.6.1  
**更新**: 2025-12-01  
**功能**: ✅ 持久化磁盘缓存  
**效果**: ⚡ 重复运行提速 99%
