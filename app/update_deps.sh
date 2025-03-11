#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 更新pip
pip install --upgrade pip

# 更新依赖项
pip install -r requirements.txt --upgrade

# 显示已安装的包
pip list

echo "依赖项更新完成！" 