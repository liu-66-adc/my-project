@echo off
chcp 65001 >nul
echo ==========================================
echo   代码实践平台 - 启动
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.11+
    pause
    exit /b 1
)

REM 检查Java
java -version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到Java，查重功能将不可用
    echo 请安装JDK 17+
)

REM 检查JPlag
if not exist "jplag-5.1.0.jar" (
    echo [提示] 未找到JPlag，正在下载...
    powershell -Command "Invoke-WebRequest -Uri https://github.com/jplag/JPlag/releases/download/v5.1.0/jplag-5.1.0.jar -OutFile jplag-5.1.0.jar"
)

REM 检查.env
if not exist ".env" (
    echo [提示] 未找到.env文件，从模板创建
    copy .env.example .env
    echo [重要] 请编辑 .env 文件，填写DEEPSEEK_API_KEY
)

REM 创建目录
if not exist "data" mkdir data
if not exist "submissions" mkdir submissions
if not exist "jplag-results" mkdir jplag-results
if not exist "exports" mkdir exports

REM 安装后端依赖
echo [1/4] 安装后端依赖...
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
cd ..

REM 启动后端
echo [2/4] 启动后端服务...
cd backend
start "后端服务" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
cd ..

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
echo [3/4] 启动前端服务...
cd frontend
start "前端服务" cmd /k "python -m http.server 8080"
cd ..

echo.
echo ==========================================
echo   启动完成！
echo.
echo   学生端: http://localhost:8080
echo   教师端: http://localhost:8080/teacher.html
echo   API文档: http://localhost:8000/docs
echo   健康检查: http://localhost:8000/health
echo.
echo   [注意] 请确保已配置DEEPSEEK_API_KEY
echo ==========================================
pause
