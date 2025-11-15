# 📓 Google Colab 使用指南

## 🎯 为什么选择 Colab？

- ✅ **完全免费**: 无需购买云服务器
- ✅ **免费 GPU**: T4 GPU 加速（Colab Pro 有更好的 GPU）
- ✅ **零配置**: 无需安装 Python 环境
- ✅ **自动保存**: 结果保存到 Google Drive
- ✅ **随时随地**: 只需浏览器即可运行

---

## 🚀 快速开始（3 步）

### 步骤 1: 打开 Notebook

1. 将 `PWD_KG_Colab.ipynb` 上传到 Google Drive
2. 右键点击 → 打开方式 → Google Colaboratory
3. 或直接访问: https://colab.research.google.com/

### 步骤 2: 准备文件

```
Google Drive/
└── PWD_KG/              ← 创建这个文件夹
    ├── *.py             ← 上传所有Python文件
    ├── config/          ← 上传配置文件夹
    ├── requirements.txt ← 上传依赖文件
    └── 文献/            ← 上传PDF文献
```

### 步骤 3: 运行

按顺序运行所有单元格（Ctrl+F9 或 Runtime → Run all）

---

## 📋 详细步骤

### 1️⃣ 上传项目到 Google Drive

#### 方法 A: 手动上传（推荐新手）

1. 打开 Google Drive
2. 创建文件夹 `PWD_KG`
3. 上传以下文件:
   ```
   ✓ 所有 .py 文件 (main.py, concept_extractor.py等)
   ✓ config/ 文件夹
   ✓ requirements.txt
   ✓ 文献/ 文件夹（包含PDF）
   ```

#### 方法 B: 压缩包上传（推荐）

1. 在本地打包项目:
   ```bash
   zip -r PWD.zip *.py config/ requirements.txt 文献/
   ```
2. 上传 `PWD.zip` 到 Google Drive
3. 在 Colab 中解压

#### 方法 C: GitHub 同步（最方便）

1. 将项目推送到 GitHub
2. 在 Colab 中克隆:
   ```python
   !git clone https://github.com/your-username/PWD.git
   ```

---

### 2️⃣ 打开 Colab Notebook

1. 上传 `PWD_KG_Colab.ipynb` 到 Google Drive
2. 双击打开（自动用 Colab 打开）
3. 或右键 → 打开方式 → Google Colaboratory

---

### 3️⃣ 配置运行参数

在 Notebook 的配置单元格中修改:

```python
# 快速测试 (12.5分钟)
MAX_CHUNKS = 50

# 标准配置 (25分钟) ⭐ 推荐
MAX_CHUNKS = 100

# 高质量 (37.5分钟)
MAX_CHUNKS = 150

# 完整处理 (80分钟)
MAX_CHUNKS = None
```

---

### 4️⃣ 运行任务

#### 自动运行（推荐）

- 点击菜单: `Runtime` → `Run all`
- 或按快捷键: `Ctrl+F9` (Windows) / `Cmd+F9` (Mac)

#### 手动运行

- 逐个点击每个单元格的运行按钮
- 或按 `Shift+Enter` 运行当前单元格

---

### 5️⃣ 监控进度

#### 查看实时输出

- 单元格下方会显示运行日志
- 看到进度条和状态信息

#### 查看详细日志

在新单元格中运行:

```python
!tail -f output/kg_builder.log
```

#### 检查任务状态

```python
!ps aux | grep python
```

---

### 6️⃣ 下载结果

#### 方法 A: 自动下载（Notebook 内置）

运行下载单元格，文件会自动下载到本地

#### 方法 B: 从 Google Drive 下载

1. 打开 Google Drive
2. 进入 `PWD_KG/output/` 文件夹
3. 下载需要的文件

#### 方法 C: 打包下载

```python
# 打包所有结果
!zip -r results.zip output/
from google.colab import files
files.download('results.zip')
```

---

## ⚙️ 配置选项

### 时间 vs 质量权衡

| 配置   | 时间      | 概念数  | 适用场景    |
| ------ | --------- | ------- | ----------- |
| 50 块  | 12.5 分钟 | 150-180 | 快速验证    |
| 100 块 | 25 分钟   | 200-250 | 日常使用 ⭐ |
| 150 块 | 37.5 分钟 | 250-300 | 标准配置    |
| 200 块 | 50 分钟   | 300-400 | 高质量      |
| 321 块 | 80 分钟   | 400-600 | 完整处理    |

### 推荐配置

#### 🥇 首次运行

```python
MAX_CHUNKS = 100  # 25分钟，效果好
```

#### 🥈 时间紧急

```python
MAX_CHUNKS = 50   # 12.5分钟，快速测试
```

#### 🥉 最终版本

```python
MAX_CHUNKS = None # 80分钟，最完整
```

---

## 💡 使用技巧

### 1. 保持连接

- **免费版**: 90 分钟后自动断开
- **建议**: 使用 100-150 块配置（25-37.5 分钟）
- **Pro 版**: 更长的运行时间和更好的 GPU

### 2. 防止断开

```python
# 在单元格中运行，保持活跃
from IPython.display import Javascript
display(Javascript('''
  function KeepAlive() {
    console.log("Keep alive");
    setTimeout(KeepAlive, 60000);
  }
  KeepAlive();
'''))
```

### 3. 后台运行

- 关闭浏览器标签页，任务继续运行
- 结果自动保存到 Google Drive
- 重新打开 Notebook 可以看到结果

### 4. 使用 GPU

Colab 会自动检测和使用 GPU，无需额外配置

### 5. 节省时间

```python
# 使用缓存，避免重复处理
# 已在代码中实现，自动生效
```

---

## 🐛 常见问题

### Q1: Colab 断开连接怎么办？

**A**:

- 结果已保存在 Google Drive
- 重新打开 Notebook
- 跳过已完成的步骤
- 从结果下载单元格继续

### Q2: 如何查看运行进度？

**A**:

```python
# 方法1: 查看日志
!tail -20 output/kg_builder.log

# 方法2: 查看进程
!ps aux | grep python

# 方法3: 查看输出文件
!ls -lh output/
```

### Q3: 内存不足怎么办？

**A**:

- 减少 `MAX_CHUNKS` 数量
- 使用 Colab Pro（更多内存）
- 分批处理文献

### Q4: Ollama 安装失败？

**A**:

```python
# 手动安装
!curl -fsSL https://ollama.ai/install.sh | sh
!nohup ollama serve > /tmp/ollama.log 2>&1 &
!sleep 5
!ollama pull llama3.2:3b
```

### Q5: 找不到文件？

**A**:

```python
# 检查当前目录
!pwd
!ls -la

# 检查Drive挂载
!ls /content/drive/MyDrive/

# 切换到工作目录
%cd /content/drive/MyDrive/PWD_KG
```

### Q6: 如何重新运行？

**A**:

1. Runtime → Restart runtime
2. 重新运行所有单元格
3. 或只运行失败的部分

### Q7: 结果在哪里？

**A**:

```
Google Drive/
└── PWD_KG/
    └── output/
        ├── statistics_report.txt  ← 统计报告
        ├── triples/               ← 三元组数据
        └── neo4j_import/          ← Neo4j导入脚本
```

---

## 📊 性能对比

### Colab vs 本地

| 指标     | 本地 Mac | Colab 免费 | Colab Pro   |
| -------- | -------- | ---------- | ----------- |
| CPU      | M1/M2    | Intel Xeon | Intel Xeon  |
| GPU      | 无/集成  | T4 (16GB)  | A100 (40GB) |
| 内存     | 8-16GB   | 12GB       | 25GB        |
| 时间限制 | 无       | 90 分钟    | 24 小时     |
| 成本     | 电费     | 免费       | $10/月      |
| 速度     | 中等     | 快         | 很快        |

### 推荐场景

**使用 Colab 免费版**:

- ✅ 首次运行测试
- ✅ 处理 100-150 块
- ✅ 不想占用本地资源
- ✅ 需要 GPU 加速

**使用本地运行**:

- ✅ 需要处理全部 321 块
- ✅ 有强大的本地机器
- ✅ 需要频繁调试
- ✅ 网络不稳定

**使用 Colab Pro**:

- ✅ 需要长时间运行
- ✅ 需要更强 GPU
- ✅ 处理大规模数据
- ✅ 专业研究使用

---

## 🎯 最佳实践

### 1. 首次运行

```python
MAX_CHUNKS = 50  # 快速验证流程
```

### 2. 正式运行

```python
MAX_CHUNKS = 100  # 平衡速度和质量
```

### 3. 最终版本

```python
MAX_CHUNKS = 150  # 或 None（全部）
```

### 4. 定期保存

- Colab 自动保存 Notebook
- 结果自动保存到 Drive
- 建议手动下载重要结果

### 5. 版本管理

```python
# 给结果文件加时间戳
from datetime import datetime
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
!cp -r output output_backup_{timestamp}
```

---

## 📦 文件清单

### 上传到 Colab 的文件

**必需文件**:

```
✓ main.py
✓ concept_extractor.py
✓ concept_deduplicator.py
✓ enhanced_pipeline.py
✓ pdf_extractor.py
✓ data_cleaner.py
✓ neo4j_generator.py
✓ config_loader.py
✓ logger_config.py
✓ requirements.txt
✓ config/config.yaml
✓ config/stopwords.txt
✓ config/domain_dict.json
✓ 文献/*.pdf
```

**可选文件**:

```
○ cache/ (缓存，可不上传)
○ output/ (结果，可不上传)
○ README.md
○ *.sh (脚本，Colab不需要)
```

---

## ✅ 检查清单

运行前检查:

- [ ] 已上传所有必需文件
- [ ] 已挂载 Google Drive
- [ ] 已配置 MAX_CHUNKS
- [ ] 文献 PDF 已上传
- [ ] config.yaml 配置正确

运行中检查:

- [ ] Ollama 服务正常
- [ ] 模型下载完成
- [ ] 看到进度输出
- [ ] 无错误信息

运行后检查:

- [ ] 查看统计报告
- [ ] 概念数量合理
- [ ] 结果文件完整
- [ ] 已下载到本地

---

## 🎓 进阶技巧

### 1. 并行处理多个文献集

```python
# 创建多个工作目录
for dataset in ['dataset1', 'dataset2']:
    !mkdir -p /content/drive/MyDrive/PWD_KG_{dataset}
    # 分别处理
```

### 2. 自动化批处理

```python
# 循环处理不同配置
for chunks in [50, 100, 150]:
    config['llm']['max_chunks'] = chunks
    # 运行并保存结果
```

### 3. 结果对比

```python
# 比较不同配置的结果
import pandas as pd
df1 = pd.read_csv('output_50/triples.csv')
df2 = pd.read_csv('output_100/triples.csv')
# 分析差异
```

---

## 📞 获取帮助

### 遇到问题？

1. **查看日志**

   ```python
   !cat output/kg_builder.log
   ```

2. **检查错误**

   ```python
   !tail -50 output/kg_builder.log | grep ERROR
   ```

3. **重启运行时**
   Runtime → Restart runtime

4. **清理重来**
   ```python
   !rm -rf output/ cache/
   ```

---

## 🎉 完成后

### 1. 下载结果

- 统计报告
- 三元组数据
- Neo4j 导入脚本

### 2. 导入 Neo4j

- 使用生成的 Cypher 脚本
- 可视化知识图谱

### 3. 分享结果

- 导出为 PDF/图片
- 生成报告
- 发表论文

---

**祝您使用愉快！** 🚀

如有问题，请查看 Notebook 中的常见问题部分。
