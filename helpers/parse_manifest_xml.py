#!/usr/bin/env python3
"""Parse AndroidManifest.xml (đã decode bởi apktool) thành JSON thống kê component.

    python parse_manifest_xml.py AndroidManifest.xml > manifest_stats.json
"""
import json
import sys
import xml.etree.ElementTree as ET

NS = "{http://schemas.android.com/apk/res/android}"

COMPONENT_TAGS = {
    "activity": "activities",
    "activity-alias": "activities",
    "service": "services",
    "receiver": "receivers",
    "provider": "providers",
}


def g(el, name):
    return el.get(NS + name)


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    path = sys.argv[1]
    out = {
        "source": "apktool xml",
        "application_flags": {},
        "activities": {"total": 0, "exported": 0, "exported_no_permission": 0,
                       "exported_no_permission_list": [], "components": []},
        "services": {"total": 0, "exported": 0, "exported_no_permission": 0,
                     "exported_no_permission_list": [], "components": []},
        "receivers": {"total": 0, "exported": 0, "exported_no_permission": 0,
                      "exported_no_permission_list": [], "components": []},
        "providers": {"total": 0, "exported": 0, "exported_no_permission": 0,
                      "exported_no_permission_list": [], "components": []},
        "custom_permissions": [],
        "deep_links": [],
        "task_hijacking_candidates": [],
        "parse_error": None,
    }

    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        out["parse_error"] = str(e)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    app = root.find("application")
    if app is None:
        out["parse_error"] = "no <application>"
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    for k in ("allowBackup", "fullBackupContent", "debuggable",
              "usesCleartextTraffic", "networkSecurityConfig", "testOnly"):
        v = g(app, k)
        if v is not None:
            out["application_flags"][k] = v

    for perm in root.findall("permission"):
        out["custom_permissions"].append({
            "name": g(perm, "name"),
            "protectionLevel": g(perm, "protectionLevel"),
        })

    for tag, bucket_name in COMPONENT_TAGS.items():
        bucket = out[bucket_name]
        for el in app.findall(tag):
            name = g(el, "name") or "<unnamed>"
            exp_attr = g(el, "exported")
            perm = g(el, "permission")
            has_filter = el.find("intent-filter") is not None

            if exp_attr is not None:
                exported = exp_attr.lower() == "true"
            else:
                exported = has_filter

            bucket["total"] += 1
            if exported:
                bucket["exported"] += 1
                if not perm:
                    bucket["exported_no_permission"] += 1
                    bucket["exported_no_permission_list"].append(name)

                ta = g(el, "taskAffinity")
                lm = g(el, "launchMode")
                if ta == "" and lm in ("singleTask", "singleInstance"):
                    out["task_hijacking_candidates"].append({
                        "component": name, "taskAffinity": ta, "launchMode": lm
                    })

            if exported or has_filter:
                bucket["components"].append({
                    "name": name,
                    "exported": exported,
                    "exported_declared": exp_attr,
                    "permission": perm,
                    "has_intent_filter": has_filter,
                    "grantUriPermissions": g(el, "grantUriPermissions"),
                    "taskAffinity": g(el, "taskAffinity"),
                    "launchMode": g(el, "launchMode"),
                })

            for f in el.findall("intent-filter"):
                for d in f.findall("data"):
                    scheme = g(d, "scheme")
                    if scheme:
                        out["deep_links"].append({
                            "component": name,
                            "scheme": scheme,
                            "host": g(d, "host"),
                            "autoVerify": g(f, "autoVerify"),
                        })

    out["summary"] = {
        "total_exported_no_permission": sum(
            out[k]["exported_no_permission"]
            for k in ("activities", "services", "receivers", "providers")),
        "task_hijacking_candidates": len(out["task_hijacking_candidates"]),
        "deep_links": len(out["deep_links"]),
        "deep_links_no_autoverify": sum(
            1 for d in out["deep_links"] if d.get("autoVerify") != "true"),
        "weak_custom_permissions": sum(
            1 for p in out["custom_permissions"]
            if p.get("protectionLevel") in (None, "normal", "dangerous")),
    }

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
