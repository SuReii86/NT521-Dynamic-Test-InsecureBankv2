@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  04_generate_report.bat — Sinh báo cáo từ evidence
REM ============================================================

call "%~dp0lib.bat" init

echo.
echo ==================================================
echo  BUOC 4 - Sinh bao cao demo
echo ==================================================
echo.

set "REPORT=%ROOT%\docs\DEMO_REPORT.md"
if not exist "%ROOT%\docs" mkdir "%ROOT%\docs"

call "%~dp0lib.bat" log "Doc evidence va sinh bao cao..."

"%PYTHON%" "%ROOT%\scripts\helpers\generate_report.py" ^
    "%EVID%" ^
    "%REPORT%" ^
    "InsecureBankv2"

if exist "%REPORT%" (
    call "%~dp0lib.bat" ok "Bao cao: docs\DEMO_REPORT.md"
    echo.
    echo   Xem:  type "%REPORT%"
    echo   Hoac: start notepad "%REPORT%"
) else (
    call "%~dp0lib.bat" err "Sinh bao cao that bai"
    endlocal & exit /b 1
)

echo.
call "%~dp0lib.bat" ok "Buoc 4 xong."
echo   Dong goi: scripts\99_package.bat
endlocal
