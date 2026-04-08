from sqlalchemy import create_engine, text

from src.config.settings import settings

engine = create_engine(settings.sql.url)

with engine.connect() as conn:
    try:
        conn.execute(text("DROP TABLE IF EXISTS chunk_duplicates"))
        print("Dropped chunk_duplicates table if it existed.")
    except Exception as e:
        print(f"Error dropping chunk_duplicates: {e}")

    try:
        # Check if is_active exists in chunk_index
        res = conn.execute(text("PRAGMA table_info(chunk_index)"))
        columns = [row[1] for row in res]
        if 'is_active' in columns:
            print("is_active already exists in chunk_index. Attempting to drop it (batch mode needed for SQLite).")
            # For simplicity in this scratch script, I'll just note it.
            # Usually we group these with migrations.
        else:
            print("is_active does not exist in chunk_index.")
    except Exception as e:
        print(f"Error checking chunk_index: {e}")

    conn.commit()
