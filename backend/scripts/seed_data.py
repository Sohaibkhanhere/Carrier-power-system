"""Seed the database from the Excel file shipped with the project."""

import sys
from pathlib import Path

# Allow running from project root: uv run python scripts/seed_data.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.services.import_service import seed_file


def main():
    excel_path = Path(__file__).resolve().parent.parent.parent / "One Month data.xlsx"
    if not excel_path.exists():
        print(f"ERROR: Seed file not found at {excel_path}")
        sys.exit(1)

    print("Initialising database …")
    init_db()

    db = SessionLocal()
    try:
        print(f"Importing {excel_path.name} …")
        count, errors = seed_file(excel_path, db)
        db.commit()
        print(f"Imported {count} rows.")
        if errors:
            print("Errors/warnings:")
            for e in errors:
                print(f"  – {e}")
        else:
            print("No errors.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
