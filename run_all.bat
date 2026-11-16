@echo off
setlocal
REM ============================================================
REM  run_all.bat — Chạy toàn bộ chuỗi phân tích động
REM
REM  scripts\run_all.bat
REM  scripts\run_all.bat --build
REM  scripts\run_all.bat --no-wait
REM ============================================================

call "%~dp0lib.bat" init

set "ARGS="
:parse
if "%~1"=="" goto :start
if /i "%~1"=="--build"   set "ARGS=!ARGS! --build"
if /i "%~1"=="--no-wait" set "ARGS=!ARGS! --no-wait"
shift
goto :parse

:start
echo.
echo ==================================================
echo  CHAY TOAN BO CHUOI PHAN TICH DONG
echo ==================================================
echo.

call "%~dp0\00_setup.bat" %ARGS%
if errorlevel 1 (
    call "%~dp0lib.bat" err "Buoc 0 that bai"
    endlocal & exit /b 1
)

call "%~dp0\01_recon_components.bat"
if errorlevel 1 (
    call "%~dp0lib.bat" err "Buoc 1 that bai"
    endlocal & exit /b 1
)

call "%~dp0\02_storage_theft.bat" %ARGS%
if errorlevel 1 (
    call "%~dp0lib.bat" err "Buoc 2 that bai"
    endlocal & exit /b 1
)

call "%~dp0\03_ipc_exploit.bat"
if errorlevel 1 (
    call "%~dp0lib.bat" err "Buoc 3 that bai"
    endlocal & exit /b 1
)

call "%~dp0\04_generate_report.bat"
if errorlevel 1 (
    call "%~dp0lib.bat" err "Buoc 4 that bai"
    endlocal & exit /b 1
)

echo.
echo ==================================================
echo  HOAN TAT
echo ==================================================
echo   Bao cao:   docs\DEMO_REPORT.md
echo   Bang chung: evidence\
echo   Dong goi:  scripts\99_package.bat
endlocal
