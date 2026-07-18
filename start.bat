@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"
set "PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"

echo ========================================
echo   云岫茶坊 AI 茶叶销售系统 - Flask 一键启动
echo ========================================
echo.

if not exist "%PYTHON_EXE%" (
    echo [错误] 未找到后端虚拟环境: %PYTHON_EXE%
    exit /b 1
)

echo [1/2] 启动 Flask 后端服务...
start "云岫茶坊后端" /D "%BACKEND_DIR%" "%PYTHON_EXE%" "%BACKEND_DIR%\main.py"

timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务...
start "云岫茶坊前端" /D "%FRONTEND_DIR%" cmd /c npm run dev

echo.
echo ========================================
echo   启动完成
echo   后端: http://localhost:8000
echo   前端: http://localhost:5173
echo   路由清单: http://localhost:8000/api/docs
echo ========================================

endlocal
