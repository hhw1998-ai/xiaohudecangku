import json
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"


SOURCES = [
    {
        "id": "ndrc-orders",
        "name": "国家发改委政策发布",
        "url": "https://www.ndrc.gov.cn/xxgk/zcfb/fzggwl/",
        "type": "政策",
        "selector_hint": "ul.u-list li",
    },
    {
        "id": "stats-release",
        "name": "国家统计局数据发布",
        "url": "https://www.stats.gov.cn/sj/zxfb/",
        "type": "行业",
        "selector_hint": ".list-content li",
    },
]


class ListItemParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self._li_depth = 0
        self._current = None
        self._in_a = False
        self._in_span = False
        self._text_parts = []
        self._span_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li":
            self._li_depth += 1
            if self._li_depth == 1:
                self._current = {"href": "", "title": "", "date": ""}
                self._text_parts = []
                self._span_parts = []
        elif self._li_depth and tag == "a" and self._current is not None:
            href = attrs.get("href", "")
            title = attrs.get("title", "")
            if href and not self._current["href"]:
                self._current["href"] = href
            if title and not self._current["title"]:
                self._current["title"] = title
            self._in_a = True
        elif self._li_depth and tag == "span":
            self._in_span = True

    def handle_endtag(self, tag):
        if tag == "a":
            self._in_a = False
        elif tag == "span":
            self._in_span = False
        elif tag == "li" and self._li_depth:
            if self._li_depth == 1 and self._current:
                title = clean_text(self._current["title"] or "".join(self._text_parts))
                date = clean_text(self._current["date"] or "".join(self._span_parts))
                href = self._current["href"]
                if title and href and looks_like_date(date):
                    self.items.append({"title": title, "href": href, "date": normalize_date(date)})
            self._li_depth -= 1

    def handle_data(self, data):
        if self._li_depth and self._in_a:
            self._text_parts.append(data)
        if self._li_depth and self._in_span:
            self._span_parts.append(data)
            if self._current is not None and looks_like_date(data):
                self._current["date"] = data


def fetch_text(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 ConsultingRadarPrototype/0.1",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=20) as resp:
        raw = resp.read()
        content_type = resp.headers.get("content-type", "")
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    try:
        return raw.decode(charset)
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def clean_text(value):
    value = unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def looks_like_date(value):
    value = clean_text(value)
    return bool(re.search(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}", value))


def normalize_date(value):
    value = clean_text(value).replace("/", "-")
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", value)
    if not match:
        return value
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def infer_tags(title, source_type):
    tags = [source_type]
    rules = [
        ("制造", "制造业"),
        ("工业", "工业"),
        ("投资", "投资"),
        ("外商", "外资"),
        ("电力", "能源"),
        ("天然气", "能源"),
        ("油气", "能源"),
        ("价格", "价格"),
        ("居民消费", "消费"),
        ("生产者", "工业价格"),
        ("采购经理", "PMI"),
        ("利润", "经营分析"),
        ("固定资产", "固定资产投资"),
        ("人口", "人口"),
    ]
    for keyword, tag in rules:
        if keyword in title and tag not in tags:
            tags.append(tag)
    if len(tags) == 1:
        tags.append("宏观观察" if source_type == "行业" else "政策跟踪")
    return tags[:4]


def infer_consulting_value(title, source_type):
    if source_type == "政策":
        if any(word in title for word in ["投资", "外商", "产业目录"]):
            return "适合用于产业机会识别、招商策略和区域政策背景页。"
        if any(word in title for word in ["电力", "天然气", "油气", "能源"]):
            return "适合用于能源、公用事业和基础设施客户的政策影响分析。"
        return "适合放入政策雷达、客户周报和项目背景研究。"
    if any(word in title for word in ["价格", "PPI", "CPI", "生产者", "居民消费"]):
        return "适合用于价格趋势、需求变化和行业经营压力判断。"
    if any(word in title for word in ["采购经理", "PMI", "工业", "利润"]):
        return "适合用于行业景气度、经营诊断和市场进入判断。"
    return "适合用于宏观背景、行业月报和客户简报。"


def infer_scene(title, source_type):
    if source_type == "政策":
        if any(word in title for word in ["投资", "外商"]):
            return "产业规划 / 招商策略"
        if any(word in title for word in ["电力", "天然气", "油气"]):
            return "能源与基础设施咨询"
        return "政策研究 / 客户简报"
    if any(word in title for word in ["价格", "利润"]):
        return "经营分析 / 市场测算"
    return "行业监测 / 宏观背景"


def collect_source(source, limit=8):
    html = fetch_text(source["url"])
    parser = ListItemParser()
    parser.feed(html)
    results = []
    seen = set()
    for item in parser.items:
        title = item["title"]
        if title in seen:
            continue
        seen.add(title)
        url = urljoin(source["url"], item["href"])
        results.append(
            {
                "id": f"{source['id']}-{len(results)+1}",
                "source_id": source["id"],
                "source_name": source["name"],
                "category": source["type"],
                "title": title,
                "url": url,
                "published_at": item["date"],
                "tags": infer_tags(title, source["type"]),
                "consulting_scene": infer_scene(title, source["type"]),
                "consulting_value": infer_consulting_value(title, source["type"]),
                "ingestion": "public_html_list",
                "score": 90 - min(len(results) * 3, 24) if source["type"] == "政策" else 82 - min(len(results) * 2, 18),
            }
        )
        if len(results) >= limit:
            break
    return results


def main():
    all_items = []
    source_status = []
    for source in SOURCES:
        try:
            items = collect_source(source)
            all_items.extend(items)
            source_status.append(
                {
                    "source_id": source["id"],
                    "name": source["name"],
                    "url": source["url"],
                    "status": "ok",
                    "items": len(items),
                    "selector_hint": source["selector_hint"],
                }
            )
        except Exception as exc:
            source_status.append(
                {
                    "source_id": source["id"],
                    "name": source["name"],
                    "url": source["url"],
                    "status": "error",
                    "error": str(exc),
                    "items": 0,
                }
            )
    all_items.sort(key=lambda item: item["published_at"], reverse=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "item_count": len(all_items),
        "sources": source_status,
        "items": all_items,
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "consulting-radar-live-data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out} with {len(all_items)} items")
    for status in source_status:
        print(f"{status['name']}: {status['status']} ({status['items']} items)")


if __name__ == "__main__":
    main()
