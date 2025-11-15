# 🚀 Colab 运行步骤 - 超简单 3 步

## ⚡ 快速开始

### 第 1 步: 推送代码到 GitHub（2 分钟）

```bash
cd /Users/lifulin/Desktop/PWD
./push_to_github.sh
```

按提示输入您的 GitHub 仓库地址，例如:

```
https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git
```

---

### 第 2 步: 上传文献到 Google Drive（3 分钟）

1. 打开 https://drive.google.com
2. 创建文件夹 `PWD_文献`
3. 将本地 `文献/` 文件夹中的所有 PDF 上传到 `PWD_文献`

---

### 第 3 步: 运行 Colab（37.5 分钟）

1. 上传 `PWD_KG_Colab_GitHub.ipynb` 到 Google Drive
2. 双击打开（自动用 Colab 打开）
3. 修改第一个单元格中的 `GITHUB_REPO`:
   ```python
   GITHUB_REPO = "https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git"
   ```
4. 点击 `Runtime` → `Run all`
5. 等待完成（37.5 分钟）

---

## ✅ 完成！

结果会自动:

- ✅ 保存到 Google Drive 的 `PWD_Results` 文件夹
- ✅ 下载到本地

---

## 🎯 质量保证

默认配置: **150 块 (高质量)**

- ⏱️ 时间: 37.5 分钟
- 📊 概念: 250-300 个
- ⭐ 质量: 高

### 如需更高质量

在 Notebook 第一个单元格修改:

```python
# 很高质量 (50分钟, 300-400个概念)
QUALITY_LEVEL = "very_high"

# 最高质量 (80分钟, 400-600个概念)
QUALITY_LEVEL = "maximum"
```

---

## 📊 配置对比

| 质量级别  | 块数 | 时间      | 概念数  | 推荐度          |
| --------- | ---- | --------- | ------- | --------------- |
| high      | 150  | 37.5 分钟 | 250-300 | ⭐⭐⭐ 推荐     |
| very_high | 200  | 50 分钟   | 300-400 | ⭐⭐⭐⭐ 更好   |
| maximum   | 321  | 80 分钟   | 400-600 | ⭐⭐⭐⭐⭐ 最佳 |

**不使用低于 150 块的配置** - 确保质量

---

## 💡 提示

1. **首次运行**: 使用 `high` (150 块)
2. **正式分析**: 使用 `very_high` (200 块)
3. **最终版本**: 使用 `maximum` (321 块)

---

## ❓ 遇到问题？

### GitHub 仓库地址在哪里？

1. 访问 https://github.com/new
2. 创建仓库后，复制仓库 URL
3. 格式: `https://github.com/YOUR_USERNAME/REPO_NAME.git`

### 文献上传太慢？

- 文献文件夹可能较大
- 建议使用 Google Drive 桌面客户端
- 或分批上传

### Colab 找不到文献？

检查文件夹名称是否为 `PWD_文献`（不是 `文献`）

---

**就这么简单！** 🎉
