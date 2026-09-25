@echo off
setlocal

set "OUTPUT_DIR=%~1"

if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=dist"

pyinstaller ^
    --onefile ^
    --name mng ^
    --console ^
    --distpath "%OUTPUT_DIR%" ^
    main.py

echo Built mng ^> %OUTPUT_DIR%\mng.exe