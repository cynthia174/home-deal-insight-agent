@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 正在启动 家装经营洞察 Agent...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
