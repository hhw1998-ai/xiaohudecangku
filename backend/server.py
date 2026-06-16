import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pipeline


ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
DEFAULT_USER = "demo-consultant"
DAILY_HOUR = int(os.environ.get("BAILING_DAILY_HOUR", "7"))


def U(value):
    return value.encode("ascii").decode("unicode_escape")


def now():
    return datetime.now().replace(microsecond=0).isoformat()


def db_status():
    return {
        "driver": "postgres" if pipeline.using_postgres() else "sqlite",
        "database_url_present": bool(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")),
        "db": "postgres" if pipeline.using_postgres() else str(pipeline.DB),
    }


def rows(sql, params=()):
    with pipeline.connect() as conn:
        return [dict(row) for row in pipeline.execute(conn, sql, params)]


def one(sql, params=()):
    result = rows(sql, params)
    return result[0] if result else None


def decode_tags(row):
    row = dict(row)
    for key in ["tags_json", "keywords_json", "categories_json", "items_json"]:
        if key in row:
            try:
                row[key.replace("_json", "")] = json.loads(row.pop(key) or "[]")
            except json.JSONDecodeError:
                row[key.replace("_json", "")] = []
    return row


def item_where(query):
    clauses = []
    params = []
    if query.get("category"):
        clauses.append("category = ?")
        params.append(query["category"][0])
    if query.get("source_id"):
        clauses.append("source_id = ?")
        params.append(query["source_id"][0])
    if query.get("q"):
        term = f"%{query['q'][0]}%"
        clauses.append("(title LIKE ? OR source_name LIKE ? OR tags_json LIKE ? OR consulting_value LIKE ?)")
        params.extend([term, term, term, term])
    if query.get("since"):
        clauses.append("published_at >= ?")
        params.append(query["since"][0])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


def get_items(query):
    limit = min(int(query.get("limit", ["50"])[0]), 200)
    where, params = item_where(query)
    sql = f"""
      SELECT * FROM items
      {where}
      ORDER BY published_at DESC, score DESC
      LIMIT ?
    """
    return [decode_tags(row) for row in rows(sql, params + [limit])]


def create_brief(payload):
    user_id = payload.get("user_id") or DEFAULT_USER
    title = payload.get("title") or U("\\u4eca\\u65e5\\u60c5\\u62a5\\u7b80\\u62a5")
    keywords = payload.get("keywords") or []
    categories = payload.get("categories") or []
    limit = int(payload.get("limit") or 12)
    terms = []
    params = []
    if categories:
        terms.append("category IN (%s)" % ",".join("?" for _ in categories))
        params.extend(categories)
    if keywords:
        keyword_terms = []
        for keyword in keywords:
            keyword_terms.append("(title LIKE ? OR tags_json LIKE ? OR consulting_value LIKE ?)")
            like = f"%{keyword}%"
            params.extend([like, like, like])
        terms.append("(" + " OR ".join(keyword_terms) + ")")
    where = " WHERE " + " AND ".join(terms) if terms else ""
    sql = f"SELECT * FROM items {where} ORDER BY published_at DESC, score DESC LIMIT ?"
    picked = [decode_tags(row) for row in rows(sql, params + [limit])]
    themes = {}
    for item in picked:
        themes[item["category"]] = themes.get(item["category"], 0) + 1
    summary = U("\\uff1b").join([f"{k}{v}{U('\\u6761')}" for k, v in themes.items()]) or U("\\u6682\\u65e0\\u5339\\u914d\\u4fe1\\u606f")
    brief = {
        "id": "brief-" + uuid.uuid4().hex[:12],
        "user_id": user_id,
        "title": title,
        "brief_type": payload.get("brief_type") or "daily",
        "generated_at": now(),
        "summary": U("\\u672c\\u6b21\\u751f\\u6210 ") + f"{len(picked)}" + U(" \\u6761\\u4fe1\\u606f\\uff0c\\u8986\\u76d6 ") + summary + U("\\u3002"),
        "items": picked,
    }
    with pipeline.connect() as conn:
        pipeline.execute(
            conn,
            "INSERT INTO briefs(id,user_id,title,brief_type,generated_at,summary,items_json) VALUES(?,?,?,?,?,?,?)",
            (
                brief["id"],
                brief["user_id"],
                brief["title"],
                brief["brief_type"],
                brief["generated_at"],
                brief["summary"],
                json.dumps([item["id"] for item in picked], ensure_ascii=False),
            ),
        )
    return brief


def create_watchlist(payload):
    watch = {
        "id": "watch-" + uuid.uuid4().hex[:12],
        "user_id": payload.get("user_id") or DEFAULT_USER,
        "name": payload.get("name") or U("\\u672a\\u547d\\u540d\\u5173\\u6ce8"),
        "keywords": payload.get("keywords") or [],
        "categories": payload.get("categories") or [],
        "created_at": now(),
        "updated_at": now(),
    }
    with pipeline.connect() as conn:
        pipeline.execute(
            conn,
            "INSERT INTO watchlists(id,user_id,name,keywords_json,categories_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (
                watch["id"],
                watch["user_id"],
                watch["name"],
                json.dumps(watch["keywords"], ensure_ascii=False),
                json.dumps(watch["categories"], ensure_ascii=False),
                watch["created_at"],
                watch["updated_at"],
            ),
        )
    return watch


def impact_matrix(payload):
    keywords = payload.get("keywords") or []
    if not keywords and payload.get("topic"):
        keywords = [payload["topic"]]
    items = create_brief({"keywords": keywords, "categories": payload.get("categories") or [], "limit": payload.get("limit") or 10})["items"]
    matrix = []
    for item in items:
        title = item["title"]
        strength = U("\\u9ad8") if item.get("score", 0) >= 88 or any(word in title for word in [U("\\u89c4\\u5212"), U("\\u610f\\u89c1"), U("\\u529e\\u6cd5"), U("\\u76ee\\u5f55")]) else U("\\u4e2d")
        matrix.append({
            "item_id": item["id"],
            "title": title,
            "source": item["source_name"],
            "published_at": item["published_at"],
            "affected_object": U("\\u4f01\\u4e1a\\u7ecf\\u8425 / \\u884c\\u4e1a\\u7ade\\u4e89 / \\u9879\\u76ee\\u673a\\u4f1a"),
            "impact_strength": strength,
            "consulting_action": U("\\u7eb3\\u5165\\u5ba2\\u6237\\u6668\\u62a5\\uff0c\\u7ed3\\u5408\\u5ba2\\u6237\\u4e1a\\u52a1\\u7ebf\\u5224\\u65ad\\u673a\\u4f1a\\u3001\\u7ea6\\u675f\\u548c\\u98ce\\u9669\\u3002"),
            "url": item["url"],
        })
    return {"topic": U("\\u3001").join(keywords) or U("\\u5168\\u90e8"), "generated_at": now(), "matrix": matrix}


def next_daily_time():
    current = datetime.now()
    target = current.replace(hour=DAILY_HOUR, minute=0, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return target


def scheduler_loop():
    next_run = next_daily_time()
    while True:
        if datetime.now() >= next_run:
            pipeline.run_collection("scheduled")
            next_run = next_daily_time()
        time.sleep(30)


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        super().end_headers()

    def send_json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                db = db_status()
                self.send_json({
                    "ok": True,
                    "time": now(),
                    "db": db["db"],
                    "driver": db["driver"],
                    "database_url_present": db["database_url_present"],
                    "next_scheduled_run": next_daily_time().isoformat(),
                    "counts": {
                        "items": one("SELECT COUNT(*) AS n FROM items")["n"],
                        "sources": one("SELECT COUNT(*) AS n FROM sources")["n"],
                    },
                })
            elif parsed.path == "/api/items":
                self.send_json({"items": get_items(query)})
            elif parsed.path == "/api/sources":
                self.send_json({"sources": rows("SELECT * FROM sources ORDER BY category,name")})
            elif parsed.path == "/api/runs":
                self.send_json({"runs": rows("SELECT * FROM source_runs ORDER BY id DESC LIMIT 30")})
            elif parsed.path == "/api/watchlists":
                user_id = query.get("user_id", [DEFAULT_USER])[0]
                data = [decode_tags(row) for row in rows("SELECT * FROM watchlists WHERE user_id=? ORDER BY updated_at DESC", (user_id,))]
                self.send_json({"watchlists": data})
            elif parsed.path == "/api/briefs":
                user_id = query.get("user_id", [DEFAULT_USER])[0]
                self.send_json({"briefs": rows("SELECT * FROM briefs WHERE user_id=? ORDER BY generated_at DESC LIMIT 20", (user_id,))})
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/collect/run":
                result = pipeline.run_collection("manual")
                self.send_json(result, 200 if result.get("ok") else 500)
            elif parsed.path == "/api/briefs/generate":
                self.send_json(create_brief(payload))
            elif parsed.path == "/api/watchlists":
                self.send_json(create_watchlist(payload))
            elif parsed.path == "/api/impact-matrix":
                self.send_json(impact_matrix(payload))
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)


def main():
    added = pipeline.bootstrap()
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Bailing backend running at http://{HOST}:{PORT}")
    print(f"Bootstrapped database; added {added} existing items.")
    print(f"Daily collection scheduled around {DAILY_HOUR:02d}:00 local time.")
    server.serve_forever()


if __name__ == "__main__":
    main()
