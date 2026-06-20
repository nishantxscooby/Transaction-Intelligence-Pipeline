import os
from pathlib import Path

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DB_PATH = Path(__file__).parent.parent / 'jobs.db'
    DATABASE_URL = f'sqlite:///{DB_PATH}' if SQLALCHEMY_AVAILABLE else str(DB_PATH)

if SQLALCHEMY_AVAILABLE:
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine)

    def init_db():
        # create table if not exists using raw SQL for simplicity
        with engine.begin() as conn:
            conn.execute(text('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                filename TEXT,
                status TEXT,
                row_count INTEGER,
                created_at TEXT,
                results TEXT
            )
            '''))
else:
    # sqlite fallback using builtin sqlite3
    import sqlite3

    DB_FILE = Path(DATABASE_URL)

    def init_db():
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''CREATE TABLE IF NOT EXISTS jobs(
            job_id TEXT PRIMARY KEY,
            filename TEXT,
            status TEXT,
            row_count INTEGER,
            created_at TEXT,
            results TEXT
        )''')
        conn.commit()
        conn.close()

    def get_sqlite_conn():
        return sqlite3.connect(DB_FILE)

