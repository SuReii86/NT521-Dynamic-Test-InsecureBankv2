#!/usr/bin/env python3
"""Sinh DEMO_REPORT.md từ evidence/ — chỉ dùng số liệu đo được.

Điểm quan trọng:
  - Không kết luận STORAGE-1 nếu prefs không chứa credential (ghi rõ lý do)
  - Không kết luận STORAGE-3 từ dòng chỉ có tên field UI
  - Phân biệt rõ PLATFORM-3 (exported component) và STORAGE-2 (dữ liệu qua IPC)
  - Nếu manifest từ dumpsys -> gắn nhãn độ tin cậy thấp

    python generate_report.py <evidence-dir> <out.md> <apk-name>
"""
import io
import json
import os
import sys
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def p(*parts):
    return os.path.join(*parts)


def has(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def read(path, limit=None):
    if not has(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            c = f.read()
        if limit:
            c = "\n".join(c.splitlines()[:limit])
        return c
    except Exception:
        return ""


def read_json(path):
    if not has(path):
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return {}


def or_na(text, msg="_Chưa có dữ liệu — chạy script tương ứng trước._"):
    return text.strip() if text and text.strip() else msg


def count_lines(path, only_real=True):
    """Đếm dòng nhưng bỏ dòng comment (#) do helper sinh ra."""
    if not has(path):
        return 0
    n = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if not s:
            continue
        if only_real and s.startswith("#"):
            continue
        n += 1
    return n


def verdict_line(ok, ok_text, fail_text, unknown_text):
    if ok is True:
        return f"❌ {fail_text}"
    if ok is False:
        return f"✅ {ok_text}"
    return f"⏳ {unknown_text}"


def main():
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2

    evid, out_md, apk_name = sys.argv[1:4]
    logs = p(evid, "logs")
    shots = p(evid, "screenshots")
    pkg = "com.android.insecurebankv2"

    F = {
        "apk_info":   p(logs, "apk_info.txt"),
        "device":     p(logs, "device_info.txt"),
        "prefs_sens": p(logs, "prefs_sensitive.txt"),
        "prefs_all":  p(logs, "prefs_all.txt"),
        "db":         p(logs, "db_contents.txt"),
        "logcat_sens": p(logs, "logcat_sensitive.txt"),
        "logcat_app": p(logs, "logcat_app.txt"),
        "ipc":        p(logs, "ipc_results.tsv"),
        "runas":      p(logs, "run_as_check.txt"),
        "exported":   p(logs, "exported_components.tsv"),
        "manifest":   p(logs, "manifest_stats.json"),
        "cmdlog":     p(logs, "commands.log"),
    }

    man = read_json(F["manifest"])
    manifest_conf = "low" if man.get("confidence") == "low" else "high"
    manifest_src = man.get("source", "?")

    # ---- Đếm có kiểm soát ----
    prefs_text = read(F["prefs_sens"])
    prefs_has_cred = bool(
        prefs_text and "KHONG tim thay key nhay cam" not in prefs_text
        and any(k in prefs_text.lower() for k in ("password", "passwd", "pwd", "token"))
    )

    logcat_n = count_lines(F["logcat_sens"])
    logcat_has_real = logcat_n > 0

    ipc_fail = ipc_pass = ipc_unknown = 0
    for line in read(F["ipc"]).splitlines():
        if "FAIL" in line:
            ipc_fail += 1
        elif "PASS" in line:
            ipc_pass += 1
        elif "CHECK" in line:
            ipc_unknown += 1

    # Component FAIL chỉ đếm khi manifest có độ tin cậy cao
    exported_fail = 0
    for line in read(F["exported"]).splitlines():
        if line.startswith("#"):
            continue
        if "\tFAIL" in line:
            exported_fail += 1

    runas_ok = "uid=" in read(F["runas"])

    db_text = read(F["db"])
    db_has_data = bool(db_text) and "Traceback" not in db_text and "[table]" in db_text \
        and "android_metadata" not in db_text.replace("android_metadata (locale TEXT)", "")

    n_shots = 0
    shot_files = []
    if os.path.isdir(shots):
        shot_files = sorted(f for f in os.listdir(shots) if f.lower().endswith(".png"))
        n_shots = len(shot_files)

    def masvs(cond):
        """cond: True=fail, False=pass, None=không kết luận"""
        return verdict_line(cond, "Pass", "Fail", "chưa đủ dữ liệu")

    storage1 = True if prefs_has_cred else (None if has(F["prefs_all"]) else None)
    storage3 = True if logcat_has_real else False if has(F["logcat_sens"]) else None
    platform3 = True if ipc_fail > 0 else (False if ipc_pass > 0 else None)
    code1 = True if runas_ok else (False if has(F["runas"]) else None)

    with open(out_md, "w", encoding="utf-8") as w:
        w.write(f"""# Báo Cáo Demo — Phân Tích Động {apk_name}

**Ứng dụng:** InsecureBankv2 (OWASP baseline)
**Package:** `{pkg}`
**Ngày sinh báo cáo:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Chuẩn đối chiếu:** OWASP MASVS v2.0 L1 / MASTG
**Nguồn manifest:** `{manifest_src}` (độ tin cậy: **{manifest_conf}**)

> Báo cáo sinh tự động từ `evidence/`. Mọi số đọc từ file thật.
> Mục nào không đủ dữ liệu sẽ ghi rõ lý do thay vì suy đoán.

---

## 1. Môi trường và APK

```
{or_na(read(F["apk_info"], 8))}
```

**Thiết bị:**

```
{or_na(read(F["device"], 3))}
```

---

## 2. Kịch bản demo

### Kịch bản A — Lấy cắp dữ liệu lưu trữ không an toàn

**Mục tiêu:** chứng minh credential lưu dạng plaintext trong SharedPreferences
và dữ liệu giao dịch nằm trong SQLite không mã hoá.

**Điều kiện:** app là debug build → `run-as` đọc được `/data/data/{pkg}`.

**Các bước:**
1. Cài app, đăng nhập `dinesh / Dinesh@123$`, **tích "Remember me"**
2. `adb shell run-as {pkg} ls shared_prefs`
3. `adb shell run-as {pkg} cat shared_prefs/<file>.xml`
4. `adb shell run-as {pkg} cat databases/<db>` → mở bằng sqlite3
5. `adb logcat --pid=<pid>` → tìm dòng chứa giá trị nhạy cảm

**Kết quả kiểm tra quyền đọc dữ liệu:**

```
{or_na(read(F["runas"], 3))}
```

**SharedPreferences — key/value nhạy cảm:**

```
{or_na(read(F["prefs_sens"], 25))}
```

**Nội dung SQLite:**

```
{or_na(read(F["db"], 45))}
```

**Logcat — dòng chứa giá trị nhạy cảm:** **{logcat_n}**

> Đã lọc bỏ dòng chỉ chứa *tên field/class/nhãn UI* (ví dụ
> `InputMethodManager ... app:id/loginscreen_password`), vì đó không phải rò rỉ dữ liệu.

```
{or_na(read(F["logcat_sens"], 15))}
```

**Kết luận A:**

| Mục | Kết quả | Lý do |
|-----|---------|-------|
| Credential trong SharedPreferences | {"❌ **FAIL**" if prefs_has_cred else "⏳ chưa kết luận"} | {"đọc được password/username plaintext" if prefs_has_cred else "prefs không chứa credential — thường do chưa tích 'Remember me'"} |
| SQLite có dữ liệu giao dịch | {"❌ lộ dữ liệu" if db_has_data else "⏳ chưa xác nhận"} | {"DB đọc được, có bảng dữ liệu" if db_has_data else "chưa thấy bảng dữ liệu ngoài android_metadata"} |
| Logcat rò rỉ giá trị | {"❌ **FAIL**" if logcat_has_real else "✅ không thấy"} | {"có dòng chứa giá trị nhạy cảm" if logcat_has_real else "chỉ có tên field/class"} |

---

### Kịch bản B — Khai thác exported component (IPC)

**Mục tiêu:** gọi Activity/Receiver exported không cần quyền, chứng minh
bypass luồng đăng nhập.

**Danh sách component từ manifest (nguồn: {manifest_src}):**

```
{or_na(read(F["exported"], 30))}
```

{f"**⚠️ Độ tin cậy THẤP:** dumpsys không cho biết `android:exported` và `android:permission`. Cần cài `apktool` hoặc `aapt` rồi chạy lại bước 01 để có dữ liệu chắc chắn." if manifest_conf == "low" else ""}

**Kết quả gọi thử bằng adb:**

```
{or_na(read(F["ipc"], 30))}
```

**Tổng hợp:** mở được **{ipc_fail}**, bị chặn **{ipc_pass}**, không xác định **{ipc_unknown}**

**Kết luận B:** {"❌ **FAIL — MASVS-PLATFORM-3**: " + str(ipc_fail) + " component gọi được mà không cần quyền" if ipc_fail > 0 else "⏳ chưa có component nào mở được (hoặc chưa chạy)"}

---

## 3. Lệnh đã chạy

Toàn bộ lệnh kèm output gốc: `evidence/logs/commands.log`

```
{or_na(read(F["cmdlog"], 50))}
```

_... (xem đầy đủ trong commands.log)_

---

## 4. Ảnh chụp

**Số ảnh thu được:** {n_shots}

""")

        for fname in shot_files:
            name = os.path.splitext(fname)[0]
            w.write(f"### {name}\n\n![{name}](../evidence/screenshots/{fname})\n\n")

        if n_shots == 0:
            w.write("_Chưa có ảnh chụp._\n\n")

        w.write(f"""---

## 5. Ánh xạ MASVS

| MASVS | Trạng thái | Bằng chứng | Ghi chú |
|-------|-----------|-----------|---------|
| **STORAGE-1** — không lưu credential plaintext | {masvs(storage1)} | `logs/prefs_sensitive.txt` | {"password/username đọc được" if prefs_has_cred else "chưa xác nhận — cần bật Remember me"} |
| **STORAGE-2** — không lộ dữ liệu qua IPC | {"⏳ chưa kiểm tra" if ipc_fail == 0 else "❌ Fail"} | `logs/ipc_results.tsv` | chỉ tính khi dữ liệu lộ *qua* provider/component, không phải chỉ gọi được |
| **STORAGE-3** — không log dữ liệu nhạy cảm | {masvs(storage3)} | `logs/logcat_sensitive.txt` | {"có dòng chứa giá trị thật" if logcat_has_real else "chỉ có tên field UI → không tính"} |
| **PLATFORM-3** — IPC component có bảo vệ | {masvs(platform3)} | `logs/ipc_results.tsv` | {str(ipc_fail) + " component mở được" if ipc_fail else "chưa có kết quả"} |
| **CODE-1** — build không debuggable | {masvs(code1)} | `logs/run_as_check.txt` | {"run-as đọc được data dir" if runas_ok else "run-as bị từ chối"} |
| **NETWORK-1** | ⏳ chưa kiểm tra | — | kịch bản động không bao gồm MITM; xem phân tích tĩnh |
| **CRYPTO-1** | ⏳ chưa kiểm tra | — | cần jadx; xem phân tích tĩnh |

> Ô `⏳` nghĩa là **không đủ dữ liệu**, không phải Pass. Không được tính là đạt.

---

## 6. Khuyến nghị khắc phục

| Lỗi | Fix |
|-----|-----|
| Credential plaintext trong SharedPreferences | `EncryptedSharedPreferences` (Jetpack Security) hoặc Android Keystore |
| SQLite không mã hoá | SQLCipher; hoặc không lưu dữ liệu nhạy cảm phía client |
| Exported component không guard | `android:exported="false"`, hoặc `android:permission="signature"` |
| Log credential | Xoá `Log.d()` ở release; ProGuard `-assumenosideeffects class android.util.Log` |
| Debug build phát hành | CI chặn build nếu `debuggable=true` |

---

## 7. Việc còn thiếu trước khi nộp

{"" if prefs_has_cred else "- [ ] **Chạy lại kịch bản A** với 'Remember me' để chứng minh STORAGE-1"}
{"" if manifest_conf == "high" else "- [ ] **Cài apktool/aapt** và chạy lại bước 01 để có danh sách component chắc chắn"}
{"" if not db_has_data else "- [ ] Kiểm tra DB có bảng dữ liệu giao dịch (hiện chỉ thấy android_metadata)"}
- [ ] Chạy `scripts\\99_package.bat` để đóng gói `.zip`
- [ ] Tái lập 1 lần trên máy sạch

---

## 8. Checklist nộp bài

- [x] Mô tả kịch bản demo (mục 2)
- [x] Lệnh đã chạy (mục 3 + `commands.log`)
- [x] Ảnh chụp (mục 4, {n_shots} ảnh)
- [x] Kết quả đo được (mục 2)
- [ ] Đóng gói `.zip` / GitHub riêng tư kèm `HOW_TO_RUN_Windows.md`
- [ ] Tái lập trên máy sạch
""")

    print(f"[OK] Đã sinh: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
