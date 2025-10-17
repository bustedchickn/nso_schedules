# nfc_tracking.py
import os
import json
import sqlite3
import time
from datetime import datetime
from urllib.parse import urlparse
import requests

DB_PATH = os.environ.get("TRACKING_DB_PATH", "nfc_tracking.db")
DATABASE_URL = os.environ.get("DATABASE_URL")  # Railway Postgres

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "replace-me-with-secure-token")  # set in Railway.env

USE_POSTGRES = bool(DATABASE_URL)

# --- DB helpers (sqlite fallback or postgres if DATABASE_URL set) ---
def get_conn():
    if USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS nfc_usage_logs (
            id SERIAL PRIMARY KEY,
            token TEXT,
            path TEXT,
            ip TEXT,
            forwarded_for TEXT,
            user_agent TEXT,
            accept_language TEXT,
            referrer TEXT,
            device_id TEXT,
            client_info JSONB,
            country TEXT,
            region TEXT,
            city TEXT,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT now()
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS nfc_tokens (
            token TEXT PRIMARY KEY,
            owner TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT now()
        );
        """)
        conn.commit()
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS nfc_usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            path TEXT,
            ip TEXT,
            forwarded_for TEXT,
            user_agent TEXT,
            accept_language TEXT,
            referrer TEXT,
            device_id TEXT,
            client_info TEXT,
            country TEXT,
            region TEXT,
            city TEXT,
            lat REAL,
            lon REAL,
            created_at TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS nfc_tokens (
            token TEXT PRIMARY KEY,
            owner TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        );
        """)
        conn.commit()
    cur.close()
    conn.close()

# --- Geo lookup (simple) ---
def geo_lookup(ip):
    """Try ip-api.com (free, rate-limited). Returns dict or {} on failure."""
    try:
        # ip-api supports private IPs returning fail; catch exceptions
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=country,regionName,city,lat,lon,status,message", timeout=3)
        data = r.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lon": data.get("lon")
            }
    except Exception:
        pass
    return {}

# --- Main logging function ---
def log_visit(flask_request, token=None, device_id=None, client_info=None):
    """
    Call this in your Flask route to log a visit.
    - flask_request: the flask request object
    - token: optional token string (if you can get from query param or path)
    - device_id: optional device id (cookie from client Side)
    - client_info: optional dict with extra client fields (tz, screen, platform, etc)
    """
    conn = get_conn()
    cur = conn.cursor()
    ip = flask_request.headers.get("X-Forwarded-For", flask_request.remote_addr)
    forwarded_for = flask_request.headers.get("X-Forwarded-For", "")
    ua = flask_request.headers.get("User-Agent", "")
    accept_lang = flask_request.headers.get("Accept-Language", "")
    referrer = flask_request.referrer or flask_request.headers.get("Referer") or ""
    path = flask_request.path + ("?" + flask_request.query_string.decode() if flask_request.query_string else "")
    created_at = datetime.utcnow()

    geo = geo_lookup(ip.split(",")[0].strip() if ip else ip)

    if USE_POSTGRES:
        # Postgres insert with JSONB
        cur.execute(
            """
            INSERT INTO nfc_usage_logs
            (token, path, ip, forwarded_for, user_agent, accept_language, referrer, device_id, client_info, country, region, city, lat, lon, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                token, path, ip, forwarded_for, ua, accept_lang, referrer, device_id,
                json.dumps(client_info) if client_info else None,
                geo.get("country"), geo.get("region"), geo.get("city"), geo.get("lat"), geo.get("lon"),
                created_at
            )
        )
        conn.commit()
    else:
        cur.execute(
            """
            INSERT INTO nfc_usage_logs
            (token, path, ip, forwarded_for, user_agent, accept_language, referrer, device_id, client_info, country, region, city, lat, lon, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                token, path, ip, forwarded_for, ua, accept_lang, referrer, device_id,
                json.dumps(client_info) if client_info else None,
                geo.get("country"), geo.get("region"), geo.get("city"), geo.get("lat"), geo.get("lon"),
                created_at.isoformat()
            )
        )
        conn.commit()

    cur.close()
    conn.close()

# --- Admin helpers ---
def fetch_logs(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("SELECT token, path, ip, user_agent, accept_language, referrer, device_id, client_info, country, region, city, lat, lon, created_at FROM nfc_usage_logs ORDER BY created_at DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
    else:
        cur.execute("SELECT token, path, ip, user_agent, accept_language, referrer, device_id, client_info, country, region, city, lat, lon, created_at FROM nfc_usage_logs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
    cur.close()
    conn.close()
    # return list of dicts
    keys = ["token","path","ip","user_agent","accept_language","referrer","device_id","client_info","country","region","city","lat","lon","created_at"]
    out = []
    for r in rows:
        entry = dict(zip(keys, r))
        # parse client_info if JSON string
        if isinstance(entry.get("client_info"), str):
            try:
                entry["client_info"] = json.loads(entry["client_info"])
            except Exception:
                pass
        out.append(entry)
    return out

def set_token_active(token, active: bool):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("INSERT INTO nfc_tokens (token, active) VALUES (%s, %s) ON CONFLICT (token) DO UPDATE SET active = EXCLUDED.active", (token, active))
    else:
        now = datetime.utcnow().isoformat()
        cur.execute("INSERT OR REPLACE INTO nfc_tokens (token, owner, active, created_at) VALUES (?,?,?,?)", (token, None, 1 if active else 0, now))
    conn.commit()
    cur.close()
    conn.close()

def token_active(token):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("SELECT active FROM nfc_tokens WHERE token = %s", (token,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        return bool(r and r[0])
    else:
        cur.execute("SELECT active FROM nfc_tokens WHERE token = ?", (token,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        return bool(r and r[0] == 1)

# Initialize DB on import
try:
    init_db()
except Exception as e:
    print("Failed to init tracking DB:", e)
