@echo off
REM ============================================================
REM  lib.bat — thư viện dùng chung (Windows)
REM  Không chạy trực tiếp. Các script khác gọi:
REM      call "%~dp0lib.bat" <verb> [args]
REM
REM  Verbs:
REM      init                       khởi tạo biến môi trường
REM      log  "msg"                 in [*]
REM      ok   "msg"                 in [+]
REM      warn "msg"                 in [!]
REM      err  "msg"                 in [-]
REM      need "tool"                kiểm tra tool, exit/b 1 nếu thiếu
REM      require_device             tìm emulator/device -> set DEVICE
REM      screenshot "name"          chụp màn hình vào evidence\screenshots
REM      record "step" "status" "detail" "evidence"
REM      wait_for_prefs [seconds]
REM ============================================================

if /i "%~1"=="init"            goto :init
if /i "%~1"=="log"             goto :log
if /i "%~1"=="ok"              goto :ok
if /i "%~1"=="warn"            goto :warn
if /i "%~1"=="err"             goto :err
if /i "%~1"=="need"            goto :need
if /i "%~1"=="require_device"  goto :require_device
if /i "%~1"=="screenshot"      goto :screenshot
if /i "%~1"=="record"          goto :record
if /i "%~1"=="wait_for_prefs"  goto :wait_for_prefs

echo [lib.bat] unknown verb: %~1 1>&2
exit /b 2

:init
set "ROOT=%~dp0.."
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "EVID=%ROOT%\evidence"
set "LOGS=%EVID%\logs"
set "SHOTS=%EVID%\screenshots"
set "CMDLOG=%LOGS%\commands.log"
set "RESULTS=%EVID%\results.jsonl"
if not defined PKG set "PKG=com.android.insecurebankv2"
if not defined PYTHON set "PYTHON=python"

if not exist "%LOGS%"  mkdir "%LOGS%"
if not exist "%SHOTS%" mkdir "%SHOTS%"
if not exist "%ROOT%\apk" mkdir "%ROOT%\apk"

REM Thêm platform-tools vào PATH nếu có ở vị trí mặc định
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
    set "PATH=%PATH%;%LOCALAPPDATA%\Android\Sdk\platform-tools"
)
if exist "%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe" (
    set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools"
)

set "DYN_LIB_LOADED=1"
exit /b 0

:log
echo [*] %~2
exit /b 0

:ok
echo [+] %~2
exit /b 0

:warn
echo [!] %~2
exit /b 0

:err
echo [-] %~2 1>&2
exit /b 0

:need
where %~2 >nul 2>&1
if errorlevel 1 (
    echo [-] Thiếu lệnh: %~2 1>&2
    exit /b 1
)
exit /b 0

:require_device
set "DEVICE="
where adb >nul 2>&1
if errorlevel 1 (
    echo [-] Thiếu adb ^(cài Android Platform Tools^) 1>&2
    exit /b 1
)

for /f "skip=1 tokens=1,2" %%a in ('adb devices 2^>nul') do (
    if /i "%%b"=="device" if not defined DEVICE set "DEVICE=%%a"
)

if not defined DEVICE (
    echo [-] Không có device/emulator ở trạng thái 'device' 1>&2
    echo     adb devices  --  phải thấy ^<serial^>  device 1>&2
    echo     Nếu thấy 'unauthorized': bật USB debugging và bấm Allow 1>&2
    exit /b 1
)

echo [+] Device: %DEVICE%
exit /b 0

:screenshot
set "SHOTNAME=%~2"
set "SHOTPATH=%SHOTS%\%SHOTNAME%.png"
del /q "%SHOTPATH%" 2>nul
adb shell screencap -p /sdcard/_dyn_shot.png >nul 2>&1
adb pull /sdcard/_dyn_shot.png "%SHOTPATH%" >nul 2>&1
adb shell rm -f /sdcard/_dyn_shot.png >nul 2>&1
if exist "%SHOTPATH%" (
    echo [+] Screenshot: evidence\screenshots\%SHOTNAME%.png
    exit /b 0
)
echo [!] Không chụp được screenshot: %SHOTNAME%
exit /b 1

:record
"%PYTHON%" "%ROOT%\scripts\helpers\record_result.py" "%RESULTS%" "%~2" "%~3" "%~4" "%~5"
exit /b 0

:wait_for_prefs
set "WAITSECS=%~2"
if not defined WAITSECS set "WAITSECS=120"
set /a ELAPSED=0
:wait_loop
adb shell "run-as %PKG% ls shared_prefs" 2>nul | findstr /i ".xml" >nul
if not errorlevel 1 exit /b 0
if %ELAPSED% GEQ %WAITSECS% exit /b 1
timeout /t 2 /nobreak >nul
set /a ELAPSED+=2
goto :wait_loop
