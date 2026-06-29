import sqlite3
from datetime import datetime

DB_PATH = "alpha_memory.db"


def connect():
    return sqlite3.connect(DB_PATH)


def setup_database():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_name TEXT,

            liquidity REAL,
            volume REAL,
            market_cap REAL,
            holders INTEGER,
            age_minutes INTEGER,
            price_change REAL,

            score INTEGER,
            risk_score INTEGER,
            probability REAL,

            action TEXT,
            status TEXT,
            reason TEXT,

            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_scan(coin_name: str, result: dict):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO scans (
            coin_name,
            liquidity,
            volume,
            market_cap,
            holders,
            age_minutes,
            price_change,
            score,
            risk_score,
            probability,
            action,
            status,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        coin_name,
        result["liquidity"],
        result["volume"],
        result["market_cap"],
        result["holders"],
        result["age_minutes"],
        result["price_change"],
        result["score"],
        result["risk_score"],
        result["probability"],
        result["action"],
        result["status"],
        result["reason"],
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_scans():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            coin_name,
            liquidity,
            volume,
            market_cap,
            holders,
            age_minutes,
            price_change,
            score,
            risk_score,
            probability,
            action,
            status,
            reason,
            created_at
        FROM scans
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "coin_name": row[1],
            "liquidity": row[2],
            "volume": row[3],
            "market_cap": row[4],
            "holders": row[5],
            "age_minutes": row[6],
            "price_change": row[7],
            "score": row[8],
            "risk_score": row[9],
            "probability": row[10],
            "action": row[11],
            "status": row[12],
            "reason": row[13],
            "created_at": row[14]
        }
        for row in rows
    ]