#!/bin/bash

# 代码实践平台 - 启动脚本

set -e

echo "=========================================="
echo "  代码实践平台 - 启动"
echo "=========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装"
    exit 1
fi

# 检查Java（JPlag需要）
if ! command -v java &> /dev/null; then
    echo "[警告] 未找到Java，查重功能将不可用"
    echo "请安装JDK 17+：sudo apt install openjdk-17-jdk"
fi

# 检查JPlag
if [ ! -f "jplag-5.1.0.jar" ]; then
    echo "[提示] 未找到JPlag，正在下载..."
    curl -L -o jplag-5.1.0.jar https://github.com/jplag/JPlag/releases/download/v5.1.0/jplag-5.1.0.jar
fi

# 检查.env
if [ ! -f ".env" ]; then
    echo "[提示] 未找到.env文件，从模板创建"
    cp .env.example .env
    echo "[重要] 请编辑 .env 文件，填写DEEPSEEK_API_KEY"
fi

# 安装后端依赖
echo "[1/4] 安装后端依赖..."
cd backend
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
cd ..

# 创建必要目录
echo "[2/4] 创建数据目录..."
mkdir -p data submissions jplag-results exports

# 启动后端
echo "[3/4] 启动后端服务..."
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 启动前端
echo "[4/4] 启动前端服务..."
cd frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  启动完成！"
echo ""
echo "  学生端: http://localhost:8080"
echo "  教师端: http://localhost:8080/teacher.html"
echo "  API文档: http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/health"
echo ""
echo "  后端PID: $BACKEND_PID"
echo "  前端PID: $FRONTEND_PID"
echo ""
echo "  按 Ctrl+C 停止服务"
echo "=========================================="

# 等待中断
trap "echo ''; echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
