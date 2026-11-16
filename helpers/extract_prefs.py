#!/usr/bin/env python3
"""Ghi kết quả đọc SharedPreferences ra file, KHÔNG có false positive.

Vào:
    evidence/logs/prefs/*.xml

Ra:
    evidence/logs/prefs_sensitive.txt   — key/value nhạy cảm đã trích
    evidence/logs/prefs_all.txt         — toàn bộ key/value (không nhạy cảm)

Exit code:
    0 = tìm thấy key nhạy cảm
    1 = không có file prefs
    2 = có file nhưng không có key nhạy cảm (vd chưa bật Remember me)

    python extract_prefs.py <thu-muc-prefs> <out-sensitive.txt> <out-all.txt>
"""
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SENSITIVE_KEY = re.compile(
    r"(pass(word|wd)?|pwd|token|secret|api[_-]?key|username|user(name)?|"
    r"account|pin\b|cvv|session|cookie|auth)",
    re.I,
)

STR_RE = re.compile(r'<string\s+name="([^"]+)"\s*>([^<]*)</string>', re.S)
OTHER_RE = re.compile(r'<(boolean|int|long|float)\s+name="([^"]+)"\s+value="([^"]*)"')


def main():
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2

    prefs_dir, out_sens, out_all = sys.argv[1:4]

    if not os.path.isdir(prefs_dir):
        print(f"[!] Khong thay thu muc: {prefs_dir}", file=sys.stderr)
        return 1

    xmls = sorted(f for f in os.listdir(prefs_dir) if f.lower().endswith(".xml"))
    if not xmls:
        print("[!] Thu muc prefs rong", file=sys.stderr)
        return 1

    sens_lines = ["=== Key/value nhay cam trong SharedPreferences ==="]
    all_lines = ["=== Toan bo key/value trong SharedPreferences ==="]
    n_sens = 0

    for name in xmls:
        path = os.path.join(prefs_dir, name)
        try:
            content = open(path, encoding="utf-8", errors="replace").read()
        except Exception as e:
            print(f"[!] Khong doc duoc {name}: {e}", file=sys.stderr)
            continue

        all_lines.append(f"\n--- {name} ---")
        pairs = []
        for k, v in STR_RE.findall(content):
            pairs.append((k, v.strip(), "string"))
        for typ, k, v in OTHER_RE.findall(content):
            pairs.append((k, v, typ))

        if not pairs:
            all_lines.append("  (khong co key nao)")
            continue

        for k, v, typ in pairs:
            line = f"  {k} = {v}   [{typ}]"
            all_lines.append(line)
            if SENSITIVE_KEY.search(k):
                sens_lines.append(f"{name}:{k} = {v}")
                n_sens += 1

    with open(out_all, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines) + "\n")

    if n_sens:
        sens_lines.insert(1, f"(tong: {n_sens} muc)")
        with open(out_sens, "w", encoding="utf-8") as f:
            f.write("\n".join(sens_lines) + "\n")
        print(f"[+] {n_sens} key nhay cam -> {out_sens}")
        return 0

    with open(out_sens, "w", encoding="utf-8") as f:
        f.write("\n".join(sens_lines) + "\n")
        f.write("\nKHONG tim thay key nhay cam (password/token/username...).\n")
        f.write("Nguyen nhan thuong gap: chua tich 'Remember me' khi dang nhap.\n")
        f.write("-> Dang xuat, dang nhap lai va TICH 'Remember me', roi chay lai buoc 2.\n")
    print("[!] Khong co key nhay cam trong prefs", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
