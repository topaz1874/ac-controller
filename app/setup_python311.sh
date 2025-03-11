#!/bin/bash

# 检查是否安装了Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11未安装，请先安装Python 3.11"
    echo "在macOS上，可以使用Homebrew安装："
    echo "brew install python@3.11"
    exit 1
fi

# 删除旧的虚拟环境
if [ -d "venv" ]; then
    echo "删除旧的虚拟环境..."
    rm -rf venv
fi

# 创建新的虚拟环境
echo "使用Python 3.11创建新的虚拟环境..."
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 更新pip
pip install --upgrade pip

# 安装依赖项
pip install -r requirements.txt

echo "Python 3.11环境设置完成！"
echo "使用 'source venv/bin/activate' 激活虚拟环境" 