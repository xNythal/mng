@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%~1"

if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=dist"

if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
) else (
    echo Warning: venv not found at %SCRIPT_DIR%venv — using system/active Python
)

pyinstaller ^
    --onefile ^
    --name mng ^
    --console ^
    --distpath "%OUTPUT_DIR%" ^
    main.py

echo Built mng ^> %OUTPUT_DIR%\mng.exe