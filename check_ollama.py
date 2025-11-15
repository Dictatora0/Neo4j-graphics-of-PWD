#!/usr/bin/env python3
"""
Ollama健康检查和自动重启脚本
"""
import requests
import subprocess
import time
import sys

def check_ollama_health():
    """检查Ollama服务是否正常"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except:
        return False

def restart_ollama():
    """重启Ollama服务"""
    print("🔄 检测到Ollama服务异常，正在重启...")
    
    # 停止Ollama
    try:
        subprocess.run(['pkill', '-9', 'ollama'], check=False)
        time.sleep(2)
    except:
        pass
    
    # 启动Ollama
    try:
        subprocess.Popen(['ollama', 'serve'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        time.sleep(5)
        
        # 验证启动成功
        if check_ollama_health():
            print("✅ Ollama服务已重启")
            return True
        else:
            print("❌ Ollama重启失败")
            return False
    except Exception as e:
        print(f"❌ 重启失败: {e}")
        return False

def main():
    """主函数"""
    if check_ollama_health():
        print("✅ Ollama服务正常")
        sys.exit(0)
    else:
        print("⚠️  Ollama服务异常")
        if restart_ollama():
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
