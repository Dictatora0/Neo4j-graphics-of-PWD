#!/bin/bash
# 多模态图片提取功能设置脚本

echo "================================"
echo "多模态图片提取功能设置"
echo "================================"

# 检查Ollama是否运行
if ! pgrep -x "ollama" > /dev/null; then
    echo "❌ Ollama未运行，请先启动: ollama serve"
    exit 1
fi

echo "✅ Ollama运行中"

# 检查是否已安装llava模型
if ollama list | grep -q "llava"; then
    echo "✅ LLaVA模型已安装"
else
    echo ""
    echo "📥 下载LLaVA视觉语言模型..."
    echo "   模型大小: 约4.7GB"
    echo "   用途: 图片描述生成"
    echo ""
    read -p "是否现在下载？(y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "下载中..."
        ollama pull llava:7b
        
        if [ $? -eq 0 ]; then
            echo "✅ LLaVA模型下载成功"
        else
            echo "❌ 下载失败，请检查网络连接"
            exit 1
        fi
    else
        echo "⚠️  跳过下载，图片描述功能将无法使用"
        echo "   稍后可运行: ollama pull llava:7b"
        exit 0
    fi
fi

# 测试VLM
echo ""
echo "🧪 测试VLM功能..."

python3.10 << 'EOF'
import sys
sys.path.insert(0, '.')

try:
    from multimodal_extractor import VisionLanguageModel
    
    print("✅ multimodal_extractor模块可用")
    
    # 初始化VLM
    vlm = VisionLanguageModel(
        provider='ollama',
        model='llava:7b',
        ollama_host='http://localhost:11434'
    )
    
    print("✅ VLM初始化成功")
    print("")
    print("=" * 50)
    print("🎉 多模态功能设置完成！")
    print("=" * 50)
    print("")
    print("功能说明:")
    print("  ✅ 从PDF自动提取图片（尺寸>300px）")
    print("  ✅ 使用LLaVA生成专业图片描述")
    print("  ✅ 将图片知识融入知识图谱")
    print("")
    print("配置文件: config/config.yaml")
    print("  enable_image_captions: true")
    print("  caption_model: llava:7b")
    print("")
    print("运行pipeline: ./start.sh")
    
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请检查multimodal_extractor.py是否存在")
    sys.exit(1)
except Exception as e:
    print(f"❌ VLM初始化失败: {e}")
    print("请确保Ollama服务正常运行")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 测试失败，请检查错误信息"
    exit 1
fi

echo ""
echo "下一步: 运行 ./start.sh 开始提取"
