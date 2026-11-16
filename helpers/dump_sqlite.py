#!/usr/bin/env python3
"""Đọc mọi SQLite DB trong 1 thư mục, in schema + vài dòng mẫu.

    python dump_sqlite.py <thu-muc-databases> [--rows N]

Tự ép stdout sang UTF-8 để không crash trên Windows (cp1252/cp437).
"""
import io
import os
import sqlite3
import sys

# Windows console mặc định cp1252 -> ép UTF-8 trước mọi print
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def dump(path, max_rows=5):
    print(f"\n===== {os.path.basename(path)} =====")
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode("utf-8", "replace")
        cur = con.cursor()
        cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view')")
        objs = cur.fetchall()
        if not objs:
            print("(khong co bang)")
            return
        for name, typ, sql in objs:
            print(f"\n[{typ}] {name}")
            if sql:
                print(f"  schema: {sql}")
            try:
                cur.execute(f'SELECT * FROM "{name}" LIMIT {max_rows}')
                cols = [d[0] for d in cur.description]
                print("  cot: " + ", ".join(cols))
                rows = cur.fetchall()
                if not rows:
                    print("  (rong)")
                for r in rows:
                    vals = []
                    for v in r:
                        if isinstance(v, (bytes, bytearray)):
                            vals.append(f"<blob {len(v)}B>")
                        else:
                            s = str(v)
                            vals.append(s[:60] + ("..." if len(s) > 60 else ""))
                    print("  | " + " | ".join(vals))
            except Exception as e:
                print(f"  (khong doc duoc bang {name}: {e})")
        con.close()
    except Exception as e:
        print(f"(khong mo duoc: {e})")


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    d = sys.argv[1]
    max_rows = 5
    if "--rows" in sys.argv:
        try:
            max_rows = int(sys.argv[sys.argv.index("--rows") + 1])
        except (IndexError, ValueError):
            pass

    if not os.path.isdir(d):
        print(f"Khong thay thu muc: {d}", file=sys.stderr)
        return 1

    found = False
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            found = True
            dump(p, max_rows)
    if not found:
        print("(thu muc rong)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
