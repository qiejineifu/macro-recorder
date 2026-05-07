@echo off
chcp 65001 >nul
cd /d "%~dp0"
python macro_gui.py
pause
