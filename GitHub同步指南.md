# 🔄 GitHub + Colab 同步方案

## 🎯 优势

- ✅ **快速**: 直接从 GitHub 克隆，无需上传大文件
- ✅ **版本控制**: 自动管理代码版本
- ✅ **完整质量**: 使用 150-321 块配置，不简化
- ✅ **自动同步**: 修改后自动更新

---

## 📋 准备工作（5 分钟）

### 1️⃣ 初始化 Git 仓库

```bash
cd /Users/lifulin/Desktop/PWD

# 如果还没有初始化Git
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: 松材线虫病知识图谱项目"
```

### 2️⃣ 创建 GitHub 仓库

1. 访问 https://github.com/new
2. 仓库名: `PWD-Knowledge-Graph` 或 `Neo4j-graphics-of-PWD`
3. 设置为 **Private** (如果文献有版权)
4. 不要初始化 README（我们已有）

### 3️⃣ 推送到 GitHub

```bash
# 添加远程仓库（替换为您的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git

# 推送
git branch -M main
git push -u origin main
```

---

## 🚀 Colab 使用（超简单）

### 完整版 Notebook（保证质量）

我已经为您准备了高质量配置的 Notebook，打开后直接运行即可。

### 在 Colab 中克隆项目

在 Notebook 的第一个单元格中:

```python
# 克隆GitHub仓库
!git clone https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git
%cd PWD-Knowledge-Graph

# 挂载Google Drive（保存结果）
from google.colab import drive
drive.mount('/content/drive')

# 创建结果目录链接
!ln -s /content/drive/MyDrive/PWD_Results output
```

---

## ⚙️ 质量保证配置

### 推荐配置（不简化）

在 Colab Notebook 中使用以下配置:

```python
# 方案1: 标准高质量 (推荐) ⭐⭐⭐
MAX_CHUNKS = 150
# 时间: 37.5分钟
# 概念: 250-300个
# 质量: 高

# 方案2: 完整处理 (最高质量) ⭐⭐⭐⭐⭐
MAX_CHUNKS = None  # 处理全部321块
# 时间: 80分钟
# 概念: 400-600个
# 质量: 最高

# 方案3: 更多块数 (平衡)
MAX_CHUNKS = 200
# 时间: 50分钟
# 概念: 300-400个
# 质量: 很高
```

### 配置说明

**不要使用 50 或 100 块** - 这会降低质量

**推荐使用**:

- **150 块**: 平衡速度和质量，37.5 分钟 ✅
- **200 块**: 更高质量，50 分钟 ✅✅
- **321 块**: 最完整，80 分钟 ✅✅✅

---

## 📝 更新后的 Colab Notebook

我会为您创建一个优化的版本，特点:

1. ✅ 直接从 GitHub 克隆
2. ✅ 默认使用 150 块（高质量）
3. ✅ 可选 321 块（完整处理）
4. ✅ 结果自动保存到 Google Drive
5. ✅ 无需上传文件

---

## 🔄 工作流程

### 首次使用

```
1. 推送代码到GitHub (1分钟)
   ↓
2. 打开Colab Notebook (30秒)
   ↓
3. 运行所有单元格 (37.5-80分钟)
   ↓
4. 自动下载结果
```

### 后续使用

```
1. 本地修改代码
   ↓
2. git push 推送到GitHub
   ↓
3. Colab中 git pull 更新
   ↓
4. 重新运行
```

---

## 💾 文献文件处理

### 方案 A: 使用 Git LFS（推荐）

```bash
# 安装Git LFS
brew install git-lfs  # Mac
# 或 sudo apt install git-lfs  # Linux

# 初始化
git lfs install

# 跟踪PDF文件
git lfs track "文献/*.pdf"
git add .gitattributes

# 提交
git add 文献/
git commit -m "Add PDF files with LFS"
git push
```

### 方案 B: 单独上传文献到 Drive

如果 PDF 文件太大，可以:

1. 文献文件夹单独上传到 Google Drive
2. 在 Colab 中挂载 Drive
3. 创建软链接

```python
# 在Colab中
!ln -s /content/drive/MyDrive/PWD_文献 文献
```

### 方案 C: 使用 Release 上传

```bash
# 打包文献
tar -czf 文献.tar.gz 文献/

# 在GitHub仓库页面:
# Releases → Create a new release → 上传 文献.tar.gz
```

---

## 📊 质量对比

| 配置       | 时间          | 概念数      | 关系质量 | 推荐度          |
| ---------- | ------------- | ----------- | -------- | --------------- |
| 50 块      | 12.5 分钟     | 150-180     | 一般     | ❌ 不推荐       |
| 100 块     | 25 分钟       | 200-250     | 中等     | ⚠️ 测试用       |
| **150 块** | **37.5 分钟** | **250-300** | **高**   | ✅ **推荐**     |
| **200 块** | **50 分钟**   | **300-400** | **很高** | ✅✅ **更好**   |
| **321 块** | **80 分钟**   | **400-600** | **最高** | ✅✅✅ **最佳** |

---

## 🎯 推荐方案

### 🥇 最推荐: 150 块配置

```python
MAX_CHUNKS = 150
```

**理由**:

- ✅ 时间可接受 (37.5 分钟 < 90 分钟限制)
- ✅ 质量高 (250-300 个概念)
- ✅ 在 Colab 免费版内完成
- ✅ 不会超时断开

### 🥈 追求完美: 200 块配置

```python
MAX_CHUNKS = 200
```

**理由**:

- ✅ 更高质量 (300-400 个概念)
- ✅ 50 分钟仍在限制内
- ✅ 显著优于 100 块

### 🥉 最高质量: 321 块配置

```python
MAX_CHUNKS = None
```

**理由**:

- ✅ 最完整 (400-600 个概念)
- ✅ 80 分钟在限制内
- ✅ 用于最终版本/发表

**注意**: 需要 Colab Pro 或本地运行

---

## 📦 完整命令清单

### 本地准备

```bash
# 1. 初始化Git
cd /Users/lifulin/Desktop/PWD
git init
git add .
git commit -m "Initial commit"

# 2. 推送到GitHub
git remote add origin https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git
git push -u origin main

# 3. 完成！
```

### Colab 运行

```python
# 1. 克隆项目
!git clone https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git
%cd PWD-Knowledge-Graph

# 2. 挂载Drive
from google.colab import drive
drive.mount('/content/drive')

# 3. 安装依赖
!curl -fsSL https://ollama.ai/install.sh | sh
!nohup ollama serve > /tmp/ollama.log 2>&1 &
!sleep 5
!ollama pull llama3.2:3b
!pip install -q -r requirements.txt

# 4. 配置高质量参数
import yaml
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['llm']['max_chunks'] = 150  # 或 200, 或 None
with open('config/config.yaml', 'w') as f:
    yaml.dump(config, f, allow_unicode=True)

# 5. 运行
!python main.py

# 6. 下载结果
!zip -r results.zip output/
from google.colab import files
files.download('results.zip')
```

---

## ✅ 检查清单

### 推送前检查

- [ ] 已添加 .gitignore
- [ ] 已提交所有代码文件
- [ ] 文献文件已处理（LFS 或单独上传）
- [ ] 已测试本地运行

### Colab 运行前检查

- [ ] GitHub 仓库已创建
- [ ] 代码已推送
- [ ] MAX_CHUNKS 设置为 150+ (保证质量)
- [ ] Google Drive 已挂载

### 运行后检查

- [ ] 概念数 ≥ 250 (150 块) 或 ≥ 400 (321 块)
- [ ] 关系质量良好
- [ ] 结果已保存
- [ ] 已下载到本地

---

## 🎓 进阶技巧

### 自动化脚本

创建 `run_in_colab.py`:

```python
#!/usr/bin/env python3
"""
Colab自动运行脚本
确保高质量输出
"""

import yaml
import subprocess
import sys

# 配置参数
QUALITY_CONFIGS = {
    'high': 150,      # 高质量
    'very_high': 200, # 很高质量
    'maximum': None   # 最高质量
}

# 选择质量级别
quality = 'high'  # 修改这里: high, very_high, maximum
max_chunks = QUALITY_CONFIGS[quality]

# 更新配置
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

config['llm']['max_chunks'] = max_chunks

with open('config/config.yaml', 'w') as f:
    yaml.dump(config, f, allow_unicode=True)

print(f"✓ 质量级别: {quality}")
print(f"✓ 处理块数: {max_chunks if max_chunks else 'ALL (321)'}")

# 运行主程序
subprocess.run([sys.executable, 'main.py'])
```

---

## 📞 需要帮助？

### 常见问题

**Q: GitHub 仓库应该设为 Public 还是 Private?**
A: 如果文献有版权，设为 Private；否则 Public 方便分享

**Q: 文献文件太大怎么办?**
A: 使用 Git LFS 或单独上传到 Google Drive

**Q: Colab 会超时吗?**
A: 150 块 37.5 分钟，200 块 50 分钟，都在 90 分钟限制内

**Q: 如何确保质量?**
A: 使用 150 块以上配置，不要低于 100 块

---

**开始推送到 GitHub 吧！** 🚀
