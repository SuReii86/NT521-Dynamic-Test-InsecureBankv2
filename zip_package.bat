@echo off
setlocal
REM ============================================================
REM  99_package.bat — Đóng gói bài nộp thành .zip
REM
REM  scripts\99_package.bat
REM  scripts\99_package.bat --no-apk
REM ============================================================

call "%~dp0lib.bat" init

set "INCLUDE_APK=1"
if /i "%~1"=="--no-apk" set "INCLUDE_APK=0"

set "STAMP=%date:~-4%%date:~3,2%%date:~0,2%"
set "OUTDIR=%ROOT%\dist"
set "ZIP=%OUTDIR%\insecurebankv2-dynamic-analysis-%STAMP%.zip"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo.
echo ==================================================
echo  Dong goi bai nop
echo ==================================================
echo.

where 7z >nul 2>&1
if errorlevel 1 where powershell >nul 2>&1
if errorlevel 1 (
    call "%~dp0lib.bat" err "Can 7z hoac PowerShell de nen zip"
    endlocal & exit /b 1
)

set "TMPDIR=%TEMP%\dyn_pack_%RANDOM%"
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%\insecurebankv2-dynamic-analysis"
set "DEST=%TMPDIR%\insecurebankv2-dynamic-analysis"

call "%~dp0lib.bat" log "Copy script..."
xcopy /s /q /y "%ROOT%\scripts" "%DEST%\scripts\" >nul

call "%~dp0lib.bat" log "Copy tai lieu..."
if exist "%ROOT%\docs" xcopy /s /q /y "%ROOT%\docs" "%DEST%\docs\" >nul

call "%~dp0lib.bat" log "Copy bang chung..."
if exist "%ROOT%\evidence" xcopy /s /q /y "%ROOT%\evidence" "%DEST%\evidence\" >nul

if "%INCLUDE_APK%"=="1" (
    if exist "%ROOT%\apk\insecurebankv2.apk" (
        call "%~dp0lib.bat" log "Copy APK..."
        mkdir "%DEST%\apk" 2>nul
        copy /y "%ROOT%\apk\insecurebankv2.apk" "%DEST%\apk\" >nul
    )
)

if exist "%ROOT%\HOW_TO_RUN_WINDOWS.md" copy /y "%ROOT%\HOW_TO_RUN_WINDOWS.md" "%DEST%\" >nul
if exist "%ROOT%\README.md" copy /y "%ROOT%\README.md" "%DEST%\" >nul

REM Sinh manifest
(
    echo # Noi dung goi nop
    echo.
    echo Sinh luc: %date% %time%
    echo.
    echo ## Cau truc
    echo.
    dir /s /b "%DEST%" 2>nul
    echo.
    echo ## So lieu
    for /f %%C in ('dir /s /b /a-d "%DEST%\evidence" 2^>nul ^| find /c /v ""') do echo - So file bang chung: %%C
    for /f %%C in ('dir /b "%DEST%\evidence\screenshots\*.png" 2^>nul ^| find /c /v ""') do echo - So anh chup: %%C
    if exist "%DEST%\docs\DEMO_REPORT.md" (
        echo - Co bao cao demo: yes
    ) else (
        echo - Co bao cao demo: no
    )
) > "%DEST%\MANIFEST.md"

REM Nén
pushd "%TMPDIR%"
where 7z >nul 2>&1
if not errorlevel 1 (
    7z a -tzip "%ZIP%" insecurebankv2-dynamic-analysis >nul
) else (
    powershell -Command "Compress-Archive -Path 'insecurebankv2-dynamic-analysis' -DestinationPath '%ZIP%' -Force" >nul
)
popd

rmdir /s /q "%TMPDIR%"

if exist "%ZIP%" (
    call "%~dp0lib.bat" ok "Da tao: %ZIP%"
    echo.
    echo   Kiem tra noi dung:
    echo     7z l "%ZIP%"
    echo   hoac:
    echo     powershell Expand-Archive "%ZIP%" -DestinationPath test
    echo.
    echo   Nop bai: upload file .zip nay, hoac push len GitHub rieng tu.
    echo   Nho kiem tra: HOW_TO_RUN_WINDOWS.md co huong dan chay lai tu dau.
) else (
    call "%~dp0lib.bat" err "Nen zip that bai"
    endlocal & exit /b 1
)

endlocal
