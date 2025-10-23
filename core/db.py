import os
import psycopg
from contextlib import contextmanager

# --- Esquema ---
SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

# --- Conexión ---
@contextmanager
def get_conn():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no configurada")
    with psycopg.connect(database_url, autocommit=True) as conn:
        yield conn

# --- Init ---
def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)