#!/bin/bash
# 自动安装依赖
pip install -r requirements.txt

# 创建模型目录
mkdir -p models/uer-gpt2

# 启动后端服务
uvicorn app:app --host 0.0.0.0 --port 8000 &

# 启动前端界面
streamlit run streamlit_app.py