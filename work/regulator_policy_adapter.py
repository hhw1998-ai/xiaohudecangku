import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs" / "bailing-public-data.json"
SPACES = ROOT / "outputs" / "bailing-industry-spaces-data.json"
AUTH = ROOT / "outputs" / "zhigeng-auth-workspace-data.json"


def U(value):
    return value.encode("ascii").decode("unicode_escape")


REG = U("\\u4ea7\\u4e1a\\u76d1\\u7ba1")
POLICY = U("\\u653f\\u7b56\\u6587\\u4ef6")
MIIT = U("\\u5de5\\u4fe1\\u90e8\\u653f\\u7b56\\u6587\\u4ef6")


def strip_html(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value or "")).strip()


def date_from_ms(value):
    try:
        return datetime.fromtimestamp(int(value) / 1000).date().isoformat()
    except Exception:
        return datetime.now().date().isoformat()


def fetch_json(url, params):
    req = Request(
        url + "?" + urlencode(params),
        headers={
            "User-Agent": "Mozilla/5.0 Bailing/1.0",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.miit.gov.cn/search/wjfb.html?websiteid=110000000000000&pg=&p=&tpl=14&category=51&q=",
        },
    )
    with urlopen(req, timeout=25) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8-sig", errors="replace"))


def miit_query(limit=14):
    params = {
        "websiteid": "110000000000000",
        "scope": "basic",
        "q": "",
        "pg": str(limit),
        "cateid": "57",
        "pos": "title_text,infocontent,titlepy",
        "_cus_eq_typename": "",
        "_cus_eq_publishgroupname": "",
        "_cus_eq_themename": "",
        "begin": "",
        "end": "",
        "dateField": "deploytime",
        "selectFields": "title,content,deploytime,_index,url,cdate,infoextends,infocontentattribute,columnname,filenumbername,publishgroupname,publishtime,metaid,bexxgk,columnid,xxgkextend1,xxgkextend2,themename,typename,indexcode,createdate",
        "group": "distinct",
        "highlightConfigs": '[{"field":"infocontent","numberOfFragments":2,"fragmentOffset":0,"fragmentSize":30,"noMatchSize":145}]',
        "highlightFields": "title_text,infocontent,webid",
        "level": "6",
        "sortFields": '[{"name":"deploytime","type":"desc"}]',
        "p": "1",
    }
    payload = fetch_json("https://www.miit.gov.cn/search-front-server/api/search/info", params)
    rows = payload.get("data", {}).get("searchResult", {}).get("dataResults", [])
    out = []
    for row in rows:
        group = row.get("groupData") or []
        if not group:
            continue
        data = group[0].get("data") or {}
        if data.get("title"):
            out.append(data)
    return out


def tags_for(row):
    title = strip_html(row.get("title"))
    tags = [REG, POLICY]
    for value in [row.get("themename"), row.get("typename"), row.get("publishgroupname")]:
        value = strip_html(value)
        if value and value not in tags:
            tags.append(value)
    for key, tag in [
        (U("\\u4e2d\\u5c0f\\u4f01\\u4e1a"), U("\\u4e2d\\u5c0f\\u4f01\\u4e1a")),
        (U("\\u65b0\\u80fd\\u6e90"), U("\\u65b0\\u80fd\\u6e90")),
        (U("\\u6c7d\\u8f66"), U("\\u6c7d\\u8f66")),
        (U("\\u4eba\\u5de5\\u667a\\u80fd"), U("\\u4eba\\u5de5\\u667a\\u80fd")),
        (U("\\u4fe1\\u606f\\u901a\\u4fe1"), U("\\u4fe1\\u901a")),
        (U("\\u6807\\u51c6"), U("\\u6807\\u51c6")),
        (U("\\u6d88\\u8d39\\u54c1"), U("\\u6d88\\u8d39\\u54c1")),
        (U("\\u98df\\u54c1"), U("\\u98df\\u54c1")),
    ]:
        if key in title and tag not in tags:
            tags.append(tag)
    return tags[:6]


def make_item(row, index):
    title = strip_html(row.get("title"))
    url = urljoin("https://www.miit.gov.cn", row.get("url") or "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", row.get("url") or str(index)).strip("-")[-80:] or str(index)
    office = strip_html(row.get("publishgroupname") or row.get("columnname") or "")
    theme = strip_html(row.get("themename") or row.get("typename") or "")
    value = U("\\u9002\\u5408\\u8ffd\\u8e2a\\u5de5\\u4e1a\\u3001\\u4fe1\\u606f\\u5316\\u3001\\u88c5\\u5907\\u3001\\u6c7d\\u8f66\\u3001\\u539f\\u6750\\u6599\\u3001\\u4e2d\\u5c0f\\u4f01\\u4e1a\\u7b49\\u9886\\u57df\\u7684\\u653f\\u7b56\\u7a97\\u53e3\\u3001\\u9879\\u76ee\\u7ea6\\u675f\\u548c\\u4ea7\\u4e1a\\u673a\\u4f1a\\u3002")
    if theme or office:
        value += f" {U('\\u4e3b\\u9898')}:{theme or '-'}; {U('\\u673a\\u6784')}:{office or '-'}."
    return {
        "id": f"miit-policy-{slug}-{index}",
        "source_id": "miit-policy-files",
        "source_name": MIIT,
        "category": REG,
        "authority": "ministry",
        "title": title,
        "url": url,
        "published_at": date_from_ms(row.get("publishtime") or row.get("deploytime")),
        "tags": tags_for(row),
        "scene": U("\\u4ea7\\u4e1a\\u76d1\\u7ba1 / \\u653f\\u7b56\\u8ffd\\u8e2a / \\u884c\\u4e1a\\u7a97\\u53e3"),
        "consulting_value": value,
        "public_value": U("\\u5e2e\\u52a9\\u4f01\\u4e1a\\u4e3b\\u548c\\u884c\\u4e1a\\u4ece\\u4e1a\\u8005\\u4e86\\u89e3\\u5de5\\u4e1a\\u548c\\u4fe1\\u606f\\u5316\\u9886\\u57df\\u7684\\u653f\\u7b56\\u53d8\\u5316\\u3002"),
        "ingestion": "miit_search_api",
        "score": max(90 - index, 72),
    }


def append_unique(items, additions):
    seen = {(item.get("source_id"), item.get("title")) for item in items}
    for item in additions:
        key = (item.get("source_id"), item.get("title"))
        if key not in seen:
            seen.add(key)
            items.append(item)


def normalize_ids(public):
    used = set()
    for idx, item in enumerate(public["items"]):
        item_id = item.get("id") or f"item-{idx}"
        if item.get("source_id") == "miit-policy-files":
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", item.get("url") or str(idx)).strip("-")[-80:] or str(idx)
            item_id = f"miit-policy-{slug}-{idx}"
        if item_id in used:
            item_id = f"{item_id}-{idx}"
        used.add(item_id)
        item["id"] = item_id


def replace_source(sources, source):
    for idx, old in enumerate(sources):
        if old.get("source_id") == source["source_id"]:
            sources[idx] = source
            return
    sources.append(source)


def remove_low_value(public):
    bad_parts = [U("\\u56fd\\u52a1\\u9662\\u5ba2\\u6237\\u7aef"), U("\\u5c0f\\u7a0b\\u5e8f"), "App", "APP"]
    before = len(public["items"])
    public["items"] = [item for item in public["items"] if not any(part in item.get("title", "") for part in bad_parts)]
    return before - len(public["items"])


def update_dependents(public):
    for path in [SPACES, AUTH]:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["source_item_count"] = public["item_count"]
        payload["input_generated_at"] = public.get("generated_at", payload.get("input_generated_at"))
        payload["industry_input_generated_at"] = public.get("generated_at", payload.get("industry_input_generated_at"))
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def update_landscape(public):
    for row in public.setdefault("source_landscape", []):
        if row.get("name") == U("\\u653f\\u7b56\\u76d1\\u7ba1"):
            row["connected"] = max(int(row.get("connected") or 0), 15)
            row["note"] = U("\\u56fd\\u5bb6\\u90e8\\u59d4\\u3001\\u76d1\\u7ba1\\u673a\\u6784\\u548c\\u653f\\u7b56\\u5165\\u53e3\\uff0c\\u5df2\\u63a5\\u5165\\u5de5\\u4fe1\\u90e8\\u653f\\u7b56\\u5e93 API")
            return


def main():
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    removed = remove_low_value(public)
    started = datetime.now()
    rows = miit_query(limit=14)
    items = [make_item(row, idx) for idx, row in enumerate(rows)]
    append_unique(public["items"], items)
    normalize_ids(public)
    replace_source(public["sources"], {
        "source_id": "miit-policy-files",
        "name": MIIT,
        "url": "https://www.miit.gov.cn/search/wjfb.html?websiteid=110000000000000&pg=&p=&tpl=14&category=51&q=",
        "status": "ok" if items else "empty",
        "items": len(items),
        "mode": "miit_search_api",
        "category": REG,
        "latency_ms": int((datetime.now() - started).total_seconds() * 1000),
    })
    public["item_count"] = len(public["items"])
    public["version"] = "source-expanded-regulators-company"
    public["generated_at"] = datetime.now().replace(microsecond=0).isoformat()
    update_landscape(public)
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    update_dependents(public)
    print(json.dumps({"added_miit": len(items), "removed_low_value": removed, "item_count": public["item_count"], "sources": len(public["sources"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
