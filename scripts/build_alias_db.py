"""从 tables/ 目录下的 CSV 文件构建别名 SQLite 数据库。

CSV 文件名（不含扩展名）即为数据库表名，每个 CSV 需包含 name 和 target_id 两列。
用法: python scripts/build_alias_db.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES_DIR = ROOT / "tables"
OUTPUT_DB = ROOT / "aliases-data.sqlite"


def main() -> None:
    OUTPUT_DB.unlink(missing_ok=True)

    conn = sqlite3.connect(OUTPUT_DB)
    try:
        for csv_file in sorted(TABLES_DIR.glob("*.csv")):
            table_name = csv_file.stem

            conn.execute(
                f"CREATE TABLE [{table_name}] "
                "(name TEXT NOT NULL, target_id INTEGER NOT NULL, "
                "PRIMARY KEY (name, target_id))"
            )

            with csv_file.open(encoding="utf-8") as f:
                rows = [
                    (row["name"], int(row["target_id"]))
                    for row in tuple(
                        csv.DictReader(f, fieldnames=["name", "target_id"])
                    )[1:]
                ]

            conn.executemany(
                f"INSERT INTO [{table_name}] (name, target_id) VALUES (?, ?)",
                rows,
            )
            print(f"{csv_file.name} -> {table_name}: {len(rows)} 条记录")

        conn.commit()
    finally:
        conn.close()

    size_kb = OUTPUT_DB.stat().st_size / 1024
    print(f"\n已生成: {OUTPUT_DB} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
