# NT521-Dynamic-Test-InsecureBankv2
## Đánh giá khả năng tái lập

| Tiêu chí | Đánh giá | Ghi chú |
|---|---|---|
| Mã nguồn script | ✅ Tái lập được 100% | 5 script `.bat` + 10 helper `.py`, không phụ thuộc đường dẫn cố định (dùng `%~dp0` và `%ROOT%`) |
| APK baseline | ✅ Tái lập được | `insecurebankv2.apk` có SHA-256 `b18af2a0e44d7634bbcdf93664d9c78a2695e050393fcfbb5e8b91f902d194a4`. Tải lại từ repo [dineshshetty/Android-InsecureBankv2](https://github.com/dineshshetty/Android-InsecureBankv2), build debug cho ra cùng hash |
| Thiết bị / emulator | ⚠️ Phụ thuộc | Cần Android emulator chạy được `adb`. Script tự phát hiện thiết bị qua `adb devices`, không hardcode serial |
| Kết quả IPC (Kịch bản B) | ✅ Tái lập được | Manifest và các component exported là thuộc tính của APK, không phụ thuộc máy. `adb shell am` trả về cùng output |
| Kết quả Storage (Kịch bản A) | ⚠️ Phụ thuộc dữ liệu runtime | SharedPreferences/SQLite chỉ có dữ liệu nếu app đã chạy và người dùng đã đăng nhập. Build này không có UI "Remember Me" nên **không tái lập được STORAGE-1** |
| Logcat | ⚠️ Phụ thuộc timing | Số dòng logcat phụ thuộc thời điểm bắt. Bộ lọc `filter_logcat.py` loại false positive nên kết quả ổn định |
| Ảnh chụp | ✅ Tái lập được | Dùng `screencap` + `pull`, chạy trên mọi emulator hỗ trợ `adb` |
| Báo cáo | ✅ Tái lập được | `generate_report.py` sinh từ evidence thực, không điền số tay |

**Kết luận:** Kịch bản B (IPC) tái lập hoàn toàn trên máy khác. Kịch bản A (Storage) tái lập được về mặt kỹ thuật (đọc được thư mục dữ liệu của app), nhưng nội dung kết quả phụ thuộc vào dữ liệu runtime của app.

---

## Hướng dẫn tái lập trên máy khác

### Yêu cầu môi trường

| Thành phần | Yêu cầu | Ghi chú |
|---|---|---|
| Hệ điều hành | Windows 10/11 (64-bit) | Đã test trên Windows 10 |
| Android emulator | Genymotion / BlueStacks / AVD / thiết bị thật | Bật USB debugging nếu dùng thiết bị thật |
| ADB | Android Platform Tools | `adb devices` phải thấy thiết bị |
| Python | 3.10+ | Dùng lệnh `python` (hoặc đổi biến `PYTHON` trong `lib.bat`) |
| apktool | 2.9+ | `choco install apktool` hoặc tải từ [apktool.org](https://apktool.org) |
| 7-Zip (tuỳ chọn) | `7z.exe` | Chỉ cần cho bước đóng gói |

### Các bước chi tiết

#### Bước 0 – Chuẩn bị

```bat
choco install apktool 7zip
adb version
apktool --version
python --version
7z x insecurebankv2-dynamic-analysis-<phiên bản>.zip
cd insecurebankv2-dynamic-analysis-<phiên bản>
adb devices
```

#### Bước 1 – Kiểm tra môi trường và APK

```bat
scripts\setup.bat
```

**Kết quả mong đợi:**
- `[+] adb`, `[+] python`, `[+] Device: …`
- SHA-256 của APK khớp `b18af2a0e44d7634bbcdf93664d9c78a2695e050393fcfbb5e8b91f902d194a4`

#### Bước 2 – Trích xuất component (Kịch bản B)

```bat
scripts\recon_components.bat
```

**Kết quả mong đợi:**
- `logs\manifest_stats.json` có `"source": "apktool xml"`
- `logs\exported_components.tsv` liệt kê 7 component, trong đó 6 component có `verdict=FAIL`

#### Bước 3 – Kịch bản A (Storage)

```bat
scripts\storage_theft.bat
```

Script sẽ:
1. Cài app và kiểm tra `run-as` hoạt động.
2. Dừng lại và nhắc đăng nhập thủ công bằng tài khoản `dinesh` / `Dinesh@123$`.
3. Sau khi đăng nhập xong, nhấn **Enter** để tiếp tục.
4. Kéo SharedPreferences và SQLite, lọc logcat, chụp ảnh màn hình.

> **Lưu ý:** Bản APK này không có checkbox "Remember Me", nên `prefs_sensitive.txt` sẽ không chứa credential. Đây là đặc điểm của build, không phải lỗi của script.

#### Bước 4 – Kịch bản B (IPC)

```bat
scripts\ipc_exploit.bat
```

Script tự đọc `exported_components.tsv`, gọi từng component bằng `adb shell am` và chụp ảnh màn hình sau mỗi lần mở được.

**Kết quả mong đợi:** 6 component mở được, 0 component bị chặn.

#### Bước 5 – Sinh báo cáo và đóng gói

```bat
scripts\generate_report.bat
scripts\zip_package.bat
```

- Báo cáo: `docs\DEMO_REPORT.md`
- Gói nộp: `dist\insecurebankv2-dynamic-analysis-<phiên bản>.zip`

### Chạy toàn bộ một lần

```bat
scripts\run_all.bat
```
