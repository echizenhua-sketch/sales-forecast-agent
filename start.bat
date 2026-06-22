@echo off
REM 产销预测智能工作台 - 启动脚本
REM 同时启动后端API和前端页面

echo ================================================
echo 产销预测智能工作台 - v2.2.0
echo ================================================
echo.

echo [1/4] 启动后端API服务...
start "后端API" /MIN python -B -m uvicorn main:app --host 127.0.0.1 --port 8000
timeout /t 3 /nobreak >nul

echo [2/4] 检查API状态...
curl -s http://localhost:8000/api/health >nul
if %errorlevel%==0 (
    echo [成功] 后端API已启动 - http://localhost:8000
) else (
    echo [等待] API正在启动中...
    timeout /t 3 /nobreak >nul
)

echo [3/4] 启动并打开静态前端...
start "前端页面" /MIN cmd /c "cd /d %CD%\web && npm.cmd run dev"
timeout /t 1 /nobreak >nul
start http://127.0.0.1:4173/

echo [4/4] 系统已就绪
echo.
echo ================================================
echo 服务已启动
echo ================================================
echo.
echo 前端登录:  http://127.0.0.1:4173/login-v2.html
echo 工作台:    http://127.0.0.1:4173/dashboard-v2.html
echo API文档:   http://localhost:8000/docs
echo 健康检查:  http://localhost:8000/api/health
echo.
echo 按任意键关闭后端服务...
pause >nul

echo.
echo 正在关闭服务...
taskkill /FI "WINDOWTITLE eq 后端API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 前端页面*" /F >nul 2>&1

echo 服务已关闭
timeout /t 2 /nobreak >nul
