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
OUT_PATH = OUTPUT_DIR / "bailing-public-data.json"


SOURCES = [
    ("gov-policy-latest", "???????", "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json", "https://www.gov.cn/zhengce/zuixin/", "????", "gov_json", "central"),
    ("gov-news-important", "???????", "https://www.gov.cn/xinwen/yaowen/", None, "????", "html_list", "central"),
    ("ndrc-orders", "?????????", "https://www.ndrc.gov.cn/xxgk/zcfb/fzggwl/", None, "????", "html_list", "ministry"),
    ("ndrc-notices", "???????", "https://www.ndrc.gov.cn/xxgk/zcfb/tz/", None, "????", "html_list", "ministry"),
    ("ndrc-announcements", "???????", "https://www.ndrc.gov.cn/xxgk/zcfb/gg/", None, "????", "html_list", "ministry"),
    ("ndrc-news", "?????????", "https://www.ndrc.gov.cn/xwdt/xwfb/", None, "????", "html_list", "ministry"),
    ("stats-release", "?????????", "https://www.stats.gov.cn/sj/zxfb/", None, "????", "html_list", "central_data"),
    ("stats-news", "?????????", "https://www.stats.gov.cn/xw/tjxw/", None, "????", "html_list", "central_data"),
    ("mof-news", "???????", "https://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/", None, "????", "html_list", "ministry"),
    ("mof-policy", "???????", "https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/", None, "????", "html_list", "ministry"),
    ("pbc-news", "????????", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html", None, "????", "anchor_context", "ministry"),
    ("pbc-policy", "????????", "https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/index.html", None, "????", "anchor_context", "ministry"),
    ("csrc-news", "?????", "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml", None, "????", "html_list", "ministry"),
    ("csrc-press", "???????", "http://www.csrc.gov.cn/csrc/c100029/common_list.shtml", None, "????", "html_list", "ministry"),
    ("mofcom-news", "???????", "https://www.mofcom.gov.cn/xwfb/", None, "????", "html_list", "ministry"),
    ("moa-news", "???????", "http://www.moa.gov.cn/xw/zwdt/", None, "????", "html_list", "ministry"),
    ("mnr-news", "???????", "https://www.mnr.gov.cn/dt/ywbb/", None, "????", "html_list", "ministry"),
    ("mee-news", "???????", "https://www.mee.gov.cn/ywdt/", None, "????", "html_list", "ministry"),
    ("beijing-policy", "?????????", "https://www.beijing.gov.cn/zhengce/zhengcefagui/", None, "????", "html_list", "local"),
    ("shanghai-policy", "?????????", "https://www.shanghai.gov.cn/nw12344/index.html", None, "????", "html_list", "local"),
    ("guangdong-policy", "?????????", "https://www.gd.gov.cn/zwgk/wjk/", None, "????", "html_list", "local"),
    ("shandong-policy", "?????????", "http://www.shandong.gov.cn/col/col107851/index.html", None, "????", "html_list", "local"),
    ("kr36-newsflash", "36???", "https://36kr.com/newsflashes", None, "????", "html_list", "media"),
]


CANDIDATE_SOURCES = [
    {"name": "?????????", "url": "https://www.gov.cn/zhengce/zhengcewenjianku/", "status": "needs_adapter", "reason": "???????????????????"},
    {"name": "???????", "url": "https://www.mofcom.gov.cn/zwgk/zcfb/", "status": "needs_adapter", "reason": "???????????????????????"},
    {"name": "???????", "url": "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html", "status": "needs_adapter", "reason": "?????????????????????"},
    {"name": "????????", "url": "https://www.nfra.gov.cn/cn/view/pages/index/index.html", "status": "needs_review", "reason": "????????????????"},
    {"name": "????????", "url": "https://www.samr.gov.cn/xw/zj/", "status": "needs_adapter", "reason": "???????????? HTML ????"},
    {"name": "????????", "url": "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/", "status": "needs_review", "reason": "??????????"},
    {"name": "?????/??", "url": "http://www.sasac.gov.cn/n2588035/n2588320/index.html", "status": "needs_adapter", "reason": "?????????????????"},
    {"name": "??????", "url": "http://www.customs.gov.cn/customs/302249/302266/302267/index.html", "status": "blocked_or_needs_headers", "reason": "???????? 412????????????"},
    {"name": "???????", "url": "https://www.nea.gov.cn/xwzx/nyyw.htm", "status": "needs_adapter", "reason": "???????????????????"},
    {"name": "?????????", "url": "https://www.zj.gov.cn/col/col1229019364/index.html", "status": "needs_adapter", "reason": "????????????????"},
    {"name": "?????????", "url": "https://www.jiangsu.gov.cn/col/col64797/index.html", "status": "needs_review", "reason": "??????????????"},
    {"name": "?????????", "url": "https://www.sc.gov.cn/10462/zfwjts/zfwj.shtml", "status": "error", "reason": "?????????????"},
    {"name": "?????????", "url": "https://www.hubei.gov.cn/zfwj/", "status": "blocked_or_needs_headers", "reason": "?????????????????????"},
    {"name": "?????????", "url": "https://www.ah.gov.cn/public/column/1681?type=4&action=list", "status": "error", "reason": "?????????????"},
    {"name": "?????????", "url": "https://www.sse.com.cn/disclosure/listedinfo/announcement/", "status": "needs_adapter", "reason": "???????????????????"},
    {"name": "?????????", "url": "https://www.szse.cn/disclosure/listed/notice/index.html", "status": "needs_adapter", "reason": "???????????????????"},
    {"name": "??????", "url": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search", "status": "needs_adapter", "reason": "?????????????????"},
    {"name": "????????", "url": "manual://wechat-official-accounts", "status": "manual_or_authorized", "reason": "????????????????????????????"},
]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._stack = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if tag == "a":
            self._current = {
                "href": attrs.get("href", ""),
                "title": attrs.get("title", ""),
                "text": [],
                "parent": list(self._stack[-6:]),
            }

    def handle_endtag(self, tag):
        if tag == "a" and self._current:
            title = clean_title(self._current["title"] or "".join(self._current["text"]))
            href = self._current["href"]
            if href and title and not skip_href(href):
                self.links.append({"title": title, "href": href})
            self._current = None
        if self._stack:
            self._stack.pop()

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"].append(data)


class ListParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self._li_depth = 0
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li":
            self._li_depth += 1
            if self._li_depth == 1:
                self._current = {"href": "", "title": "", "text": []}
        elif self._li_depth and tag == "a" and self._current is not None:
            self._current["href"] = self._current["href"] or attrs.get("href", "")
            self._current["title"] = self._current["title"] or attrs.get("title", "")

    def handle_endtag(self, tag):
        if tag == "li" and self._li_depth:
            if self._li_depth == 1 and self._current:
                text = clean_text(" ".join(self._current["text"]))
                title = clean_title(self._current["title"] or text)
                date = extract_date(text)
                href = self._current["href"]
                if href and title and date and not skip_href(href):
                    self.items.append({"title": title, "href": href, "date": date})
            self._li_depth -= 1

    def handle_data(self, data):
        if self._li_depth and self._current is not None:
            self._current["text"].append(data)


def source_dict(row):
    sid, name, url, home_url, category, mode, authority = row
    return {"id": sid, "name": name, "url": url, "home_url": home_url, "category": category, "mode": mode, "authority": authority}


def fetch_text(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 BailingSourceCollector/1.0",
        "Accept": "text/html,application/json,application/xhtml+xml",
        "Referer": "https://www.gov.cn/",
    })
    with urlopen(req, timeout=20) as resp:
        raw = resp.read()
        content_type = resp.headers.get("content-type", "")
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    encodings = [match.group(1)] if match else []
    encodings += ["utf-8-sig", "utf-8", "gb18030"]
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def clean_text(value):
    value = unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def clean_title(value):
    value = clean_text(value)
    value = re.sub(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?", "", value)
    value = re.sub(r"\[\d{4}-\d{2}-\d{2}\]", "", value)
    return clean_text(value).strip("-|· ")


def extract_date(value):
    value = clean_text(value)
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", value)
    if not match:
        return ""
    y, m, d = match.groups()
    return f"{y}-{int(m):02d}-{int(d):02d}"


def skip_href(href):
    href = (href or "").lower()
    return href.startswith(("javascript:", "mailto:", "#")) or href.endswith((".css", ".js"))


def collect_gov_json(source, limit):
    rows = json.loads(fetch_text(source["url"]))
    items = []
    for row in rows:
        title = clean_text(row.get("TITLE") or row.get("title"))
        url = clean_text(row.get("URL") or row.get("url"))
        date = extract_date(row.get("DOCRELPUBTIME", "") or row.get("PUB_TIME", ""))
        if title and url and date:
            items.append(build_item(source, title, url, date, len(items), "public_json"))
        if len(items) >= limit:
            break
    return items


def collect_html_list(source, limit):
    html = fetch_text(source["url"])
    parser = ListParser()
    parser.feed(html)
    rows = parser.items
    if len(rows) < 3:
        return collect_anchor_context_from_html(source, html, limit)
    return rows_to_items(source, rows, limit, "public_html_list")


def collect_anchor_context(source, limit):
    return collect_anchor_context_from_html(source, fetch_text(source["url"]), limit)


def collect_anchor_context_from_html(source, html, limit):
    parser = LinkParser()
    parser.feed(html)
    rows = []
    seen = set()
    for link in parser.links:
        title = link["title"]
        href = link["href"]
        if title in seen or len(title) < 6:
            continue
        idx = html.find(href)
        context = html[max(0, idx - 500): idx + 1000] if idx >= 0 else title
        date = extract_date(context)
        if not date:
            continue
        seen.add(title)
        rows.append({"title": title, "href": href, "date": date})
        if len(rows) >= limit:
            break
    return rows_to_items(source, rows, limit, "public_anchor_context")


def rows_to_items(source, rows, limit, ingestion):
    items, seen = [], set()
    for row in rows:
        title = clean_title(row["title"])
        if title in seen:
            continue
        seen.add(title)
        url = urljoin(source["url"], row["href"])
        items.append(build_item(source, title, url, row["date"], len(items), ingestion))
        if len(items) >= limit:
            break
    return items


def build_item(source, title, url, date, index, ingestion):
    return {
        "id": f"{source['id']}-{index + 1}",
        "source_id": source["id"],
        "source_name": source["name"],
        "category": source["category"],
        "authority": source["authority"],
        "title": title,
        "url": url,
        "published_at": date,
        "tags": infer_tags(title, source["category"]),
        "scene": infer_scene(title, source["category"]),
        "consulting_value": infer_value(title, source["category"]),
        "public_value": infer_public_value(title, source["category"]),
        "ingestion": ingestion,
        "score": score_item(source["category"], index),
    }


def score_item(category, index):
    base = {"国家政策": 96, "宏观数据": 90, "财政金融": 88, "外贸外资": 86}.get(category, 82)
    return max(base - index * 2, 60)


def infer_tags(title, category):
    tags = [category]
    rules = [
        ("十五五", "十五五"), ("规划", "规划"), ("投资", "投资"), ("基金", "资本市场"),
        ("财政", "财政"), ("金融", "金融"), ("货币", "金融"), ("利率", "金融"),
        ("工业", "工业"), ("制造", "制造业"), ("价格", "价格"), ("居民消费", "消费"),
        ("生产者", "工业价格"), ("采购经理", "PMI"), ("PMI", "PMI"), ("利润", "经营分析"),
        ("固定资产", "固定资产投资"), ("人口", "人口"), ("能源", "能源"), ("电力", "能源"),
        ("民营", "民营经济"), ("外资", "外资"), ("外贸", "外贸"), ("商务", "商务"),
        ("监管", "监管"), ("风险", "风险"), ("国资", "国企"), ("证券", "资本市场"),
        ("上市", "上市公司"), ("海关", "外贸"), ("消费", "消费"),
    ]
    for keyword, tag in rules:
        if keyword in title and tag not in tags:
            tags.append(tag)
    if len(tags) == 1:
        tags.append("政策跟踪" if category == "国家政策" else "宏观观察")
    return tags[:5]


def infer_scene(title, category):
    if category == "国家政策":
        if any(w in title for w in ["投资", "基金", "外资", "民营", "目录"]):
            return "产业规划 / 招商策略 / 企业战略"
        if any(w in title for w in ["能源", "电力", "应急", "安全"]):
            return "公共治理 / 能源与基础设施咨询"
        return "政策研究 / 客户简报 / 项目背景"
    if category == "财政金融":
        return "投融资判断 / 财政政策 / 金融环境研判"
    if category == "外贸外资":
        return "外贸外资 / 企业出海 / 招商策略"
    if any(w in title for w in ["价格", "CPI", "PPI", "生产者", "居民消费"]):
        return "经营分析 / 市场测算"
    if any(w in title for w in ["采购经理", "PMI", "工业", "利润"]):
        return "行业景气 / 经营诊断"
    return "宏观背景 / 行业月报"


def infer_value(title, category):
    if category == "国家政策":
        return "适合放入政策雷达、客户周报和项目前期背景研究，用于判断监管方向、产业机会和项目约束。"
    if category == "财政金融":
        return "适合用于判断财政金融环境、融资条件、市场预期和客户战略窗口。"
    if category == "外贸外资":
        return "适合用于外贸企业、跨境业务、招商引资和企业出海相关项目背景研究。"
    if any(w in title for w in ["价格", "CPI", "PPI", "生产者", "居民消费"]):
        return "适合用于价格趋势、需求变化和行业经营压力判断。"
    return "适合用于宏观背景、行业月报和客户简报，帮助顾问快速建立事实底座。"


def infer_public_value(title, category):
    if category == "国家政策":
        return "帮助企业主和行业从业者及时了解国家政策方向。"
    if category == "财政金融":
        return "帮助普通用户理解财政金融动态对经营和投资环境的影响。"
    if category == "外贸外资":
        return "帮助外贸、跨境和出海相关用户了解商务政策变化。"
    return "帮助关注经济和产业的人快速了解重要数据变化。"


def collect_source(source, limit=10):
    if source["mode"] == "gov_json":
        return collect_gov_json(source, limit)
    if source["mode"] == "anchor_context":
        return collect_anchor_context(source, limit)
    return collect_html_list(source, limit)


def main():
    all_items, source_status = [], []
    for row in SOURCES:
        source = source_dict(row)
        started = datetime.now()
        try:
            items = collect_source(source)
            all_items.extend(items)
            source_status.append({
                "source_id": source["id"],
                "name": source["name"],
                "url": source.get("home_url") or source["url"],
                "status": "ok" if items else "empty",
                "items": len(items),
                "mode": source["mode"],
                "category": source["category"],
                "latency_ms": int((datetime.now() - started).total_seconds() * 1000),
            })
        except Exception as exc:
            source_status.append({
                "source_id": source["id"],
                "name": source["name"],
                "url": source.get("home_url") or source["url"],
                "status": "error",
                "items": 0,
                "mode": source["mode"],
                "category": source["category"],
                "error": str(exc),
            })
    all_items.sort(key=lambda item: item["published_at"], reverse=True)
    payload = {
        "product": "百灵",
        "professional_layer": "知更",
        "version": "source-expanded-1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "item_count": len(all_items),
        "sources": source_status,
        "candidate_sources": CANDIDATE_SOURCES,
        "items": all_items,
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with {len(all_items)} items")
    for status in source_status:
        print(f"{status['name']}: {status['status']} ({status['items']} items)")


if __name__ == "__main__":
    main()
