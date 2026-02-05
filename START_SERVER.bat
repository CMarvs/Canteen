@echo off
cls
echo ========================================
echo   🍽️ Online Canteen Server Starting...
echo ========================================
echo.
echo 🌐 Server will run at: http://localhost:8000
echo 📊 Database: NeonDB PostgreSQL (Connected)
echo.
echo ✅ READY TO USE:
echo    - Home Page: http://localhost:8000
echo    - Login: http://localhost:8000/index.html
echo    - Register: http://localhost:8000/register.html
echo.
echo 🔑 Test Accounts:
echo    Admin: admin@canteen / admin123
echo    User: user@demo / user123
echo.
echo ⚠️  Keep this window open while using the app
echo 🛑 Press CTRL+C to stop the server
echo ========================================
echo.
echo Starting server...
echo.

python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000

pause
