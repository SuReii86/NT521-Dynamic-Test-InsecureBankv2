#!/usr/bin/env python3
"""Kéo 1 file từ data dir của app ra máy Windows, an toàn với file nhị phân.

`adb exec-out` không chuyển LF -> CRLF, nên dùng nó thay `adb shell` để tránh
làm hỏng file SQLite. Nếu exec-out thất bại, fallback sang `adb pull` qua
thư mục tạm trên /sdcard.

Dùng:
    python pull_file.py <package> <path-tuong-doi> <file-dich>
    python pull_file.py com.android.insecurebankv2 shared_prefs/prefs.xml out/prefs.xml
"""
import os
import subprocess
import sys


def run(cmd, binary=False):
    return subprocess.run(cmd, capture_output=True, text=not binary)


def via_exec_out(pkg, rel, dest):
    r = subprocess.run(
        ["adb", "exec-out", f"run-as {pkg} cat '{rel}'"],
        capture_output=True,
    )
    if r.returncode != 0 or not r.stdout:
        return False, (r.stderr or b"").decode("utf-8", "replace")
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(r.stdout)
    return True, "exec-out"


def via_sdcard(pkg, rel, dest):
    tmp = "/sdcard/_dyn_pull.tmp"
    subprocess.run(["adb", "shell", f"run-as {pkg} cat '{rel}' > {tmp}"],
                   capture_output=True)
    r = subprocess.run(["adb", "pull", tmp, dest], capture_output=True, text=True)
    subprocess.run(["adb", "shell", "rm", "-f", tmp], capture_output=True)
    ok = r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0
    return ok, "sdcard-pull"


def main():
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    pkg, rel, dest = sys.argv[1:4]

    ok, how = via_exec_out(pkg, rel, dest)
    if not ok:
        ok, how = via_sdcard(pkg, rel, dest)

    if ok:
        size = os.path.getsize(dest)
        print(f"OK\t{dest}\t{size}\t{how}")
        return 0

    print(f"FAIL\t{dest}\t0\t{how}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
