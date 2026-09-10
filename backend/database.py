import os
import re
import logging
import psycopg2
from psycopg2 import pool, extras
from config import Config

logger = logging.getLogger(__name__)

db_pool = None

def _clean_postgres_query(query: str, params=()) -> str:
    # 1. Convert MySQL DATE_FORMAT to PostgreSQL TO_CHAR
    q = re.sub(r"DATE_FORMAT\s*\(\s*(\w+)\s*,\s*'%H:00'\s*\)", r"TO_CHAR(\1, 'HH24:00')", query, flags=re.IGNORECASE)
    q = re.sub(r"DATE_FORMAT\s*\(\s*(\w+)\s*,\s*'%Y-%m-%d'\s*\)", r"TO_CHAR(\1, 'YYYY-MM-DD')", q, flags=re.IGNORECASE)
    
    # 2. Escape literal % in psycopg2 to prevent tuple index out of range
    if not params:
        # When there are no parameters, all single % are literal
        q = re.sub(r"(?<!%)%(?!%)", "%%", q)
    else:
        # When parameters are supplied, escape % that are not %s placeholders
        q = re.sub(r"(?<!%)%(?!s|%)", "%%", q)
        
    return q

def _try_create_pool(host):
    kwargs = {
        'minconn': 1,
        'maxconn': 20,
        'host': host,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'dbname': Config.DB_NAME,
        'connect_timeout': 5
    }
    if Config.POSTGRES_SSLMODE:
        kwargs['sslmode'] = Config.POSTGRES_SSLMODE
    return psycopg2.pool.ThreadedConnectionPool(**kwargs)

def init_postgres_tables():
    conn = get_db_connection()
    if not conn:
        return False
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(base_dir, 'database', 'complete_postgres_schema.sql')
        seed_path = os.path.join(base_dir, 'database', 'postgres_seed.sql')

        with conn.cursor() as cur:
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)
            if os.path.exists(seed_path):
                with open(seed_path, 'r', encoding='utf-8') as f:
                    seed_sql = f.read()
                cur.execute(seed_sql)
        conn.commit()
        logger.info("PostgreSQL schema and baseline seed verification complete.")
        return True
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.warning(f"Note on PostgreSQL table initialization: {str(e)}")
        return False
    finally:
        put_db_connection(conn)

def init_db_pool():
    global db_pool
    hosts = [Config.DB_HOST]
    if Config.DB_HOST not in ("127.0.0.1", "localhost"):
        hosts.append("127.0.0.1")
        
    last_err = None
    for h in hosts:
        try:
            db_pool = _try_create_pool(h)
            logger.info(f"PostgreSQL primary connection pool initialized successfully ({h}:{Config.DB_PORT}/{Config.DB_NAME}).")
            init_postgres_tables()
            return True
        except Exception as e:
            last_err = e
            
    logger.error(f"Failed to initialize PostgreSQL pool across hosts: {str(last_err)}")
    db_pool = None
    return False

def close_db_pool():
    global db_pool
    if db_pool:
        try:
            db_pool.closeall()
            logger.info("PostgreSQL connection pool closed.")
        except Exception as e:
            logger.warning(f"Error closing DB pool: {e}")
        db_pool = None

def check_db_connection():
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
            put_db_connection(conn)
            return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
    return False

def get_db_connection():
    global db_pool
    if db_pool is None:
        init_db_pool()
    if db_pool:
        try:
            return db_pool.getconn()
        except Exception as e:
            logger.error(f"Error getting connection from PostgreSQL pool: {str(e)}")
            for h in [Config.DB_HOST, "127.0.0.1"]:
                try:
                    kwargs = {
                        'host': h,
                        'port': Config.DB_PORT,
                        'user': Config.DB_USER,
                        'password': Config.DB_PASSWORD,
                        'dbname': Config.DB_NAME,
                        'connect_timeout': 5
                    }
                    if Config.POSTGRES_SSLMODE:
                        kwargs['sslmode'] = Config.POSTGRES_SSLMODE
                    return psycopg2.connect(**kwargs)
                except Exception:
                    continue
    return None

def put_db_connection(conn):
    global db_pool
    if conn:
        if db_pool:
            try:
                db_pool.putconn(conn)
                return
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

def execute_query(query, params=(), commit=True):
    query = _clean_postgres_query(query, params)
    is_insert = query.strip().upper().startswith("INSERT INTO")
    has_returning = "RETURNING" in query.upper()
    if is_insert and not has_returning:
        query = query.rstrip("; ") + " RETURNING id"
        has_returning = True

    conn = get_db_connection()
    if not conn:
        raise Exception("PostgreSQL primary database connection unavailable.")
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            last_id = None
            if has_returning:
                row = cursor.fetchone()
                if row:
                    last_id = row.get("id", 1)
            if commit:
                conn.commit()
            return last_id or 1
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"PostgreSQL query error: {str(e)} | Query: {query}")
        raise e
    finally:
        put_db_connection(conn)

def fetch_one(query, params=()):
    query = _clean_postgres_query(query, params)
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"PostgreSQL fetch_one error: {str(e)} | Query: {query}")
        return None
    finally:
        put_db_connection(conn)

def fetch_all(query, params=()):
    query = _clean_postgres_query(query, params)
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows] if rows else []
    except Exception as e:
        logger.error(f"PostgreSQL fetch_all error: {str(e)} | Query: {query}")
        return []
    finally:
        put_db_connection(conn)
