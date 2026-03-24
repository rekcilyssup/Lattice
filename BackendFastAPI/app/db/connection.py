from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from app.core.config import settings


def _dsn() -> str:
    dsn = (
        f"host={settings.POSTGRES_HOST} "
        f"port={settings.POSTGRES_PORT} "
        f"dbname={settings.POSTGRES_DB} "
        f"user={settings.POSTGRES_USER} "
        f"password={settings.POSTGRES_PASSWORD}"
    )
    if settings.POSTGRES_SSL:
        dsn += " sslmode=require"
    return dsn


@contextmanager
def get_conn():
    conn = psycopg.connect(_dsn(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
