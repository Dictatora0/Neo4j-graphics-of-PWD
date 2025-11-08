# 故障排除指南

## 常见问题及解决方案

### 1. KeyBERT 导入错误

**错误信息**：`ImportError: cannot import name 'cached_download'`

**解决方案**：

```bash
pip uninstall sentence-transformers huggingface-hub keybert -y
pip install sentence-transformers==2.3.1 huggingface-hub>=0.19.0 keybert==0.8.5
```

---

### 2. spaCy 模型未安装

**错误信息**：`OSError: [E050] Can't find model 'zh_core_web_sm'`

**解决方案**：

```bash
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm

# 如果下载失败，使用镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python -m spacy download zh_core_web_sm
```

---

### 3. 关系数量为 0

**原因**：置信度阈值太高

**解决方案**：

修改 `config/config.yaml`：

```yaml
cleaning:
  confidence_threshold: 0.65  # 降低阈值（范围：0.60-0.70）
```

---

### 4. Neo4j 连接失败

**错误信息**：`Connection refused` 或 `Failed to establish connection`

**原因**：Neo4j 服务未启动

**解决方案**：

```bash
# 方法 1: 使用命令行启动 Neo4j
neo4j start

# 方法 2: 使用 brew services（macOS）
brew services start neo4j

# 方法 3: 使用 Neo4j Desktop
# 打开 Neo4j Desktop 应用，点击数据库的 Start 按钮

# 检查 Neo4j 状态
neo4j status

# 访问 Neo4j Browser 确认运行
open http://localhost:7474
```

**如果未安装 Neo4j**：

```bash
# macOS 使用 Homebrew 安装
brew install neo4j

# 或下载 Neo4j Desktop（推荐）
# 访问: https://neo4j.com/download/
```

---

### 5. Neo4j CSV 导入失败

**错误信息**：`Couldn't load the external resource`

**原因**：CSV 文件不在 Neo4j 的 import 目录

**解决方案**：

```bash
# 查找 Neo4j import 目录
# Linux/Mac: ~/neo4j/import/ 或 /var/lib/neo4j/import/
# Windows: C:\Users\YourName\neo4j\import\

# 复制文件
cp output/neo4j_import/*.csv ~/neo4j/import/

# 检查文件权限
chmod 644 ~/neo4j/import/*.csv
```

---

### 6. 内存不足

**症状**：`MemoryError: Unable to allocate array`

**解决方案**：

方法一：减少并行进程数

```yaml
# config/config.yaml
pdf:
  parallel_workers: 2  # 降低从 4
```

方法二：减少关键词提取数量

```yaml
entity:
  max_keywords_tfidf: 30  # 降低从 50
  enable_keybert: false   # 禁用占用内存较多的功能
```

---

### 7. 实体识别结果过少

**解决方案**：

1. 扩充领域词典 `config/domain_dict.json`
2. 降低清洗阈值

```yaml
cleaning:
  similarity_threshold: 0.75  # 降低从 0.85
  confidence_threshold: 0.60  # 降低从 0.65

entity:
  max_keywords_tfidf: 100  # 增加从 50
```

---

### 8. 关系抽取质量低

**解决方案**：

1. 提高置信度阈值

```yaml
cleaning:
  confidence_threshold: 0.70  # 提高从 0.65
```

2. 启用实体链接

```yaml
cleaning:
  enable_entity_linking: true
```

---

### 9. PDF 提取失败

**症状**：提取的文本为空或乱码

**可能原因**：
- PDF 是扫描版（需要 OCR）
- PDF 文件损坏
- PDF 加密保护

**解决方案**：

检查 PDF 类型：

```python
import fitz
doc = fitz.open('文献/your_file.pdf')
text = doc[0].get_text()
print(f"文本长度: {len(text)}")
```

如果文本长度为 0，说明是扫描版 PDF，需要 OCR 支持（当前版本暂不支持）。

---

## 快速修复命令

### 完全重新安装

```bash
# 卸载所有依赖
pip freeze | xargs pip uninstall -y

# 重新安装
pip install -r requirements.txt

# 下载 spaCy 模型
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm

# 测试
python test_modules.py
```

### 清理缓存

```bash
# 删除缓存目录
rm -rf output/cache/

# 或使用 Python
python -c "from cache_manager import CacheManager; CacheManager().clear_cache()"
```

---

## 调试技巧

### 查看日志

```bash
# 实时查看日志
tail -f output/kg_builder.log

# 查看错误
grep "ERROR" output/kg_builder.log

# 查看特定模块
grep "EntityRecognizer" output/kg_builder.log
```

### 测试单个模块

```bash
# 测试 PDF 提取
python -c "from pdf_extractor import PDFExtractor; print('OK')"

# 测试实体识别
python -c "from entity_recognizer import EntityRecognizer; print('OK')"

# 运行完整测试
python test_modules.py
```

---

## 版本兼容性

| Python | spaCy | sentence-transformers | 状态 |
| ------ | ----- | --------------------- | ---- |
| 3.8    | 3.7.x | 2.3.x                 | ✅   |
| 3.9    | 3.7.x | 2.3.x                 | ✅   |
| 3.10   | 3.7.x | 2.3.x                 | ✅   |
| 3.11   | 3.7.x | 2.3.x                 | ✅   |
| 3.12   | 3.7.x | 2.3.x                 | ⚠️   |

---

## 获取帮助

如果以上方法无法解决问题：

1. 查看完整错误日志：`output/kg_builder.log`
2. 运行诊断脚本：`python test_modules.py`
3. 提交 Issue 并附上错误日志
