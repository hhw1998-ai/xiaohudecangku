import json
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PUBLIC = ROOT / "outputs" / "bailing-public-data.json"
OUT_SPACES = ROOT / "outputs" / "bailing-industry-spaces-data.json"
OUT_AUTH = ROOT / "outputs" / "zhigeng-auth-workspace-data.json"
APP_HTML = ROOT / "app" / "index.html"


def U(value):
    return value.encode("ascii").decode("unicode_escape")


C = {
    "consulting": U("\\u54a8\\u8be2\\u673a\\u6784\\u6d1e\\u5bdf"),
    "company": U("\\u516c\\u53f8\\u516c\\u544a"),
    "soe": U("\\u56fd\\u4f01\\u592e\\u4f01"),
    "reg": U("\\u4ea7\\u4e1a\\u76d1\\u7ba1"),
    "local": U("\\u5730\\u65b9\\u653f\\u7b56"),
    "energy": U("\\u80fd\\u6e90"),
    "policy": U("\\u56fd\\u5bb6\\u653f\\u7b56"),
    "source_map": U("\\u4fe1\\u6e90\\u7248\\u56fe"),
    "expanded": U("\\u5df2\\u6269\\u5c55"),
}


DIRECT_SOURCES = [
    {
        "id": "mckinsey-cn-insights",
        "name": U("\\u9ea6\\u80af\\u9521\\u4e2d\\u6587\\u6d1e\\u5bdf"),
        "url": "https://www.mckinsey.com.cn/insights/",
        "category": C["consulting"],
        "authority": "consulting_firm",
        "mode": "insight_links",
        "limit": 8,
        "include": ["/insights/"],
    },
    {
        "id": "pwc-cn-insights",
        "name": U("\\u666e\\u534e\\u6c38\\u9053\\u7814\\u7a76\\u4e0e\\u6d1e\\u5bdf"),
        "url": "https://www.pwccn.com/zh/research-and-insights.html",
        "category": C["consulting"],
        "authority": "consulting_firm",
        "mode": "insight_links",
        "limit": 8,
        "include": ["/zh/"],
    },
    {
        "id": "sasac-news",
        "name": U("\\u56fd\\u8d44\\u59d4\\u65b0\\u95fb\\u53d1\\u5e03"),
        "url": "http://www.sasac.gov.cn/n2588025/index.html",
        "category": C["soe"],
        "authority": "ministry",
        "mode": "html_links",
        "limit": 8,
        "include": ["/n2588025/", "/n2588030/", "/n2588035/"],
    },
    {
        "id": "sasac-policy",
        "name": U("\\u56fd\\u8d44\\u59d4\\u653f\\u52a1\\u516c\\u5f00"),
        "url": "http://www.sasac.gov.cn/n2588035/n2588320/index.html",
        "category": C["soe"],
        "authority": "ministry",
        "mode": "html_links",
        "limit": 8,
        "include": ["/n2588035/", "/n2588320/"],
    },
]


BACKLOG = [
    (U("\\u5de5\\u4fe1\\u90e8\\u6587\\u4ef6\\u53d1\\u5e03"), "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html", C["reg"], "needs_adapter", U("\\u9875\\u9762\\u4e3a\\u52a8\\u6001\\u7ec4\\u4ef6\\uff0c\\u9700\\u8ffd\\u8e2a\\u63a5\\u53e3\\u6216\\u6d4f\\u89c8\\u5668\\u9002\\u914d")),
    (U("\\u5de5\\u4fe1\\u90e8\\u53f8\\u5c40\\u52a8\\u6001"), "https://www.miit.gov.cn/xwdt/gxdt/sjdt/index.html", C["reg"], "needs_adapter", U("\\u80fd\\u8bbf\\u95ee\\uff0c\\u4f46\\u5217\\u8868\\u6570\\u636e\\u9700\\u63d0\\u53d6\\u5185\\u5d4c\\u63a5\\u53e3")),
    (U("\\u5e02\\u573a\\u76d1\\u7ba1\\u603b\\u5c40\\u65b0\\u95fb"), "https://www.samr.gov.cn/xw/zj/", C["reg"], "needs_adapter", U("\\u9875\\u9762\\u53ef\\u8bbf\\u95ee\\uff0c\\u9700\\u8865\\u5145\\u771f\\u6b63\\u5217\\u8868\\u63a5\\u53e3")),
    (U("\\u5e02\\u573a\\u76d1\\u7ba1\\u603b\\u5c40\\u653f\\u7b56"), "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/", C["reg"], "needs_adapter", U("\\u9875\\u9762\\u53ef\\u8bbf\\u95ee\\uff0c\\u9700\\u5206\\u6790\\u4fe1\\u606f\\u516c\\u5f00\\u5217\\u8868\\u63a5\\u53e3")),
    (U("\\u56fd\\u5bb6\\u80fd\\u6e90\\u5c40\\u8981\\u95fb"), "https://www.nea.gov.cn/xwzx/nyyw.htm", C["energy"], "needs_adapter", U("\\u9996\\u9875\\u58f3\\u53ef\\u8bbf\\u95ee\\uff0c\\u8981\\u95fb\\u5217\\u8868\\u9700\\u5b9a\\u5411\\u9002\\u914d")),
    (U("\\u6d77\\u5173\\u603b\\u7f72\\u65b0\\u95fb"), "http://www.customs.gov.cn/customs/302249/302266/302267/index.html", C["reg"], "blocked_or_headers", U("\\u8fd4\\u56de 412\\uff0c\\u9700\\u589e\\u5f3a\\u8bf7\\u6c42\\u5934\\u6216\\u4ee3\\u7406\\u7b56\\u7565")),
    (U("\\u4e0a\\u4ea4\\u6240\\u4e0a\\u5e02\\u516c\\u53f8\\u516c\\u544a"), "https://www.sse.com.cn/disclosure/listedinfo/announcement/", C["company"], "needs_api", U("\\u9700\\u63a5\\u5165\\u52a8\\u6001 API\\uff0c\\u7528\\u4e8e\\u5e74\\u62a5\\u3001\\u516c\\u544a\\u548c\\u516c\\u53f8\\u52a8\\u5411")),
    (U("\\u6df1\\u4ea4\\u6240\\u4e0a\\u5e02\\u516c\\u53f8\\u516c\\u544a"), "https://www.szse.cn/disclosure/listed/notice/index.html", C["company"], "needs_api", U("\\u9700\\u63a5\\u5165\\u52a8\\u6001 API\\uff0c\\u7528\\u4e8e\\u5e74\\u62a5\\u3001\\u516c\\u544a\\u548c\\u516c\\u53f8\\u52a8\\u5411")),
    (U("\\u5de8\\u6f6e\\u8d44\\u8baf\\u516c\\u544a\\u641c\\u7d22"), "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search", C["company"], "needs_api", U("\\u9875\\u9762\\u4e3a\\u524d\\u7aef\\u5e94\\u7528\\uff0c\\u9700\\u76f4\\u63a5\\u5c01\\u88c5\\u516c\\u544a\\u641c\\u7d22\\u63a5\\u53e3")),
    (U("\\u6c5f\\u82cf\\u7701\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "https://www.jiangsu.gov.cn/col/col64797/index.html", C["local"], "needs_adapter", U("\\u80fd\\u8bbf\\u95ee\\uff0c\\u65e5\\u671f\\u8f83\\u591a\\uff0c\\u9700\\u5b9a\\u5236\\u5217\\u8868\\u89e3\\u6790")),
    (U("BCG \\u516c\\u5f00\\u6d1e\\u5bdf"), "https://www.bcg.com/zh-cn/publications", C["consulting"], "needs_filter", U("\\u53ef\\u8bbf\\u95ee\\uff0c\\u9700\\u52a0\\u884c\\u4e1a\\u6d1e\\u5bdf\\u94fe\\u63a5\\u8fc7\\u6ee4")),
]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.current = {"href": attrs.get("href", ""), "title": attrs.get("title", ""), "text": []}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            title = clean(self.current["title"] or "".join(self.current["text"]))
            href = self.current["href"]
            if href and title and not href.lower().startswith(("javascript:", "mailto:", "#")):
                self.links.append({"title": title[:160], "href": href})
            self.current = None


def clean(value):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 BailingExpand/1.0",
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://www.gov.cn/",
    })
    with urlopen(req, timeout=20) as resp:
        raw = resp.read()
        ct = resp.headers.get("content-type", "")
    encs = []
    m = re.search(r"charset=([\w-]+)", ct, re.I)
    if m:
        encs.append(m.group(1))
    encs += ["utf-8-sig", "utf-8", "gb18030"]
    for enc in encs:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def infer_date(html):
    m = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", html)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return datetime.now().date().isoformat()


def build_items(source):
    html = fetch(source["url"])
    parser = LinkParser()
    parser.feed(html)
    items = []
    seen = set()
    for link in parser.links:
        title = link["title"]
        href = link["href"]
        if title in seen or len(title) < 8:
            continue
        absolute = urljoin(source["url"], href)
        if source.get("include") and not any(part in absolute for part in source["include"]):
            continue
        if any(skip in title.lower() for skip in ["english", "app", "cookie", "privacy", "contact", "首页", "主页", "服务"]):
            continue
        seen.add(title)
        items.append(make_item(source, title, absolute, infer_date(html), len(items)))
        if len(items) >= source.get("limit", 8):
            break
    return items


def tags_for(source, title):
    tags = [source["category"]]
    for key, tag in [
        (U("\\u6d1e\\u5bdf"), U("\\u673a\\u6784\\u89c2\\u70b9")),
        (U("\\u7814\\u7a76"), U("\\u7814\\u7a76\\u62a5\\u544a")),
        (U("\\u6570\\u5b57"), U("\\u6570\\u5b57\\u5316")),
        (U("\\u6c7d\\u8f66"), U("\\u6c7d\\u8f66")),
        (U("\\u91d1\\u878d"), U("\\u91d1\\u878d")),
        (U("\\u56fd\\u8d44"), U("\\u56fd\\u4f01")),
        (U("\\u4e2d\\u592e\\u4f01\\u4e1a"), U("\\u592e\\u4f01")),
    ]:
        if key in title and tag not in tags:
            tags.append(tag)
    return tags[:5]


def make_item(source, title, url, date, index):
    if source["category"] == C["consulting"]:
        scene = U("\\u673a\\u6784\\u6d1e\\u5bdf / \\u884c\\u4e1a\\u7814\\u7a76 / \\u5ba2\\u6237\\u7b80\\u62a5")
        value = U("\\u9002\\u5408\\u7528\\u4e8e\\u8865\\u5145\\u987e\\u95ee\\u89c2\\u70b9\\u3001\\u6807\\u6746\\u6848\\u4f8b\\u548c\\u884c\\u4e1a\\u8d8b\\u52bf\\u5224\\u65ad\\u3002")
    elif source["category"] == C["soe"]:
        scene = U("\\u56fd\\u4f01\\u592e\\u4f01 / \\u516c\\u53f8\\u52a8\\u5411 / \\u884c\\u4e1a\\u683c\\u5c40")
        value = U("\\u9002\\u5408\\u8ffd\\u8e2a\\u592e\\u4f01\\u6539\\u9769\\u3001\\u91cd\\u5927\\u9879\\u76ee\\u548c\\u56fd\\u8d44\\u76d1\\u7ba1\\u52a8\\u5411\\u3002")
    else:
        scene = U("\\u4fe1\\u6e90\\u6269\\u5c55 / \\u884c\\u4e1a\\u89c2\\u5bdf")
        value = U("\\u9002\\u5408\\u7528\\u4e8e\\u8865\\u5145\\u884c\\u4e1a\\u4fe1\\u53f7\\u548c\\u9879\\u76ee\\u80cc\\u666f\\u3002")
    return {
        "id": f"{source['id']}-{index + 1}",
        "source_id": source["id"],
        "source_name": source["name"],
        "category": source["category"],
        "authority": source["authority"],
        "title": title,
        "url": url,
        "published_at": date,
        "tags": tags_for(source, title),
        "scene": scene,
        "consulting_value": value,
        "public_value": U("\\u5e2e\\u52a9\\u5173\\u6ce8\\u4ea7\\u4e1a\\u548c\\u7ecf\\u8425\\u7684\\u7528\\u6237\\u5feb\\u901f\\u83b7\\u53d6\\u53ef\\u5f15\\u7528\\u7684\\u516c\\u5f00\\u4fe1\\u606f\\u3002"),
        "ingestion": "source_expand_pack",
        "score": max(84 - index * 2, 66),
    }


def source_status(source, items, started):
    return {
        "source_id": source["id"],
        "name": source["name"],
        "url": source["url"],
        "status": "ok" if items else "empty",
        "items": len(items),
        "mode": source["mode"],
        "category": source["category"],
        "latency_ms": int((datetime.now() - started).total_seconds() * 1000),
    }


def append_unique(items, additions):
    seen = {(item.get("source_id"), item.get("title")) for item in items}
    for item in additions:
        key = (item.get("source_id"), item.get("title"))
        if key not in seen:
            seen.add(key)
            items.append(item)


def main():
    public = json.loads(OUT_PUBLIC.read_text(encoding="utf-8"))
    source_ids = {s["source_id"] for s in public["sources"]}
    all_new = []
    new_status = []
    for source in DIRECT_SOURCES:
        if source["id"] in source_ids:
            continue
        started = datetime.now()
        try:
            items = build_items(source)
            all_new.extend(items)
            new_status.append(source_status(source, items, started))
        except Exception as exc:
            new_status.append({
                "source_id": source["id"],
                "name": source["name"],
                "url": source["url"],
                "status": "error",
                "items": 0,
                "mode": source["mode"],
                "category": source["category"],
                "error": str(exc),
            })
    append_unique(public["items"], all_new)
    public["items"].sort(key=lambda item: item["published_at"], reverse=True)
    public["sources"].extend(new_status)
    public["source_landscape"] = [
        {"name": U("\\u653f\\u7b56\\u76d1\\u7ba1"), "connected": 14, "target": 35, "note": U("\\u56fd\\u5bb6\\u90e8\\u59d4\\u3001\\u76d1\\u7ba1\\u673a\\u6784\\u548c\\u653f\\u7b56\\u5165\\u53e3")},
        {"name": U("\\u5730\\u65b9\\u653f\\u7b56"), "connected": 3, "target": 30, "note": U("\\u91cd\\u70b9\\u7701\\u5e02\\u3001\\u56ed\\u533a\\u3001\\u62db\\u5546\\u653f\\u7b56")},
        {"name": U("\\u516c\\u53f8\\u4e0e\\u8d44\\u672c\\u5e02\\u573a"), "connected": 0, "target": 20, "note": U("\\u4ea4\\u6613\\u6240\\u3001\\u5de8\\u6f6e\\u3001\\u5e74\\u62a5\\u516c\\u544a\\u548c\\u516c\\u53f8\\u52a8\\u5411")},
        {"name": U("\\u673a\\u6784\\u7814\\u7a76\\u4e0e\\u54a8\\u8be2\\u6d1e\\u5bdf"), "connected": 2, "target": 25, "note": U("\\u54a8\\u8be2\\u516c\\u53f8\\u3001\\u5238\\u5546\\u7814\\u62a5\\u3001\\u6295\\u8d44\\u673a\\u6784\\u89c2\\u70b9")},
        {"name": U("\\u4ea7\\u4e1a\\u5a92\\u4f53"), "connected": 1, "target": 20, "note": U("\\u4ea7\\u4e1a\\u5a92\\u4f53\\u3001\\u5782\\u76f4\\u5a92\\u4f53\\u548c\\u516c\\u5f00\\u4e13\\u680f")},
    ]
    for name, url, category, status, reason in BACKLOG:
        if not any(c.get("url") == url for c in public.get("candidate_sources", [])):
            public.setdefault("candidate_sources", []).append({"name": name, "url": url, "status": status, "reason": reason, "category": category})
    public["version"] = "source-expanded-pack-3"
    public["generated_at"] = datetime.now().isoformat(timespec="seconds")
    public["item_count"] = len(public["items"])
    OUT_PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")

    spaces = json.loads(OUT_SPACES.read_text(encoding="utf-8"))
    spaces["source_item_count"] = public["item_count"]
    spaces["input_generated_at"] = public["generated_at"]
    spaces["version"] = "industry-spaces-expanded-pack-3"
    for space in spaces.get("spaces", []):
        if space.get("id") == "consulting":
            additions = [item for item in public["items"] if item.get("category") == C["consulting"]][:6]
            existing = {item.get("item_id") for item in space.get("top_items", [])}
            for item in additions:
                if item["id"] not in existing:
                    space["top_items"].append({
                        "item_id": item["id"],
                        "title": item["title"],
                        "url": item["url"],
                        "source_name": item["source_name"],
                        "category": item["category"],
                        "published_at": item["published_at"],
                        "score": item["score"],
                        "matches": item["tags"][1:],
                        "scene": item["scene"],
                        "consulting_value": item["consulting_value"],
                    })
            space["item_count"] += len(additions)
    OUT_SPACES.write_text(json.dumps(spaces, ensure_ascii=False, indent=2), encoding="utf-8")

    auth = json.loads(OUT_AUTH.read_text(encoding="utf-8"))
    auth["source_item_count"] = public["item_count"]
    auth["industry_input_generated_at"] = spaces.get("generated_at")
    auth["version"] = "auth-workspace-expanded-pack-3"
    OUT_AUTH.write_text(json.dumps(auth, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"added_items": len(all_new), "added_sources": len(new_status), "total_items": public["item_count"], "total_sources": len(public["sources"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
