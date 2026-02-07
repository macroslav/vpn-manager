import sqlite3
from datetime import datetime
from typing import Iterable

from config import DB_PATH, DATA_DIR


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS peers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                ip TEXT UNIQUE NOT NULL,
                public_key TEXT NOT NULL,
                private_key TEXT,
                config_path TEXT,
                qr_path TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


def list_peers() -> list[sqlite3.Row]:
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT id, name, ip, public_key, private_key, config_path, qr_path, created_at
            FROM peers
            ORDER BY id DESC
            """
        ).fetchall()


def find_peer_by_id(peer_id: int) -> sqlite3.Row | None:
    with db_connect() as conn:
        return conn.execute("SELECT * FROM peers WHERE id = ?", (peer_id,)).fetchone()


def find_peer_by_name(name: str) -> sqlite3.Row | None:
    with db_connect() as conn:
        return conn.execute("SELECT * FROM peers WHERE name = ?", (name,)).fetchone()


def find_peer_by_ip(ip: str) -> sqlite3.Row | None:
    with db_connect() as conn:
        return conn.execute("SELECT * FROM peers WHERE ip = ?", (ip,)).fetchone()


def insert_peer(
    name: str,
    ip: str,
    public_key: str,
    private_key: str | None,
    config_path: str | None,
    qr_path: str | None,
) -> int:
    created_at = datetime.utcnow().isoformat()
    with db_connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO peers (name, ip, public_key, private_key, config_path, qr_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, ip, public_key, private_key, config_path, qr_path, created_at),
        )
        conn.commit()
        return int(cur.lastrowid)


def delete_peer(peer_id: int) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM peers WHERE id = ?", (peer_id,))
        conn.commit()


def list_ips_from_db() -> set[str]:
    with db_connect() as conn:
        rows = conn.execute("SELECT ip FROM peers").fetchall()
    return {row["ip"] for row in rows}


def import_peers(records: Iterable[dict[str, str]]) -> int:
    imported = 0
    with db_connect() as conn:
        for rec in records:
            ip = rec["ip"]
            exists = conn.execute("SELECT id FROM peers WHERE ip = ?", (ip,)).fetchone()
            if exists:
                continue

            name = rec["name"]
            name_exists = conn.execute(
                "SELECT id FROM peers WHERE name = ?", (name,)
            ).fetchone()
            if name_exists:
                last_octet = ip.split(".")[-1]
                name = f"{name}-{last_octet}"

            conn.execute(
                """
                INSERT INTO peers (name, ip, public_key, private_key, config_path, qr_path, created_at)
                VALUES (?, ?, ?, NULL, NULL, NULL, ?)
                """,
                (name, ip, rec["public_key"], datetime.utcnow().isoformat()),
            )
            imported += 1
        conn.commit()
    return imported
