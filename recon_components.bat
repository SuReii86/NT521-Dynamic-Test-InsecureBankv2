@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  01_recon_components.bat — Liệt kê component exported
REM
REM  Nguồn dữ liệu, theo thứ tự ưu tiên:
REM    1. apktool  -> apktool_output\AndroidManifest.xml  (XML thật)
REM    2. aapt     -> aapt dump xmltree                   (text)
REM    3. dumpsys  -> adb shell dumpsys package <pkg>     (trên thiết bị)
REM ============================================================

call "%~dp0lib.bat" init

echo.
echo ==================================================
echo  BUOC 1 - Trinh sat component exported
echo ==================================================
echo.

set "APK=%ROOT%\apk\insecurebankv2.apk"
if not exist "%APK%" (
    call "%~dp0lib.bat" err "Chua co apk\insecurebankv2.apk - chay 00_setup.bat"
    endlocal & exit /b 1
)

set "MANIFEST_JSON=%LOGS%\manifest_stats.json"
set "EXPORTED_TSV=%LOGS%\exported_components.tsv"

REM ---------- 1. apktool ----------
set "HAVE_APKTOOL=0"
where apktool >nul 2>&1 && set "HAVE_APKTOOL=1"

if "%HAVE_APKTOOL%"=="1" (
    call "%~dp0lib.bat" log "[1/3] apktool decode..."
    if exist "%ROOT%\work\apktool_output" rmdir /s /q "%ROOT%\work\apktool_output"
    mkdir "%ROOT%\work" 2>nul
    call apktool d "%APK%" -o "%ROOT%\work\apktool_output" -f
    if exist "%ROOT%\work\apktool_output\AndroidManifest.xml" (
        call "%~dp0lib.bat" ok "apktool_output\AndroidManifest.xml"
        "%PYTHON%" "%ROOT%\scripts\helpers\parse_manifest_xml.py" ^
            "%ROOT%\work\apktool_output\AndroidManifest.xml" > "%MANIFEST_JSON%" 2>nul
        if exist "%MANIFEST_JSON%" call "%~dp0lib.bat" ok "manifest_stats.json"
        goto :make_tsv
    ) else (
        call "%~dp0lib.bat" warn "apktool decode that bai - thu aapt"
    )
)

REM ---------- 2. aapt ----------
set "HAVE_AAPT=0"
where aapt >nul 2>&1 && set "HAVE_AAPT=1"
if "%HAVE_AAPT%"=="0" (
    where aapt2 >nul 2>&1 && set "HAVE_AAPT=1"
)

if "%HAVE_AAPT%"=="1" (
    call "%~dp0lib.bat" log "[1/3] aapt dump xmltree..."
    if exist "%LOGS%\manifest_dump.txt" del /q "%LOGS%\manifest_dump.txt"

    where aapt >nul 2>&1
    if not errorlevel 1 (
        aapt dump xmltree "%APK%" AndroidManifest.xml > "%LOGS%\manifest_dump.txt" 2>&1
    ) else (
        aapt2 dump xmltree --file AndroidManifest.xml "%APK%" > "%LOGS%\manifest_dump.txt" 2>&1
    )

    if exist "%LOGS%\manifest_dump.txt" (
        call "%~dp0lib.bat" ok "manifest_dump.txt"
        "%PYTHON%" "%ROOT%\scripts\helpers\parse_aapt_xmltree.py" ^
            "%LOGS%\manifest_dump.txt" > "%MANIFEST_JSON%" 2>nul
        if exist "%MANIFEST_JSON%" call "%~dp0lib.bat" ok "manifest_stats.json"
        goto :make_tsv
    )
)

REM ---------- 3. dumpsys ----------
call "%~dp0lib.bat" warn "Khong co apktool/aapt - doc tu dumpsys tren thiet bi"
call "%~dp0lib.bat" require_device
if errorlevel 1 (
    call "%~dp0lib.bat" err "Khong co ca thiet bi -> khong the liet ke component"
    call "%~dp0lib.bat" record "recon" "blocked" "no apktool/aapt/device" ""
    endlocal & exit /b 1
)

adb shell pm list packages 2>nul | findstr /i /c:"package:%PKG%" >nul
if errorlevel 1 (
    call "%~dp0lib.bat" log "Cai app..."
    adb install -r "%APK%"
)

adb shell dumpsys package %PKG% > "%LOGS%\dumpsys_package.txt" 2>&1
call "%~dp0lib.bat" ok "dumpsys_package.txt"
"%PYTHON%" "%ROOT%\scripts\helpers\parse_dumpsys.py" "%LOGS%\dumpsys_package.txt" > "%MANIFEST_JSON%" 2>nul
if exist "%MANIFEST_JSON%" call "%~dp0lib.bat" ok "manifest_stats.json (tu dumpsys)"

:make_tsv
REM ---------- Sinh TSV tóm tắt ----------
if exist "%MANIFEST_JSON%" (
    "%PYTHON%" "%ROOT%\scripts\helpers\manifest_to_tsv.py" "%MANIFEST_JSON%" > "%EXPORTED_TSV%" 2>nul
    if exist "%EXPORTED_TSV%" (
        call "%~dp0lib.bat" ok "exported_components.tsv"
        echo.
        type "%EXPORTED_TSV%"
    )

    REM Cảnh báo nếu nguồn là dumpsys (độ tin cậy thấp)
    findstr /c:"\"source\": \"dumpsys package\"" "%MANIFEST_JSON%" >nul 2>&1
    if not errorlevel 1 (
        echo.
        echo ================================================================
        call "%~dp0lib.bat" warn "DU LIEU MANIFEST CO DO TIN CAY THAP"
        echo ================================================================
        echo   Nguon: dumpsys package ^(khong co apktool/aapt^)
        echo   dumpsys KHONG cho biet android:exported va android:permission.
        echo   => cot verdict = UNKNOWN, KHONG dung de ket luan.
        echo.
        echo   Cai them de co du lieu that ^(chon 1^):
        echo     - apktool:   choco install apktool
        echo                  hoac tai apktool.jar + apktool.bat tu apktool.org
        echo     - Android SDK Build-Tools chua aapt.exe, them vao PATH
        echo.
        echo   Sau khi cai, chay lai: scripts\01_recon_components.bat
        echo ================================================================
        call "%~dp0lib.bat" record "recon" "low-confidence" "dumpsys fallback - install apktool/aapt" "logs/manifest_stats.json"
    ) else (
        call "%~dp0lib.bat" record "recon" "ok" "manifest parsed from apktool/aapt" "logs/exported_components.tsv"
    )
)

REM ---------- Driver: cài app + dumpsys ----------
call "%~dp0lib.bat" require_device
if not errorlevel 1 (
    call "%~dp0lib.bat" log "[2/3] Xac nhan tren thiet bi..."
    adb shell pm list packages 2>nul | findstr /i /c:"package:%PKG%" >nul
    if errorlevel 1 (
        call "%~dp0lib.bat" log "Cai app..."
        adb install -r "%APK%"
    )
    adb shell dumpsys package %PKG% > "%LOGS%\dumpsys_package.txt" 2>&1
    call "%~dp0lib.bat" ok "dumpsys_package.txt"

    REM ---------- Drozer (nếu có) ----------
    where drozer >nul 2>&1
    if not errorlevel 1 (
        call "%~dp0lib.bat" log "[3/3] Drozer..."
        adb forward tcp:31415 tcp:31415 >nul 2>&1
        (
            echo run app.package.attacksurface %PKG%
            echo run app.activity.info -a %PKG%
            echo run app.provider.info -a %PKG%
            echo run app.service.info -a %PKG%
            echo run app.broadcast.info -a %PKG%
            echo exit
        ) > "%LOGS%\drozer_commands.txt"
        call "%~dp0lib.bat" warn "Chay thu cong: adb forward tcp:31415 tcp:31415 ^&^& drozer console connect"
        echo     Dan lenh trong: logs\drozer_commands.txt
    )
    call "%~dp0lib.bat" record "recon" "ok" "components enumerated" "logs/exported_components.tsv"
)

echo.
call "%~dp0lib.bat" ok "Buoc 1 xong."
echo   Xem: type "%EXPORTED_TSV%"
echo   Tiep: scripts\02_storage_theft.bat
endlocal
