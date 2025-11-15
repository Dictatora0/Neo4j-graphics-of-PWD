# 🚀 Colab 快速开始 - 3 分钟上手

## 📋 准备工作（5 分钟）

### 1. 打包项目文件

在本地运行:

```bash
cd /Users/lifulin/Desktop/PWD
zip -r PWD.zip *.py config/ requirements.txt 文献/
```

### 2. 上传到 Google Drive

1. 打开 https://drive.google.com
2. 创建文件夹 `PWD_KG`
3. 上传 `PWD.zip` 和 `PWD_KG_Colab.ipynb`

---

## ⚡ 运行（3 步）

### 步骤 1: 打开 Notebook

1. 在 Google Drive 中双击 `PWD_KG_Colab.ipynb`
2. 会自动用 Google Colab 打开

### 步骤 2: 运行所有单元格

- 点击菜单: `Runtime` → `Run all`
- 或按快捷键: `Ctrl+F9`

### 步骤 3: 等待完成

- 25 分钟后（100 块）
- 自动下载结果

---

## 🎯 就这么简单！

**时间线**:

- 0-5 分钟: 安装依赖
- 5-30 分钟: 构建知识图谱
- 30 分钟: 完成，下载结果

**预期结果**:

- 200-250 个概念
- 1000+条关系
- 完整的 Neo4j 导入脚本

---

## 💡 配置选项

在 Notebook 中找到这一行并修改:

```python
MAX_CHUNKS = 100  # 修改这里
```

**选项**:

- `50` = 12.5 分钟 (快速测试)
- `100` = 25 分钟 (推荐) ⭐
- `150` = 37.5 分钟 (高质量)
- `None` = 80 分钟 (完整处理)

---

## 📥 下载结果

Notebook 运行完成后:

1. 自动下载压缩包
2. 或从 Google Drive 的 `PWD_KG/output/` 下载

---

## ❓ 遇到问题？

### Colab 断开连接

- 结果已保存在 Google Drive
- 重新打开 Notebook
- 运行"下载结果"单元格

### 找不到文件

- 确保上传了所有必需文件
- 检查 Google Drive 的 `PWD_KG` 文件夹

### 运行失败

- 查看错误信息
- 重启运行时: `Runtime` → `Restart runtime`
- 重新运行所有单元格

---

## 📚 详细文档

- **完整指南**: `Colab使用指南.md`
- **Notebook**: `PWD_KG_Colab.ipynb`
- **本地运行**: `QUICK_START.md`

---

**开始使用吧！** 🎉
