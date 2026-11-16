#!/usr/bin/env python3
"""Lọc logcat: chỉ giữ dòng THỰC SỰ chứa dữ liệu nhạy cảm.

Loại false positive phổ biến:
  - InputMethodManager showSoftInput() view=...app:id/loginscreen_password
    -> chỉ là TÊN FIELD UI, không phải giá trị password
  - Dòng chỉ chứa tên class như TokenManager, PasswordValidator
  - Dòng chứa "password" nhưng là nhãn UI: "Enter your password"

    python filter_logcat.py <logcat.txt> <out-sensitive.txt>

Exit: 0 = có dòng nghi vấn thật, 1 = không có
"""
import io
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Từ khoá giá trị nhạy cảm
KEYWORDS = re.compile(
    r"(password|passwd|pwd|token|secret|api[_-]?key|authorization|bearer|"
    r"sessionid|session_id|cvv|card_?number|pin\s*[:=])",
    re.I,
)

# Dòng chắc chắn là nhiễu
NOISE = [
    # InputMethodManager chỉ in id của view, không in giá trị
    re.compile(r"InputMethodManager", re.I),
    # Tên class/package
    re.compile(r"\b[\w.]*(Password|Token|Secret|Auth)[A-Z]\w*\b(?!\s*[:=])"),
    # Nhãn UI dạng "Enter your password"
    re.compile(r"(enter|type|confirm|forgot|reset|current|new)\s+(your\s+)?(password|pin)", re.I),
    # Định nghĩa hằng số trong log debug thư viện
    re.compile(r"(EditText|TextView|Button|resource|layout|xml|app:id/)", re.I),
]

# Dấu hiệu là GIÁ TRỊ thật: key=value, key: value, JSON
VALUE_LIKE = re.compile(
    r"(password|passwd|pwd|token|secret|api[_-]?key)\s*[:=]\s*[^\s\"']{3,}"
    r"|[\"'](password|token|secret)[\"']\s*:\s*[\"'][^\"']{3,}[\"']",
    re.I,
)


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    src, dst = sys.argv[1], sys.argv[2]

    kept, dropped = [], 0
    try:
        with open(src, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not KEYWORDS.search(line):
                    continue
                if any(p.search(line) for p in NOISE):
                    dropped += 1
                    continue
                if not VALUE_LIKE.search(line):
                    dropped += 1
                    continue
                kept.append(line.rstrip())
    except FileNotFoundError:
        print(f"[!] Khong thay file: {src}", file=sys.stderr)
        open(dst, "w", encoding="utf-8").close()
        return 1

    with open(dst, "w", encoding="utf-8") as f:
        if kept:
            f.write("\n".join(kept) + "\n")
        else:
            f.write("# Khong co dong logcat nao chua GIA TRI nhay cam.\n")
            f.write(f"# (da loai {dropped} dong chi chua ten field/class/nhan UI)\n")
            f.write("# -> STORAGE-3 khong ket luan duoc tu logcat.\n")

    print(f"[{'+' if kept else '!'}] {len(kept)} dong nghi van, loai {dropped} dong nhieu")
    return 0 if kept else 1


if __name__ == "__main__":
    sys.exit(main())
