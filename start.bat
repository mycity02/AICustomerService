@echo off
chcp 65001 >nul
echo ========================================
echo   AI瀹㈡湇绯荤粺 - 涓€閿惎鍔?
echo ========================================
echo.

echo [1/2] 鍚姩鍚庣鏈嶅姟...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'e:\Project\AICustomerService\backend\venv\Scripts\python.exe' -ArgumentList 'e:\Project\AICustomerService\backend\main.py' -WorkingDirectory 'e:\Project\AICustomerService\backend'"

timeout /t 3 /nobreak >nul

echo [2/2] 鍚姩鍓嶇鏈嶅姟...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev' -WorkingDirectory 'e:\Project\AICustomerService\frontend'"

echo.
echo ========================================
echo   鍚姩瀹屾垚锛?
echo   鍚庣: http://localhost:8000
echo   鍓嶇: http://localhost:5173
echo   API鏂囨。: http://localhost:8000/api/docs
echo ========================================

