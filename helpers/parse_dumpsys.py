#!/usr/bin/env python3
"""Đọc `adb shell dumpsys package <pkg>` -> JSON component (ĐỘ TIN CẬY THẤP).

dumpsys KHÔNG cho biết chính xác android:exported và android:permission.
Script này chỉ suy ra component nào có mặt trong resolver table.

Chỉ dùng làm fallback khi không có apktool/aapt. Mọi kết quả được đánh dấu
confidence="low" để báo cáo không trình bày như dữ liệu chắc chắn.

    python parse_dumpsys.py dumpsys_package.txt > manifest_stats.json
"""
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Dòng component trong resolver table:
#   "        3f4c7e1 com.android.insecurebankv2/.MainActivity filter 5b2a9c3"
# hoặc "1234abcd com.example/.Foo"
COMP_LINE = re.compile(r"^\s+([0-9a-f]{6,})\s+([\w.]+)/([\w.$]+)\s+(?:filter\b|\S*$)")

# Các dòng KHÔNG phải component (action/category/data)
NOISE = re.compile(
    r"^\s*(Action:|Category:|Scheme:|Authority:|Path:|Type:|Static|Priority|"
    r"autoVerify=|Non-Data Actions|MIME Media Types|Data Schemes|"
    r"Activity Resolver Table|Service Resolver Table|Receiver Resolver Table|"
    r"Provider Resolver Table|Registered ContentProviders|ContentProvider Authorities)",
    re.I,
)

SECTIONS = {
    "Activity Resolver Table": "activities",
    "Service Resolver Table": "services",
    "Receiver Resolver Table": "receivers",
    "Provider Resolver Table": "providers",
}

KIND_LABEL = {"activities": "activity", "services": "service",
              "receivers": "receiver", "providers": "provider"}


def blank_bucket():
    return {"total": 0, "exported": 0, "exported_no_permission": 0,
            "exported_no_permission_list": [], "components": []}


def parse_component(raw_pkg, cls, pkg):
    """Chuẩn hoá 'com.foo/.Bar' -> 'com.foo.Bar'."""
    if cls.startswith("."):
        cls = pkg + cls
    return cls


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    text = open(sys.argv[1], encoding="utf-8", errors="replace").read()

    # Tên package thật
    m = re.search(r"Package \[([\w.]+)\]", text)
    pkg = m.group(1) if m else ""

    out = {
        "source": "dumpsys package",
        "confidence": "low",
        "package": pkg,
        "application_flags": {},
        "activities": blank_bucket(),
        "services": blank_bucket(),
        "receivers": blank_bucket(),
        "providers": blank_bucket(),
        "custom_permissions": [],
        "deep_links": [],
        "task_hijacking_candidates": [],
        "parse_error": None,
        "limitations": [
            "dumpsys không báo android:exported gốc",
            "dumpsys không báo android:permission gắn trên component",
            "component nằm trong resolver table KHÔNG đồng nghĩa exported=true",
            "cần apktool hoặc aapt để có dữ liệu chắc chắn",
        ],
    }

    # Flags package-level
    for flag, key in (("DEBUGGABLE", "debuggable"), ("ALLOW_BACKUP", "allowBackup")):
        if re.search(rf"\b{flag}\b", text):
            out["application_flags"][key] = "true"

    # Cắt theo section
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        matched_section = None
        for header, bucket in SECTIONS.items():
            if stripped.startswith(header):
                matched_section = bucket
                break
        if matched_section:
            current = matched_section
            continue

        # Gặp section khác ở cấp ngoài -> thoát
        if re.match(r"^[A-Z][\w ]+ Table:", stripped) and not any(
                stripped.startswith(h) for h in SECTIONS):
            current = None
            continue

        if current is None or NOISE.match(line):
            continue

        mm = COMP_LINE.match(line)
        if not mm:
            continue

        raw_pkg, cls = mm.group(2), mm.group(3)
        comp = parse_component(raw_pkg, cls, pkg)
        bucket = out[current]

        if any(c["name"] == comp for c in bucket["components"]):
            continue

        bucket["total"] += 1
        # Không khẳng định exported — để None
        bucket["components"].append({
            "name": comp,
            "exported": None,
            "exported_declared": None,
            "permission": None,
            "has_intent_filter": True,
            "grantUriPermissions": None,
            "taskAffinity": None,
            "launchMode": None,
            "confidence": "low",
        })

    # Custom permission
    for m in re.finditer(
            r"permission ([\w.]+)\s*\n\s*package:\s*([\w.]+)\s*\n\s*protectionLevel:\s*(\w+)",
            text):
        out["custom_permissions"].append({
            "name": m.group(1), "protectionLevel": m.group(3).lower()
        })

    total = sum(out[k]["total"] for k in SECTIONS.values())
    out["summary"] = {
        "total_components_seen": total,
        "total_exported_no_permission": None,
        "task_hijacking_candidates": 0,
        "deep_links": 0,
        "deep_links_no_autoverify": 0,
        "weak_custom_permissions": sum(
            1 for p in out["custom_permissions"]
            if p.get("protectionLevel") in (None, "normal", "dangerous")),
        "note": "Số liệu từ dumpsys: chỉ là component CÓ MẶT trong resolver table, "
                "không phải danh sách exported đã xác nhận.",
    }

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
