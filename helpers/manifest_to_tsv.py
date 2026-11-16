#!/usr/bin/env python3
"""Sinh bảng TSV component từ manifest_stats.json.

    python manifest_to_tsv.py manifest_stats.json > exported_components.tsv

Nếu nguồn là dumpsys (confidence low), cột verdict = UNKNOWN thay vì FAIL,
và thêm dòng cảnh báo ở đầu file (dạng comment #).
"""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KINDS = [("activities", "activity"), ("services", "service"),
         ("receivers", "receiver"), ("providers", "provider")]


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    try:
        d = json.load(open(sys.argv[1], encoding="utf-8"))
    except Exception as e:
        print(f"# parse error: {e}", file=sys.stderr)
        return 1

    low_conf = d.get("confidence") == "low"
    if low_conf:
        print("# CANH BAO: du lieu tu dumpsys (confidence=low)")
        print("# 'exported' va 'permission' KHONG xac dinh duoc bang dumpsys")
        print("# -> verdict=UNKNOWN, khong dung de ket luan")
        print("# Cai apktool hoac Android SDK build-tools (aapt) de co du lieu that")

    print("type\tname\texported\tpermission\tintent_filter\tverdict\tconfidence")

    for key, label in KINDS:
        bucket = d.get(key) or {}
        for c in bucket.get("components") or []:
            exported = c.get("exported")
            perm = c.get("permission") or "-"
            flt = "yes" if c.get("has_intent_filter") else "no"

            if low_conf or exported is None:
                exported_s = "unknown"
                verdict = "UNKNOWN"
                conf = "low"
            else:
                exported_s = "true" if exported else "false"
                conf = "high"
                if exported and not c.get("permission"):
                    verdict = "FAIL"
                elif exported and c.get("permission"):
                    verdict = "guarded"
                else:
                    verdict = "PASS"

            print(f"{label}\t{c.get('name')}\t{exported_s}\t{perm}\t{flt}\t{verdict}\t{conf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
