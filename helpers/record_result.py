#!/usr/bin/env python3
"""Ghi 1 kết quả vào results.jsonl.

Dùng: python record_result.py <results.jsonl> <step> <status> <detail> [evidence]
"""
import json
import sys
import datetime


def main():
    if len(sys.argv) < 5:
        print(__doc__, file=sys.stderr)
        return 2
    path, step, status, detail = sys.argv[1:5]
    evidence = sys.argv[5] if len(sys.argv) > 5 else ""
    rec = {
        "step": step,
        "status": status,
        "detail": detail,
        "evidence": evidence,
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
