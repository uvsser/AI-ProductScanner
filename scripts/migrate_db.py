import sqlite3
from app.core.config import settings

db_path = settings.resolved_storage_dir / "app.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
columns = [col[1] for col in cur.execute("PRAGMA table_info(products)").fetchall()]
print("Current columns:", columns)
if "barcode" not in columns:
    cur.execute("ALTER TABLE products ADD COLUMN barcode VARCHAR(100) DEFAULT ''")
    conn.commit()
    print("Added barcode column successfully!")
else:
    print("Barcode column already present.")
conn.close()
