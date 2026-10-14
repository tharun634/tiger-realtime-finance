"""Apply sql/001_schema.sql outside a transaction.

Continuous aggregates cannot be created inside a transaction block.
"""

from pathlib import Path

from dotenv import load_dotenv

from websocket_test import connect

load_dotenv()


def statements(sql: str):
    chunks = []
    current = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            text = "\n".join(current).strip().rstrip(";").strip()
            if text:
                chunks.append(text)
            current = []
    return chunks


def main():
    sql = Path("sql/001_schema.sql").read_text(encoding="utf-8")
    conn = connect()
    conn.autocommit = True
    with conn.cursor() as cursor:
        for statement in statements(sql):
            preview = " ".join(statement.split())[:80]
            print(f"running: {preview}")
            cursor.execute(statement)
    print("schema applied")


if __name__ == "__main__":
    main()
