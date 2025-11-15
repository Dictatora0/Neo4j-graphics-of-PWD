#!/bin/bash
################################################################################
# 云服务器部署脚本
# 用途: 将项目部署到云服务器并运行知识图谱构建任务
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

################################################################################
# 配置变量 - 请根据您的云服务器修改
################################################################################

# 云服务器信息 (请修改为您的服务器信息)
SERVER_USER="root"                          # SSH 用户名
SERVER_HOST="your-server-ip"                # 服务器IP或域名
SERVER_PORT="22"                            # SSH 端口
REMOTE_DIR="/root/PWD"                      # 远程工作目录

# 本地项目路径
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

################################################################################
# 检查配置
################################################################################

check_config() {
    print_header "检查部署配置"
    
    if [ "$SERVER_HOST" = "your-server-ip" ]; then
        print_error "请先修改脚本中的服务器配置信息"
        print_info "编辑 deploy_to_cloud.sh，设置:"
        print_info "  - SERVER_USER: SSH用户名"
        print_info "  - SERVER_HOST: 服务器IP"
        print_info "  - SERVER_PORT: SSH端口"
        print_info "  - REMOTE_DIR: 远程目录"
        exit 1
    fi
    
    print_success "配置检查通过"
}

################################################################################
# 测试SSH连接
################################################################################

test_ssh() {
    print_header "测试SSH连接"
    
    if ssh -p $SERVER_PORT -o ConnectTimeout=10 $SERVER_USER@$SERVER_HOST "echo 'SSH连接成功'" > /dev/null 2>&1; then
        print_success "SSH连接正常"
    else
        print_error "SSH连接失败"
        print_info "请检查:"
        print_info "  1. 服务器IP和端口是否正确"
        print_info "  2. SSH密钥是否已配置"
        print_info "  3. 服务器防火墙是否开放SSH端口"
        exit 1
    fi
}

################################################################################
# 上传项目文件
################################################################################

upload_files() {
    print_header "上传项目文件"
    
    print_info "创建远程目录..."
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "mkdir -p $REMOTE_DIR"
    
    print_info "上传项目文件 (排除大文件和缓存)..."
    rsync -avz --progress \
        --exclude 'output/' \
        --exclude 'cache/' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        --exclude '.git/' \
        --exclude 'venv/' \
        --exclude '.DS_Store' \
        -e "ssh -p $SERVER_PORT" \
        "$LOCAL_DIR/" \
        "$SERVER_USER@$SERVER_HOST:$REMOTE_DIR/"
    
    print_success "文件上传完成"
}

################################################################################
# 安装依赖
################################################################################

install_dependencies() {
    print_header "安装服务器依赖"
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "bash -s" << 'ENDSSH'
        set -e
        
        echo "更新系统包..."
        apt-get update -qq
        
        echo "安装Python3和pip..."
        apt-get install -y python3 python3-pip python3-venv
        
        echo "安装Ollama..."
        if ! command -v ollama &> /dev/null; then
            curl -fsSL https://ollama.ai/install.sh | sh
        else
            echo "Ollama已安装"
        fi
        
        echo "启动Ollama服务..."
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep 5
        
        echo "拉取llama3.2:3b模型..."
        ollama pull llama3.2:3b
        
        echo "依赖安装完成"
ENDSSH
    
    print_success "依赖安装完成"
}

################################################################################
# 安装Python依赖
################################################################################

install_python_deps() {
    print_header "安装Python依赖"
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "bash -s" << ENDSSH
        set -e
        cd $REMOTE_DIR
        
        echo "创建虚拟环境..."
        python3 -m venv venv
        
        echo "安装Python包..."
        source venv/bin/activate
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
        
        echo "Python依赖安装完成"
ENDSSH
    
    print_success "Python依赖安装完成"
}

################################################################################
# 运行任务
################################################################################

run_task() {
    print_header "启动知识图谱构建任务"
    
    print_info "任务将在后台运行，日志保存到 output/kg_builder.log"
    print_info "预计运行时间: 37.5分钟 (150块)"
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "bash -s" << ENDSSH
        set -e
        cd $REMOTE_DIR
        
        # 创建输出目录
        mkdir -p output
        
        # 激活虚拟环境并运行
        source venv/bin/activate
        
        # 后台运行任务
        nohup python main.py > output/run.log 2>&1 &
        
        # 保存进程ID
        echo \$! > output/task.pid
        
        echo "任务已启动，PID: \$(cat output/task.pid)"
        echo "查看日志: tail -f $REMOTE_DIR/output/kg_builder.log"
ENDSSH
    
    print_success "任务已启动"
    print_info "使用以下命令查看进度:"
    print_info "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST 'tail -f $REMOTE_DIR/output/kg_builder.log'"
}

################################################################################
# 检查任务状态
################################################################################

check_status() {
    print_header "检查任务状态"
    
    ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "bash -s" << ENDSSH
        cd $REMOTE_DIR
        
        if [ -f output/task.pid ]; then
            PID=\$(cat output/task.pid)
            if ps -p \$PID > /dev/null 2>&1; then
                echo "✓ 任务正在运行 (PID: \$PID)"
                echo ""
                echo "最近日志:"
                tail -20 output/kg_builder.log
            else
                echo "✗ 任务已完成或已停止"
                echo ""
                echo "检查结果:"
                if [ -f output/statistics_report.txt ]; then
                    cat output/statistics_report.txt
                else
                    echo "未找到结果文件"
                fi
            fi
        else
            echo "未找到运行中的任务"
        fi
ENDSSH
}

################################################################################
# 下载结果
################################################################################

download_results() {
    print_header "下载结果文件"
    
    print_info "下载到本地 output/ 目录..."
    
    rsync -avz --progress \
        -e "ssh -p $SERVER_PORT" \
        "$SERVER_USER@$SERVER_HOST:$REMOTE_DIR/output/" \
        "$LOCAL_DIR/output/"
    
    print_success "结果下载完成"
    print_info "查看结果: cat output/statistics_report.txt"
}

################################################################################
# 清理远程文件
################################################################################

cleanup() {
    print_header "清理远程文件"
    
    read -p "确认删除远程目录 $REMOTE_DIR? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST "rm -rf $REMOTE_DIR"
        print_success "远程文件已清理"
    else
        print_info "取消清理"
    fi
}

################################################################################
# 主菜单
################################################################################

show_menu() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  云服务器部署菜单"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  1) 完整部署 (上传+安装+运行)"
    echo "  2) 仅上传文件"
    echo "  3) 仅安装依赖"
    echo "  4) 启动任务"
    echo "  5) 查看任务状态"
    echo "  6) 下载结果"
    echo "  7) 清理远程文件"
    echo "  8) 退出"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

################################################################################
# 主程序
################################################################################

main() {
    print_header "云服务器部署工具"
    
    # 检查配置
    check_config
    
    # 如果提供了命令行参数
    if [ $# -gt 0 ]; then
        case "$1" in
            deploy)
                test_ssh
                upload_files
                install_dependencies
                install_python_deps
                run_task
                ;;
            upload)
                test_ssh
                upload_files
                ;;
            install)
                test_ssh
                install_dependencies
                install_python_deps
                ;;
            run)
                test_ssh
                run_task
                ;;
            status)
                test_ssh
                check_status
                ;;
            download)
                test_ssh
                download_results
                ;;
            cleanup)
                test_ssh
                cleanup
                ;;
            *)
                echo "用法: $0 {deploy|upload|install|run|status|download|cleanup}"
                exit 1
                ;;
        esac
        exit 0
    fi
    
    # 交互式菜单
    while true; do
        show_menu
        read -p "请选择操作 [1-8]: " choice
        
        case $choice in
            1)
                test_ssh
                upload_files
                install_dependencies
                install_python_deps
                run_task
                ;;
            2)
                test_ssh
                upload_files
                ;;
            3)
                test_ssh
                install_dependencies
                install_python_deps
                ;;
            4)
                test_ssh
                run_task
                ;;
            5)
                test_ssh
                check_status
                ;;
            6)
                test_ssh
                download_results
                ;;
            7)
                test_ssh
                cleanup
                ;;
            8)
                print_info "退出"
                exit 0
                ;;
            *)
                print_error "无效选择"
                ;;
        esac
        
        echo ""
        read -p "按回车继续..."
    done
}

# 运行主程序
main "$@"
