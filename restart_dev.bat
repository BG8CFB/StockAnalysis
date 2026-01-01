@echo off
echo 正在停止 Vite 开发服务器...
taskkill /F /IM node.exe 2>nul

echo 等待 2 秒...
timeout /t 2 /nobreak >nul

echo 清除缓存...
if exist "frontend\node_modules\.vite" rmdir /s /q "frontend\node_modules\.vite"
if exist "frontend\dist" rmdir /s /q "frontend\dist"

echo 重新启动开发服务器...
cd frontend
npm run dev

pause
