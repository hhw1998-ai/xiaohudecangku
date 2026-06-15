import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs" / "bailing-public-data.json"


def U(value):
    return value.encode("ascii").decode("unicode_escape")


C = {
    "company": U("\\u516c\\u53f8\\u516c\\u544a"),
    "listed": U("\\u4e0a\\u5e02\\u516c\\u53f8"),
    "report": U("\\u5e74\\u62a5\\u5b63\\u62a5"),
    "performance": U("\\u4e1a\\u7ee9\\u9884\\u544a"),
    "ma": U("\\u5e76\\u8d2d\\u91cd\\u7ec4"),
    "investment": U("\\u91cd\\u5927\\u6295\\u8d44"),
    "risk": U("\\u98ce\\u9669\\u63d0\\u793a"),
    "finance": U("\\u878d\\u8d44\\u4e8b\\u9879"),
    "contract": U("\\u91cd\\u5927\\u5408\\u540c"),
}


CNINFO_CATEGORIES = [
    {
        "key": "reports",
        "name": U("\\u5de8\\u6f6e\\u8d44\\u8baf\\u5b9a\\u671f\\u62a5\\u544a"),
        "query_categories": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh",
        "tags": [C["report"]],
        "score": 91,
        "limit": 14,
        "value": U("\\u9002\\u5408\\u8ffd\\u8e2a\\u5ba2\\u6237\\u3001\\u7ade\\u5bf9\\u548c\\u6807\\u6746\\u516c\\u53f8\\u7684\\u5e74\\u62a5\\u3001\\u534a\\u5e74\\u62a5\\u548c\\u5b63\\u62a5\\uff0c\\u7528\\u4e8e\\u62c6\\u89e3\\u589e\\u957f\\u3001\\u5229\\u6da6\\u3001\\u73b0\\u91d1\\u6d41\\u548c\\u6218\\u7565\\u53d8\\u5316\\u3002"),
    },
    {
        "key": "performance",
        "name": U("\\u5de8\\u6f6e\\u8d44\\u8baf\\u4e1a\\u7ee9\\u9884\\u544a"),
        "query_categories": "category_yjygjxz_szsh;category_yjkb_szsh",
        "queries": [U("\\u4e1a\\u7ee9\\u9884\\u544a"), U("\\u4e1a\\u7ee9\\u5feb\\u62a5")],
        "tags": [C["performance"]],
        "score": 88,
        "limit": 10,
        "value": U("\\u9002\\u5408\\u8ffd\\u8e2a\\u4e0a\\u5e02\\u516c\\u53f8\\u4e1a\\u7ee9\\u8f6c\\u6298\\u3001\\u884c\\u4e1a\\u666f\\u6c14\\u53d8\\u5316\\u548c\\u7ecf\\u8425\\u98ce\\u9669\\u4fe1\\u53f7\\u3002"),
    },
    {
        "key": "ma",
        "name": U("\\u5de8\\u6f6e\\u8d44\\u8baf\\u5e76\\u8d2d\\u91cd\\u7ec4"),
        "query_categories": "",
        "queries": [U("\\u5e76\\u8d2d"), U("\\u91cd\\u7ec4"), U("\\u6536\\u8d2d"), U("\\u8d44\\u4ea7\\u8d2d\\u4e70")],
        "exclude": [U("\\u72ec\\u7acb\\u8d22\\u52a1\\u987e\\u95ee\\u62a5\\u544a"), U("\\u6cd5\\u5f8b\\u610f\\u89c1\\u4e66")],
        "tags": [C["ma"]],
        "score": 87,
        "limit": 8,
        "value": U("\\u9002\\u5408\\u53d1\\u73b0\\u884c\\u4e1a\\u6574\\u5408\\u3001\\u4ea7\\u4e1a\\u94fe\\u5e03\\u5c40\\u548c\\u5ba2\\u6237\\u6f5c\\u5728\\u4ea4\\u6613\\u673a\\u4f1a\\u3002"),
    },
    {
        "key": "investment",
        "name": U("\\u5de8\\u6f6e\\u8d44\\u8baf\\u6295\\u8d44\\u9879\\u76ee"),
        "query_categories": "",
        "queries": [U("\\u5bf9\\u5916\\u6295\\u8d44"), U("\\u9879\\u76ee\\u6295\\u8d44"), U("\\u589e\\u8d44"), U("\\u5408\\u8d44")],
        "exclude": [U("\\u7ba1\\u7406\\u5236\\u5ea6"), U("\\u4e0d\\u5b58\\u5728\\u76f4\\u63a5\\u6216\\u901a\\u8fc7"), U("\\u8d22\\u52a1\\u8d44\\u52a9\\u6216\\u8865\\u507f")],
        "tags": [C["investment"]],
        "score": 86,
        "limit": 8,
        "value": U("\\u9002\\u5408\\u8ffd\\u8e2a\\u4ea7\\u80fd\\u6269\\u5f20\\u3001\\u65b0\\u57fa\\u5730\\u5e03\\u5c40\\u3001\\u5408\\u8d44\\u5408\\u4f5c\\u548c\\u533a\\u57df\\u62db\\u5546\\u7ebf\\u7d22\\u3002"),
    },
    {
        "key": "risk",
        "name": U("\\u5de8\\u6f6e\\u8d44\\u8baf\\u98ce\\u9669\\u4e0e\\u76d1\\u7ba1"),
        "query_categories": "",
        "queries": [U("\\u98ce\\u9669\\u63d0\\u793a"), U("\\u7acb\\u6848"), U("\\u5904\\u7f5a"), U("\\u8b66\\u793a\\u51fd"), U("\\u95ee\\u8be2\\u51fd")],
        "exclude": [U("\\u56de\\u590d\\u516c\\u544a")],
        "tags": [C["risk"]],
        "score": 84,
        "limit": 8,
        "value": U("\\u9002\\u5408\\u7528\\u4e8e\\u8bc6\\u522b\\u5ba2\\u6237\\u3001\\u4f9b\\u5e94\\u5546\\u6216\\u6807\\u6746\\u516c\\u53f8\\u7684\\u5408\\u89c4\\u3001\\u8d22\\u52a1\\u548c\\u7ecf\\u8425\\u98ce\\u9669\\u3002"),
    },
]


def fetch_json(url, body=None, referer="http://www.cninfo.com.cn/"):
    data = None
    headers = {
        "User-Agent": "Mozilla/5.0 Bailing/1.0",
        "Accept": "application/json,text/plain,*/*",
        "Origin": "http://www.cninfo.com.cn",
        "Referer": referer,
    }
    if body is not None:
        data = urlencode(body).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = Request(url, data=data, headers=headers, method="POST" if body is not None else "GET")
    with urlopen(req, timeout=25) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def strip_html(value):
    text = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", text).strip()


def cninfo_query_once(pack, searchkey="", days=30, page_size=None):
    end = datetime.now().date()
    start = end - timedelta(days=days)
    body = {
        "pageNum": "1",
        "pageSize": str(page_size or pack["limit"]),
        "column": "szse",
        "tabName": "fulltext",
        "plate": "",
        "stock": "",
        "searchkey": searchkey,
        "secid": "",
        "category": pack.get("query_categories", ""),
        "trade": "",
        "seDate": f"{start.isoformat()}~{end.isoformat()}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    payload = fetch_json(
        "http://www.cninfo.com.cn/new/hisAnnouncement/query",
        body=body,
        referer="http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    )
    return payload.get("announcements") or []


def cninfo_query(pack):
    rows = []
    seen = set()
    queries = pack.get("queries")
    if not queries:
        queries = [pack.get("searchkey", "")]
    for query in queries:
        for ann in cninfo_query_once(pack, searchkey=query, page_size=max(pack["limit"], 20)):
            key = ann.get("announcementId") or (ann.get("secCode"), ann.get("announcementTitle"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(ann)
    return rows


def announcement_date(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000).date().isoformat()
    except Exception:
        return datetime.now().date().isoformat()


def classify_extra(title):
    tags = []
    rules = [
        (U("\\u5e74\\u5ea6\\u62a5\\u544a"), C["report"]),
        (U("\\u534a\\u5e74\\u5ea6"), C["report"]),
        (U("\\u5b63\\u5ea6\\u62a5\\u544a"), C["report"]),
        (U("\\u4e1a\\u7ee9\\u9884\\u544a"), C["performance"]),
        (U("\\u4e1a\\u7ee9\\u5feb\\u62a5"), C["performance"]),
        (U("\\u6536\\u8d2d"), C["ma"]),
        (U("\\u91cd\\u7ec4"), C["ma"]),
        (U("\\u6295\\u8d44"), C["investment"]),
        (U("\\u589e\\u8d44"), C["investment"]),
        (U("\\u5408\\u540c"), C["contract"]),
        (U("\\u98ce\\u9669"), C["risk"]),
        (U("\\u5904\\u7f5a"), C["risk"]),
        (U("\\u95ee\\u8be2\\u51fd"), C["risk"]),
        (U("\\u53ef\\u8f6c\\u503a"), C["finance"]),
        (U("\\u878d\\u8d44"), C["finance"]),
    ]
    for key, tag in rules:
        if key in title and tag not in tags:
            tags.append(tag)
    return tags


def make_item(pack, ann, index):
    title = strip_html(ann.get("announcementTitle") or ann.get("shortTitle") or "")
    sec_name = strip_html(ann.get("secName") or ann.get("tileSecName") or "")
    sec_code = ann.get("secCode") or ""
    display_title = f"{sec_name}({sec_code})：{title}" if sec_name and sec_code else title
    adjunct_url = ann.get("adjunctUrl") or ""
    url = "http://static.cninfo.com.cn/" + adjunct_url.lstrip("/") if adjunct_url else "http://www.cninfo.com.cn/"
    tags = [C["company"], C["listed"]]
    for tag in pack["tags"] + classify_extra(display_title):
        if tag not in tags:
            tags.append(tag)
    return {
        "id": f"cninfo-{pack['key']}-{ann.get('announcementId') or index}",
        "source_id": f"cninfo-{pack['key']}",
        "source_name": pack["name"],
        "category": C["company"],
        "authority": "exchange_disclosure",
        "title": display_title,
        "url": url,
        "published_at": announcement_date(ann.get("announcementTime")),
        "tags": tags[:6],
        "scene": U("\\u516c\\u53f8\\u52a8\\u5411 / \\u5e74\\u62a5\\u516c\\u544a / \\u7ade\\u5bf9\\u76d1\\u6d4b"),
        "consulting_value": pack["value"],
        "public_value": U("\\u5e2e\\u52a9\\u4f01\\u4e1a\\u4e3b\\u3001\\u6295\\u8d44\\u8005\\u548c\\u884c\\u4e1a\\u4ece\\u4e1a\\u8005\\u8ffd\\u8e2a\\u4e0a\\u5e02\\u516c\\u53f8\\u91cd\\u8981\\u516c\\u5f00\\u4fe1\\u606f\\u3002"),
        "ingestion": "cninfo_api",
        "score": max(pack["score"] - index, 70),
    }


def accepted(pack, ann):
    title = strip_html(ann.get("announcementTitle") or ann.get("shortTitle") or "")
    if not title:
        return False
    for word in pack.get("exclude", []):
        if word in title:
            return False
    queries = [q for q in pack.get("queries", []) if q]
    if queries and not any(q in title for q in queries):
        return False
    return True


def append_unique(items, additions):
    seen = {(item.get("source_id"), item.get("title")) for item in items}
    for item in additions:
        key = (item.get("source_id"), item.get("title"))
        if key not in seen:
            seen.add(key)
            items.append(item)


def replace_source(sources, source):
    for idx, old in enumerate(sources):
        if old.get("source_id") == source["source_id"]:
            sources[idx] = source
            return
    sources.append(source)


def upsert_candidate(public, name, url, status, reason):
    rows = public.setdefault("candidate_sources", [])
    for row in rows:
        if row.get("name") == name or row.get("url") == url:
            row.update({"name": name, "url": url, "status": status, "reason": reason})
            return
    rows.append({"name": name, "url": url, "status": status, "reason": reason})


def update_landscape(public, added_sources):
    landscape = public.setdefault("source_landscape", [])
    for row in landscape:
        if row.get("name") == U("\\u516c\\u53f8\\u4e0e\\u8d44\\u672c\\u5e02\\u573a"):
            row["connected"] = max(int(row.get("connected") or 0), added_sources)
            row["note"] = U("\\u4ea4\\u6613\\u6240\\u3001\\u5de8\\u6f6e\\u3001\\u5e74\\u62a5\\u516c\\u544a\\u548c\\u516c\\u53f8\\u52a8\\u5411")
            return
    landscape.append({
        "name": U("\\u516c\\u53f8\\u4e0e\\u8d44\\u672c\\u5e02\\u573a"),
        "connected": added_sources,
        "target": 20,
        "note": U("\\u4ea4\\u6613\\u6240\\u3001\\u5de8\\u6f6e\\u3001\\u5e74\\u62a5\\u516c\\u544a\\u548c\\u516c\\u53f8\\u52a8\\u5411"),
    })


def main():
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    new_items = []
    statuses = []
    for pack in CNINFO_CATEGORIES:
        started = datetime.now()
        try:
            announcements = [ann for ann in cninfo_query(pack) if accepted(pack, ann)]
            items = [make_item(pack, ann, idx) for idx, ann in enumerate(announcements[: pack["limit"]])]
            new_items.extend(items)
            statuses.append({
                "source_id": f"cninfo-{pack['key']}",
                "name": pack["name"],
                "url": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
                "status": "ok" if items else "empty",
                "items": len(items),
                "mode": "cninfo_api",
                "category": C["company"],
                "latency_ms": int((datetime.now() - started).total_seconds() * 1000),
            })
        except Exception as exc:
            statuses.append({
                "source_id": f"cninfo-{pack['key']}",
                "name": pack["name"],
                "url": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
                "status": "error",
                "items": 0,
                "mode": "cninfo_api",
                "category": C["company"],
                "error": str(exc)[:180],
                "latency_ms": int((datetime.now() - started).total_seconds() * 1000),
            })

    append_unique(public["items"], new_items)
    for source in statuses:
        replace_source(public["sources"], source)

    upsert_candidate(
        public,
        U("\\u4e0a\\u4ea4\\u6240\\u4e0a\\u5e02\\u516c\\u53f8\\u516c\\u544a"),
        "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
        "next_adapter",
        U("\\u5df2\\u5148\\u7528\\u5de8\\u6f6e API \\u8986\\u76d6\\u6caa\\u6df1\\u516c\\u544a\\uff0c\\u540e\\u7eed\\u518d\\u8865\\u4ea4\\u6613\\u6240\\u539f\\u751f\\u63a5\\u53e3\\u4f5c\\u6821\\u9a8c\\u548c\\u5e02\\u573a\\u5206\\u5c42"),
    )
    upsert_candidate(
        public,
        U("\\u6df1\\u4ea4\\u6240\\u4e0a\\u5e02\\u516c\\u53f8\\u516c\\u544a"),
        "https://www.szse.cn/disclosure/listed/notice/index.html",
        "next_adapter",
        U("\\u5df2\\u5148\\u7528\\u5de8\\u6f6e API \\u8986\\u76d6\\u6caa\\u6df1\\u516c\\u544a\\uff0c\\u540e\\u7eed\\u518d\\u8865\\u4ea4\\u6613\\u6240\\u539f\\u751f\\u63a5\\u53e3\\u4f5c\\u6821\\u9a8c\\u548c\\u5e02\\u573a\\u5206\\u5c42"),
    )

    public["item_count"] = len(public["items"])
    public["version"] = "source-expanded-company-announcements"
    public["generated_at"] = datetime.now().replace(microsecond=0).isoformat()
    update_landscape(public, sum(1 for s in statuses if s["status"] == "ok"))
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"added_items": len(new_items), "item_count": public["item_count"], "sources": len(public["sources"]), "statuses": statuses}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
