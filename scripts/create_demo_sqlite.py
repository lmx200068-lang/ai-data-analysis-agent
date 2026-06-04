from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "SuperMarket Analysis.csv"
DB_PATH = BASE_DIR / "supermarket_demo.db"
TABLE_NAME = "supermarket_sales"


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    print(f"Created SQLite database: {DB_PATH}")
    print(f"Table: {TABLE_NAME}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()
