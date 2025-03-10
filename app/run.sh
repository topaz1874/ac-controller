#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 安装依赖项
pip install -r requirements.txt

# 运行应用
python app.py

# 停用虚拟环境
deactivate 