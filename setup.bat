@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  00_setup.bat — Chuẩn bị môi trường Windows + APK InsecureBankv2
REM
REM  ./scripts/00_setup.bat            kiểm tra tool + hướng dẫn
REM  ./scripts/00_setup.bat --build    clone repo + build bằng gradlew
REM ============================================================

call "%~dp0lib.bat" init

echo.
echo ==================================================
echo  BUOC 0 - Chuan bi moi truong (Windows)
echo ==================================================
echo.

set "BUILD=0"
if /i "%~1"=="--build" set "BUILD=1"

REM ---------- 1. Kiểm tra tool ----------
call "%~dp0lib.bat" log "Kiem tra cong cu..."
set "MISSING=0"

for %%T in (adb java python) do (
    where %%T >nul 2>&1
    if errorlevel 1 (
        call "%~dp0lib.bat" err "%%T - CHUA CAI"
        set /a MISSING+=1
    ) else (
        call "%~dp0lib.bat" ok "%%T"
    )
)

REM aapt hoặc apktool — cần ít nhất 1 để đọc manifest
set "HAVE_AAPT=0"
set "HAVE_APKTOOL=0"
where aapt  >nul 2>&1 && set "HAVE_AAPT=1"
where aapt2 >nul 2>&1 && if "%HAVE_AAPT%"=="0" set "HAVE_AAPT=1"
where apktool >nul 2>&1 && set "HAVE_APKTOOL=1"

if "%HAVE_AAPT%"=="1"    call "%~dp0lib.bat" ok "aapt"
if "%HAVE_AAPT%"=="0"    call "%~dp0lib.bat" warn "aapt - chua co (can build-tools)"
if "%HAVE_APKTOOL%"=="1" call "%~dp0lib.bat" ok "apktool"
if "%HAVE_APKTOOL%"=="0" call "%~dp0lib.bat" warn "apktool - chua co (fallback dung dumpsys)"

if "%HAVE_AAPT%%HAVE_APKTOOL%"=="00" (
    echo.
    call "%~dp0lib.bat" warn "Khong co aapt/apktool -> se doc component bang 'dumpsys package' tren thiet bi"
    echo     Cai day du hon:
    echo       - Android SDK Build-Tools chua aapt.exe
    echo       - Hoac: choco install apktool
    echo.
)

REM ---------- 2. Device ----------
call "%~dp0lib.bat" log "Kiem tra thiet bi..."
call "%~dp0lib.bat" require_device
if errorlevel 1 (
    echo.
    echo   Khong co emulator. Voi VirtualBox Android VM:
    echo     1. Bat ADB over TCP trong VM:
    echo          setprop service.adb.tcp.port 5555
    echo          stop adbd ^& start adbd
    echo     2. Tren Windows:
    echo          adb connect 127.0.0.1:5555
    echo.
    call "%~dp0lib.bat" record "setup" "blocked" "no device" ""
) else (
    adb shell getprop ro.product.model        >> "%LOGS%\device_info.txt" 2>&1
    adb shell getprop ro.build.version.release >> "%LOGS%\device_info.txt" 2>&1
    adb shell getprop ro.build.version.sdk     >> "%LOGS%\device_info.txt" 2>&1
    call "%~dp0lib.bat" ok "device_info.txt"
)

REM ---------- 3. Lấy APK ----------
echo.
echo ==================================================
echo  APK InsecureBankv2
echo ==================================================

set "APK=%ROOT%\apk\insecurebankv2.apk"

if exist "%APK%" (
    call "%~dp0lib.bat" ok "Da co: apk\insecurebankv2.apk"
    goto :apk_info
)

echo Chua co APK. Hai cach:
echo.
echo   Cach A - tu build ^(khuyen nghi^):
echo     scripts\00_setup.bat --build
echo.
echo   Cach B - tai APK co san:
echo     https://github.com/dineshshetty/Android-InsecureBankv2/releases
echo     -> doi ten thanh apk\insecurebankv2.apk
echo.

if "%BUILD%"=="0" goto :end

REM ---------- Build ----------
where git >nul 2>&1
if errorlevel 1 (
    call "%~dp0lib.bat" err "Can git de build"
    goto :end
)

set "BUILDDIR=%ROOT%\.build"
if exist "%BUILDDIR%" rmdir /s /q "%BUILDDIR%"
mkdir "%BUILDDIR%"

call "%~dp0lib.bat" log "Clone repo..."
git clone --depth 1 https://github.com/dineshshetty/Android-InsecureBankv2.git "%BUILDDIR%\repo"
if errorlevel 1 (
    call "%~dp0lib.bat" err "Clone that bai"
    goto :end
)

pushd "%BUILDDIR%\repo\InsecureBankv2"
call "%~dp0lib.bat" log "Build (5-15 phut lan dau)..."
call gradlew.bat assembleDebug
if errorlevel 1 (
    popd
    call "%~dp0lib.bat" err "Build that bai - xem .build\repo\InsecureBankv2"
    goto :end
)
popd

for /r "%BUILDDIR%\repo\InsecureBankv2" %%F in (*.apk) do (
    echo %%F | findstr /i "outputs" >nul && if not defined FOUNDAPK set "FOUNDAPK=%%F"
)

if not defined FOUNDAPK (
    call "%~dp0lib.bat" err "Khong tim thay APK sau khi build"
    goto :end
)

copy /y "%FOUNDAPK%" "%APK%" >nul
call "%~dp0lib.bat" ok "APK: apk\insecurebankv2.apk"
call "%~dp0lib.bat" record "setup" "ok" "built apk" "apk/insecurebankv2.apk"

:apk_info
echo.
call "%~dp0lib.bat" log "Thong tin APK..."
(
    echo file    : insecurebankv2.apk
    echo size    : %~zAPK%
    echo sha256  :
) > "%LOGS%\apk_info.txt"
certutil -hashfile "%APK%" SHA256 | findstr /v ":" >> "%LOGS%\apk_info.txt" 2>nul

if "%HAVE_AAPT%"=="1" (
    aapt dump badging "%APK%" 2>nul | findstr /b "package:" >> "%LOGS%\apk_info.txt"
)
type "%LOGS%\apk_info.txt"
call "%~dp0lib.bat" record "apk" "ok" "apk present" "logs/apk_info.txt"

:end
echo.
call "%~dp0lib.bat" ok "Buoc 0 xong. Tiep theo: scripts\01_recon_components.bat"
endlocal
