import os
import psycopg2
from pathlib import Path

def init_db():
    db_url = os.getenv("DATABASE_URL_SYNC")
    if not db_url:
        print("DATABASE_URL_SYNC not set, skipping DB init.")
        return

    # Render gives postgres:// but psycopg2 handles it fine.
    print(f"Connecting to DB to initialize schema...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        sql_file = Path(__file__).parent / "init_db.sql"
        with open(sql_file, "r") as f:
            sql = f.read()
            
        print("Executing init_db.sql...")
        cursor.execute(sql)
        print("Database schema initialized successfully.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to initialize database: {e}")

if __name__ == "__main__":
    init_db()
