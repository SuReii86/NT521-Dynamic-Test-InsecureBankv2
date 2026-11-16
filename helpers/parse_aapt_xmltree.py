#!/usr/bin/env python3
"""Parse output của `aapt dump xmltree AndroidManifest.xml` thành JSON component.

Dùng khi không có apktool (chỉ có aapt/aapt2 từ Android SDK build-tools).

    aapt dump xmltree app.apk AndroidManifest.xml > dump.txt
    python parse_aapt_xmltree.py dump.txt > manifest_stats.json
"""
import json
import re
import sys

COMPONENT_TAGS = {
    "activity": "activities",
    "activity-alias": "activities",
    "service": "services",
    "receiver": "receivers",
    "provider": "providers",
}

# Các tag con không làm kết thúc block component
CHILD_TAGS = {
    "intent-filter", "action", "category", "data", "meta-data",
    "grant-uri-permission", "path-permission", "uses-permission",
}


def attr(line, name):
    """Lấy giá trị của 1 attribute trong dòng xmltree."""
    key = f'"{name}"'
    if key not in line:
        return None
    rest = line.split(key, 1)[1]
    m = re.search(r'="([^"]*)"', rest)
    if m:
        return m.group(1)
    # boolean/int dạng =(type 0x12)0xffffffff
    m = re.search(r'=\([^)]*\)(0x[0-9a-fA-F]+|true|false)', rest)
    if m:
        v = m.group(1).lower()
        if v in ("0xffffffff", "true"):
            return "true"
        if v in ("0x0", "false"):
            return "false"
        return v
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    result = {
        "source": "aapt xmltree",
        "application_flags": {},
        "activities": {"total": 0, "exported": 0, "exported_no_permission": 0,
                       "exported_no_permission_list": [], "components": []},
        "services": {"total": 0, "exported": 0, "exported_no_permission": 0,
                     "exported_no_permission_list": [], "components": []},
        "receivers": {"total": 0, "exported": 0, "exported_no_permission": 0,
                      "exported_no_permission_list": [], "components": []},
        "providers": {"total": 0, "exported": 0, "exported_no_permission": 0,
                      "exported_no_permission_list": [], "components": []},
        "deep_links": [],
        "task_hijacking_candidates": [],
    }

    current = None          # component đang đọc
    in_application = False
    current_filter = None

    def close(current):
        if not current:
            return
        bucket = result[current["bucket"]]
        bucket["total"] += 1
        if current["exported"]:
            bucket["exported"] += 1
            if not current["permission"]:
                bucket["exported_no_permission"] += 1
                bucket["exported_no_permission_list"].append(current["name"])
            if current["taskAffinity"] == "" and current["launchMode"] in ("singleTask", "singleInstance"):
                result["task_hijacking_candidates"].append({
                    "component": current["name"],
                    "taskAffinity": "",
                    "launchMode": current["launchMode"],
                })
        if current["exported"] or current["has_filter"]:
            bucket["components"].append({
                "name": current["name"],
                "exported": current["exported"],
                "exported_declared": current["exported_declared"],
                "permission": current["permission"],
                "has_intent_filter": current["has_filter"],
                "grantUriPermissions": current["grantUriPermissions"],
                "taskAffinity": current["taskAffinity"],
                "launchMode": current["launchMode"],
            })

    for line in lines:
        s = line.strip()

        # Bắt đầu application -> đọc flags
        if s.startswith("E: application"):
            in_application = True
            continue

        if in_application and s.startswith("A: "):
            for k in ("allowBackup", "debuggable", "usesCleartextTraffic",
                      "networkSecurityConfig", "fullBackupContent", "testOnly"):
                v = attr(s, f"android:{k}")
                if v is not None:
                    result["application_flags"][k] = v
            continue

        # Component mới
        started = None
        for tag, bucket in COMPONENT_TAGS.items():
            if s.startswith(f"E: {tag} ") or s == f"E: {tag}":
                started = (tag, bucket)
                break
        if started:
            close(current)
            current = {
                "bucket": started[1], "kind": started[0], "name": None,
                "exported_declared": None, "exported": False, "permission": None,
                "has_filter": False, "grantUriPermissions": None,
                "taskAffinity": None, "launchMode": None,
            }
            current_filter = None
            continue

        if current is None:
            continue

        # Attribute của component
        if s.startswith("A: "):
            name = attr(s, "android:name")
            if name and current["name"] is None:
                current["name"] = name
            v = attr(s, "android:exported")
            if v is not None:
                current["exported_declared"] = v
                current["exported"] = v == "true"
            p = attr(s, "android:permission")
            if p is not None:
                current["permission"] = p
            g = attr(s, "android:grantUriPermissions")
            if g is not None:
                current["grantUriPermissions"] = g
            ta = attr(s, "android:taskAffinity")
            if ta is not None:
                current["taskAffinity"] = ta
            lm = attr(s, "android:launchMode")
            if lm is not None:
                current["launchMode"] = lm
            continue

        # intent-filter
        if s.startswith("E: intent-filter"):
            current["has_filter"] = True
            current_filter = {"autoVerify": None, "scheme": None, "host": None}
            result.setdefault("_filters_tmp", []).append((current, current_filter))
            continue

        if current_filter is not None:
            av = attr(s, "android:autoVerify")
            if av is not None:
                current_filter["autoVerify"] = av
            sch = attr(s, "android:scheme")
            if sch is not None:
                current_filter["scheme"] = sch
            h = attr(s, "android:host")
            if h is not None:
                current_filter["host"] = h
            if s.startswith("E: data") and current_filter.get("scheme"):
                result["deep_links"].append({
                    "component": current["name"],
                    "scheme": current_filter["scheme"],
                    "host": current_filter.get("host"),
                    "autoVerify": current_filter.get("autoVerify"),
                })
                current_filter = None

    close(current)

    # Mặc định exported: có intent-filter => exportable
    for key in ("activities", "services", "receivers", "providers"):
        b = result[key]
        for c in b["components"]:
            if c["exported_declared"] is None and c["has_intent_filter"]:
                c["exported"] = True

    result.pop("_filters_tmp", None)
    result["summary"] = {
        "total_exported_no_permission": sum(
            result[k]["exported_no_permission"]
            for k in ("activities", "services", "receivers", "providers")),
        "task_hijacking_candidates": len(result["task_hijacking_candidates"]),
        "deep_links": len(result["deep_links"]),
        "deep_links_no_autoverify": sum(
            1 for d in result["deep_links"] if d.get("autoVerify") != "true"),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
