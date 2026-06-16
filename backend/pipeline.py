import hashlib
import json
import os
import runpy
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("BAILING_DB_PATH", str(ROOT / "outputs" / "bailing.db")))
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
PUBLIC_JSON = ROOT / "outputs" / "bailing-public-data.json"
SCHEMA = Path(__file__).with_name("schema.sql")
SUPABASE_SCHEMA = Path(__file__).with_name("supabase_schema.sql")


def now():
    return datetime.now().replace(microsecond=0).isoformat()


def U(value):
    return value.encode("ascii").decode("unicode_escape")


def using_postgres():
    return bool(DATABASE_URL)


def adapt_sql(sql):
    if not using_postgres():
        return sql
    return sql.replace("?", "%s")


def execute(conn, sql, params=()):
    return conn.execute(adapt_sql(sql), params)


class Db:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()


def connect():
    if using_postgres():
        import psycopg
        from psycopg.rows import dict_row

        return Db(psycopg.connect(DATABASE_URL, row_factory=dict_row))
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        if using_postgres():
            conn.execute(SUPABASE_SCHEMA.read_text(encoding="utf-8"))
        else:
            conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        if using_postgres():
            execute(
                conn,
                "INSERT INTO users(id,name,role,industry,created_at) VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                ("demo-consultant", U("\\u77e5\\u66f4\\u4f53\\u9a8c\\u987e\\u95ee"), "verified", U("\\u7ba1\\u7406\\u54a8\\u8be2"), now()),
            )
        else:
            execute(
                conn,
                "INSERT OR IGNORE INTO users(id,name,role,industry,created_at) VALUES(?,?,?,?,?)",
                ("demo-consultant", U("\\u77e5\\u66f4\\u4f53\\u9a8c\\u987e\\u95ee"), "verified", U("\\u7ba1\\u7406\\u54a8\\u8be2"), now()),
            )
    return "postgres" if using_postgres() else DB


def content_hash(item):
    raw = "|".join([item.get("source_id", ""), item.get("title", ""), item.get("url", "")])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_public_json():
    return json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))


def upsert_public_data(data):
    init_db()
    stamp = now()
    with connect() as conn:
        for source in data.get("sources", []):
            execute(
                conn,
                """
                INSERT INTO sources(source_id,name,url,status,mode,category,items,latency_ms,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                  name=excluded.name,url=excluded.url,status=excluded.status,mode=excluded.mode,
                  category=excluded.category,items=excluded.items,latency_ms=excluded.latency_ms,
                  updated_at=excluded.updated_at
                """,
                (
                    source.get("source_id"),
                    source.get("name"),
                    source.get("url"),
                    source.get("status"),
                    source.get("mode"),
                    source.get("category"),
                    int(source.get("items") or 0),
                    int(source.get("latency_ms") or 0),
                    stamp,
                ),
            )
        existing = {row["id"] for row in execute(conn, "SELECT id FROM items")}
        added = 0
        for item in data.get("items", []):
            item_id = item.get("id")
            if not item_id:
                continue
            if item_id not in existing:
                added += 1
            execute(
                conn,
                """
                INSERT INTO items(
                  id,source_id,source_name,category,authority,title,url,published_at,tags_json,
                  scene,consulting_value,public_value,ingestion,score,content_hash,inserted_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  source_id=excluded.source_id,source_name=excluded.source_name,category=excluded.category,
                  authority=excluded.authority,title=excluded.title,url=excluded.url,
                  published_at=excluded.published_at,tags_json=excluded.tags_json,scene=excluded.scene,
                  consulting_value=excluded.consulting_value,public_value=excluded.public_value,
                  ingestion=excluded.ingestion,score=excluded.score,content_hash=excluded.content_hash,
                  updated_at=excluded.updated_at
                """,
                (
                    item_id,
                    item.get("source_id"),
                    item.get("source_name"),
                    item.get("category"),
                    item.get("authority"),
                    item.get("title"),
                    item.get("url"),
                    item.get("published_at"),
                    json.dumps(item.get("tags") or [], ensure_ascii=False),
                    item.get("scene"),
                    item.get("consulting_value"),
                    item.get("public_value"),
                    item.get("ingestion"),
                    int(item.get("score") or 0),
                    content_hash(item),
                    stamp,
                    stamp,
                ),
            )
    return added


def create_run(run_type):
    init_db()
    with connect() as conn:
        cur = execute(
            conn,
            "INSERT INTO source_runs(run_type,status,started_at,message) VALUES(?,?,?,?)",
            (run_type, "running", now(), "started"),
        )
        if using_postgres():
            row = execute(conn, "SELECT currval(pg_get_serial_sequence('source_runs','id')) AS id").fetchone()
            return row["id"]
        return cur.lastrowid


def finish_run(run_id, status, message="", added_count=0):
    data = load_public_json() if PUBLIC_JSON.exists() else {"items": [], "sources": []}
    with connect() as conn:
        execute(
            conn,
            """
            UPDATE source_runs
            SET status=?,finished_at=?,item_count=?,source_count=?,added_count=?,message=?
            WHERE id=?
            """,
            (
                status,
                now(),
                len(data.get("items", [])),
                len(data.get("sources", [])),
                added_count,
                message[:1000],
                run_id,
            ),
        )


def run_script(path):
    runpy.run_path(str(path), run_name="__main__")


def run_collection(run_type="manual"):
    run_id = create_run(run_type)
    try:
        before = len(load_public_json().get("items", [])) if PUBLIC_JSON.exists() else 0
        run_script(ROOT / "work" / "company_announcements_adapter.py")
        run_script(ROOT / "work" / "regulator_policy_adapter.py")
        run_script(ROOT / "work" / "inject_expanded_data.py")
        data = load_public_json()
        added_to_db = upsert_public_data(data)
        after = len(data.get("items", []))
        finish_run(run_id, "success", f"collection ok; json_delta={after - before}; db_added={added_to_db}", added_to_db)
        return {"ok": True, "run_id": run_id, "item_count": after, "source_count": len(data.get("sources", [])), "added_to_db": added_to_db}
    except Exception as exc:
        finish_run(run_id, "error", str(exc), 0)
        return {"ok": False, "run_id": run_id, "error": str(exc)}


def bootstrap():
    init_db()
    if PUBLIC_JSON.exists():
        return upsert_public_data(load_public_json())
    return 0


if __name__ == "__main__":
    print(json.dumps(run_collection("manual"), ensure_ascii=False, indent=2))
