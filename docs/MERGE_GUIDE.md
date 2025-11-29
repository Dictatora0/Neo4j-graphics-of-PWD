# 多功能分支合并指南

## 📋 待合并分支清单

- ✅ `feature/llm-upgrade` - LLM 推理升级 & 结构化抽取（成员 A）
- ⏳ `feature/multimodal` - PDF 图片与图表信息提取（成员 B）
- ⏳ `feature/smart-parser` - Layout-Aware 文档解析优化（成员 C）
- ⏳ `feature/agent-logic` - Agentic Workflow & GraphRAG（成员 D）
- ⏳ `feature/bge-embedding` - Embedding 升级 & 实体对齐（成员 E）

## 🎯 合并策略选择

### 方案 A：逐个合并法（推荐 ⭐）

**优点**：

- 安全可控，问题易定位
- 可以逐步测试每个功能
- 冲突处理更简单

**步骤**：

```bash
# 1. 确保本地是最新的
git checkout main
git pull origin main

# 2. 逐个合并功能分支（按依赖顺序）
# 建议顺序：C → A → E → B → D

# Step 1: 合并 smart-parser（基础设施，最先合并）
git merge origin/feature/smart-parser --no-ff -m "Merge: Layout-Aware 文档解析优化"
# 如有冲突，解决后：
# git add .
# git commit -m "Fix: 解决 smart-parser 合并冲突"

# 测试：验证 PDF 解析功能
python -m pytest tests/test_pdf_parser.py
# 或手动测试
python pdf_extractor.py

# Step 2: 合并 llm-upgrade（核心功能）
git merge origin/feature/llm-upgrade --no-ff -m "Merge: LLM 推理升级"
# 测试：验证 LLM 抽取
python enhanced_pipeline.py --max-chunks 5

# Step 3: 合并 bge-embedding（实体对齐）
git merge origin/feature/bge-embedding --no-ff -m "Merge: Embedding 升级"
# 测试：验证实体去重
python concept_deduplicator.py

# Step 4: 合并 multimodal（图片提取）
git merge origin/feature/multimodal --no-ff -m "Merge: 多模态图片提取"
# 测试：验证图片描述生成
python image_captioner.py

# Step 5: 合并 agent-logic（高级功能，最后合并）
git merge origin/feature/agent-logic --no-ff -m "Merge: Agentic Workflow"
# 测试：验证 GraphRAG
python graph_summarizer.py

# 3. 推送合并结果
git push origin main
```

---

### 方案 B：集成分支法（适合复杂项目）

创建一个临时的集成分支，在上面测试所有功能，验证无误后再合并到 main。

```bash
# 1. 创建集成分支
git checkout main
git pull origin main
git checkout -b integration/v2.0

# 2. 合并所有功能分支
git merge origin/feature/smart-parser --no-ff
git merge origin/feature/llm-upgrade --no-ff
git merge origin/feature/bge-embedding --no-ff
git merge origin/feature/multimodal --no-ff
git merge origin/feature/agent-logic --no-ff

# 3. 全面测试
python -m pytest tests/
python enhanced_pipeline.py --full-test

# 4. 如果测试通过，合并到 main
git checkout main
git merge integration/v2.0 --no-ff -m "Release: v2.0 - 全功能升级"
git push origin main

# 5. 清理集成分支
git branch -d integration/v2.0
```

---

### 方案 C：Rebase + Squash（保持历史干净）

适合想要线性历史的团队。

```bash
git checkout main
git pull origin main

# 对每个分支进行 rebase
git checkout feature/smart-parser
git rebase main
git push -f origin feature/smart-parser

# 然后合并并压缩提交
git checkout main
git merge --squash feature/smart-parser
git commit -m "Feature: Layout-Aware 文档解析优化

- 引入 Marker/MarkItDown 智能解析
- 优化表格提取逻辑
- 精准剔除参考文献"

# 重复其他分支...
```

---

## ⚠️ 合并冲突处理

### 常见冲突文件

根据各分支修改的文件，预计以下文件可能冲突：

1. **config/config.yaml**

   - 成员 A、B、D 都可能修改
   - 解决方案：手动合并所有配置项

2. **pdf_extractor.py**

   - 成员 B、C 都会修改
   - 解决方案：确保图片提取和智能解析逻辑兼容

3. **concept_deduplicator.py**

   - 成员 E 重构
   - 解决方案：保留新的 BGE-M3 实现

4. **enhanced_pipeline.py**

   - 成员 A 修改 Prompt
   - 解决方案：保留 Qwen 优化后的版本

5. **requirements.txt**
   - 所有成员都可能添加依赖
   - 解决方案：合并所有新增依赖

### 冲突解决流程

```bash
# 1. 查看冲突文件
git status

# 2. 查看具体冲突内容
git diff

# 3. 手动编辑冲突文件
# 移除 <<<<<<, ======, >>>>>> 标记
# 保留需要的代码

# 4. 标记为已解决
git add <conflicted-file>

# 5. 完成合并
git commit -m "Fix: 解决合并冲突"

# 6. 运行测试确保功能正常
python -m pytest
```

---

## 🧪 合并后测试清单

### 必须通过的测试

```bash
# 1. 单元测试
python -m pytest tests/ -v

# 2. LLM 抽取测试（成员 A）
python -c "
from enhanced_pipeline import run_enhanced_pipeline
from config_loader import load_config

config = load_config()
config['llm.max_chunks'] = 3
concepts, relations = run_enhanced_pipeline(config=config)
assert len(concepts) > 0
assert len(relations) > 0
print('✓ LLM 抽取测试通过')
"

# 3. 图片提取测试（成员 B）
python -c "
from image_captioner import ImageCaptioner
captioner = ImageCaptioner()
result = captioner.caption_from_pdf('文献/test.pdf')
assert len(result) > 0
print('✓ 图片提取测试通过')
"

# 4. PDF 解析测试（成员 C）
python -c "
from pdf_extractor import PDFExtractor
extractor = PDFExtractor()
text = extractor.extract_from_file('文献/test.pdf')
assert '参考文献' not in text  # 确保参考文献被剔除
print('✓ PDF 解析测试通过')
"

# 5. Embedding 测试（成员 E）
python -c "
from concept_deduplicator import ConceptDeduplicator
dedup = ConceptDeduplicator()
assert dedup.embedding_provider.model_name == 'BAAI/bge-m3'
print('✓ BGE-M3 Embedding 测试通过')
"

# 6. GraphRAG 测试（成员 D）
python -c "
from graph_summarizer import GraphSummarizer
summarizer = GraphSummarizer()
communities = summarizer.detect_communities()
assert len(communities) > 0
print('✓ GraphRAG 测试通过')
"

# 7. 端到端测试
python main.py --test-mode
```

---

## 📊 合并依赖关系图

```
                    main
                     ↓
         ┌───────────┴───────────┐
         ↓                       ↓
   smart-parser            llm-upgrade
    (成员 C)                (成员 A)
         ↓                       ↓
         └───────────┬───────────┘
                     ↓
              bge-embedding
               (成员 E)
                     ↓
         ┌───────────┴───────────┐
         ↓                       ↓
    multimodal              agent-logic
     (成员 B)                (成员 D)
         ↓                       ↓
         └───────────┬───────────┘
                     ↓
                   main
```

**建议合并顺序**：C → A → E → B → D

**原因**：

1. C（smart-parser）是基础，为其他功能提供高质量输入
2. A（llm-upgrade）是核心抽取逻辑
3. E（bge-embedding）依赖抽取结果进行对齐
4. B（multimodal）依赖 C 的解析框架
5. D（agent-logic）是最高层的应用逻辑

---

## 🚀 快速合并脚本（自动化）

创建自动化合并脚本：

```bash
#!/bin/bash
# merge_all_features.sh

set -e  # 遇到错误立即退出

echo "🔄 开始合并所有功能分支..."

# 切换到 main
git checkout main
git pull origin main

# 定义合并顺序
BRANCHES=(
    "feature/smart-parser"
    "feature/llm-upgrade"
    "feature/bge-embedding"
    "feature/multimodal"
    "feature/agent-logic"
)

# 逐个合并
for branch in "${BRANCHES[@]}"; do
    echo "📦 正在合并 $branch..."

    # 尝试合并
    if git merge origin/$branch --no-ff -m "Merge: $branch"; then
        echo "✓ $branch 合并成功"

        # 运行测试
        echo "🧪 运行测试..."
        if python -m pytest tests/ -k $(basename $branch); then
            echo "✓ 测试通过"
        else
            echo "❌ 测试失败，回滚合并"
            git reset --hard HEAD^
            exit 1
        fi
    else
        echo "⚠️  $branch 有冲突，需要手动解决"
        echo "请解决冲突后运行："
        echo "  git add ."
        echo "  git commit"
        echo "  ./merge_all_features.sh"
        exit 1
    fi

    echo ""
done

echo "🎉 所有功能分支合并完成！"
echo "📤 推送到远程..."
git push origin main

echo "✅ 完成！"
```

使用方法：

```bash
chmod +x merge_all_features.sh
./merge_all_features.sh
```

---

## 📝 合并后的版本记录

在 `CHANGELOG.md` 中记录：

```markdown
# Changelog

## [2.0.0] - 2024-11-29

### 🎉 重大升级

#### 成员 A: LLM 推理升级

- ✨ 升级模型至 Qwen2.5-Coder-14B
- ✨ 重写 Prompt 强制 JSON Schema 输出
- ✨ JSON 解析成功率从 75% 提升至 97%

#### 成员 B: 多模态支持

- ✨ 新增图片提取功能
- ✨ 集成 Qwen2-VL 生成图片描述
- ✨ 图表信息可参与关系抽取

#### 成员 C: 智能文档解析

- ✨ 集成 Marker/MarkItDown
- ✨ 表格数据正确解析率提升至 95%
- ✨ 精准剔除参考文献

#### 成员 D: Agentic Workflow

- ✨ LLM 二次校验三元组
- ✨ GraphRAG 社区摘要
- ✨ 新增主题节点类型

#### 成员 E: Embedding 升级

- ✨ 升级至 BGE-M3
- ✨ 中英实体对齐准确率 100%
- ✨ 混合检索支持

### 📊 性能提升

- 概念抽取准确率: 70% → 85%
- 关系抽取准确率: 65% → 82%
- PDF 解析质量: 60% → 95%
- 实体对齐准确率: 80% → 100%
```

---

## ⚡ 紧急回滚方案

如果合并后出现严重问题：

```bash
# 查看合并历史
git log --oneline --graph

# 回滚到合并前（假设合并提交是 abc123）
git reset --hard <合并前的commit-hash>

# 或者创建回滚提交（更安全）
git revert -m 1 <merge-commit-hash>

# 推送回滚
git push origin main -f  # 谨慎使用 -f
```

---

## 🎯 最佳实践建议

1. **合并前备份**

   ```bash
   git tag backup-before-merge-v2.0
   git push origin backup-before-merge-v2.0
   ```

2. **使用 Pull Request**

   - 在 GitHub 上创建 PR
   - Code Review
   - CI/CD 自动测试通过后再合并

3. **保持沟通**

   - 合并前开会同步进度
   - 明确各自修改的文件范围
   - 提前识别潜在冲突

4. **分阶段发布**
   - 先合并到 `develop` 分支测试
   - 稳定后再合并到 `main`
   - 使用 Git Flow 工作流

---

**祝合并顺利！** 🚀
