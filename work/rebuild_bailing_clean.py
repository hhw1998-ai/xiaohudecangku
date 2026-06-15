import json
import re
from collections import Counter
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
APP_DIR = ROOT / "app"


def U(value):
    return value.encode("ascii").decode("unicode_escape")


C = {
    "product": U("\\u767e\\u7075"),
    "pro": U("\\u77e5\\u66f4"),
    "all": U("\\u5168\\u90e8"),
    "policy": U("\\u56fd\\u5bb6\\u653f\\u7b56"),
    "macro": U("\\u5b8f\\u89c2\\u6570\\u636e"),
    "finance": U("\\u8d22\\u653f\\u91d1\\u878d"),
    "trade": U("\\u5916\\u8d38\\u5916\\u8d44"),
    "industry": U("\\u4ea7\\u4e1a\\u76d1\\u7ba1"),
    "local": U("\\u5730\\u65b9\\u653f\\u7b56"),
    "media": U("\\u4ea7\\u4e1a\\u5a92\\u4f53"),
    "company": U("\\u516c\\u53f8\\u516c\\u544a"),
}


SOURCES = [
    ("gov-policy-latest", U("\\u56fd\\u52a1\\u9662\\u6700\\u65b0\\u653f\\u7b56"), "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json", "https://www.gov.cn/zhengce/zuixin/", C["policy"], "gov_json", "central"),
    ("gov-news-important", U("\\u4e2d\\u56fd\\u653f\\u5e9c\\u7f51\\u8981\\u95fb"), "https://www.gov.cn/xinwen/yaowen/", None, C["policy"], "html_list", "central"),
    ("ndrc-orders", U("\\u56fd\\u5bb6\\u53d1\\u6539\\u59d4\\u653f\\u7b56\\u53d1\\u5e03"), "https://www.ndrc.gov.cn/xxgk/zcfb/fzggwl/", None, C["policy"], "html_list", "ministry"),
    ("ndrc-notices", U("\\u56fd\\u5bb6\\u53d1\\u6539\\u59d4\\u901a\\u77e5"), "https://www.ndrc.gov.cn/xxgk/zcfb/tz/", None, C["policy"], "html_list", "ministry"),
    ("ndrc-announcements", U("\\u56fd\\u5bb6\\u53d1\\u6539\\u59d4\\u516c\\u544a"), "https://www.ndrc.gov.cn/xxgk/zcfb/gg/", None, C["policy"], "html_list", "ministry"),
    ("ndrc-news", U("\\u56fd\\u5bb6\\u53d1\\u6539\\u59d4\\u65b0\\u95fb\\u53d1\\u5e03"), "https://www.ndrc.gov.cn/xwdt/xwfb/", None, C["policy"], "html_list", "ministry"),
    ("stats-release", U("\\u56fd\\u5bb6\\u7edf\\u8ba1\\u5c40\\u6570\\u636e\\u53d1\\u5e03"), "https://www.stats.gov.cn/sj/zxfb/", None, C["macro"], "html_list", "central_data"),
    ("stats-news", U("\\u56fd\\u5bb6\\u7edf\\u8ba1\\u5c40\\u7edf\\u8ba1\\u65b0\\u95fb"), "https://www.stats.gov.cn/xw/tjxw/", None, C["macro"], "html_list", "central_data"),
    ("mof-news", U("\\u8d22\\u653f\\u90e8\\u8d22\\u653f\\u65b0\\u95fb"), "https://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/", None, C["finance"], "html_list", "ministry"),
    ("mof-policy", U("\\u8d22\\u653f\\u90e8\\u653f\\u7b56\\u53d1\\u5e03"), "https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/", None, C["finance"], "html_list", "ministry"),
    ("pbc-news", U("\\u4eba\\u6c11\\u94f6\\u884c\\u5de5\\u4f5c\\u52a8\\u6001"), "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html", None, C["finance"], "anchor_context", "ministry"),
    ("pbc-policy", U("\\u4eba\\u6c11\\u94f6\\u884c\\u8d27\\u5e01\\u653f\\u7b56"), "https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/index.html", None, C["finance"], "anchor_context", "ministry"),
    ("csrc-news", U("\\u8bc1\\u76d1\\u4f1a\\u8981\\u95fb"), "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml", None, C["finance"], "html_list", "ministry"),
    ("csrc-press", U("\\u8bc1\\u76d1\\u4f1a\\u65b0\\u95fb\\u53d1\\u5e03"), "http://www.csrc.gov.cn/csrc/c100029/common_list.shtml", None, C["finance"], "html_list", "ministry"),
    ("mofcom-news", U("\\u5546\\u52a1\\u90e8\\u65b0\\u95fb\\u53d1\\u5e03"), "https://www.mofcom.gov.cn/xwfb/", None, C["trade"], "html_list", "ministry"),
    ("moa-news", U("\\u519c\\u4e1a\\u519c\\u6751\\u90e8\\u65b0\\u95fb"), "http://www.moa.gov.cn/xw/zwdt/", None, U("\\u519c\\u4e1a\\u519c\\u6751"), "html_list", "ministry"),
    ("mnr-news", U("\\u81ea\\u7136\\u8d44\\u6e90\\u90e8\\u65b0\\u95fb"), "https://www.mnr.gov.cn/dt/ywbb/", None, U("\\u8d44\\u6e90\\u73af\\u5883"), "html_list", "ministry"),
    ("mee-news", U("\\u751f\\u6001\\u73af\\u5883\\u90e8\\u65b0\\u95fb"), "https://www.mee.gov.cn/ywdt/", None, U("\\u8d44\\u6e90\\u73af\\u5883"), "html_list", "ministry"),
    ("beijing-policy", U("\\u5317\\u4eac\\u5e02\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "https://www.beijing.gov.cn/zhengce/zhengcefagui/", None, C["local"], "html_list", "local"),
    ("shanghai-policy", U("\\u4e0a\\u6d77\\u5e02\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "https://www.shanghai.gov.cn/nw12344/index.html", None, C["local"], "html_list", "local"),
    ("guangdong-policy", U("\\u5e7f\\u4e1c\\u7701\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "https://www.gd.gov.cn/zwgk/wjk/", None, C["local"], "html_list", "local"),
    ("shandong-policy", U("\\u5c71\\u4e1c\\u7701\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "http://www.shandong.gov.cn/col/col107851/index.html", None, C["local"], "html_list", "local"),
    ("kr36-newsflash", U("36\\u6c2a\\u5feb\\u8baf"), "https://36kr.com/newsflashes", None, C["media"], "html_list", "media"),
]


CANDIDATE_SOURCES = [
    {"name": U("\\u4e2d\\u56fd\\u653f\\u5e9c\\u7f51\\u653f\\u7b56\\u6587\\u4ef6"), "url": "https://www.gov.cn/zhengce/zhengcewenjianku/", "status": "needs_adapter", "reason": U("\\u9875\\u9762\\u7ed3\\u6784\\u66f4\\u52a8\\uff0c\\u9700\\u5355\\u72ec\\u9002\\u914d\\u5217\\u8868\\u63a5\\u53e3")},
    {"name": U("\\u5de5\\u4fe1\\u90e8\\u6587\\u4ef6\\u53d1\\u5e03"), "url": "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html", "status": "needs_adapter", "reason": U("\\u52a8\\u6001\\u5217\\u8868\\u9700\\u8981\\u8ffd\\u8e2a\\u63a5\\u53e3")},
    {"name": U("\\u91d1\\u878d\\u76d1\\u7ba1\\u603b\\u5c40"), "url": "https://www.nfra.gov.cn/cn/view/pages/index/index.html", "status": "needs_review", "reason": U("\\u9700\\u786e\\u8ba4\\u65b0\\u95fb\\u548c\\u653f\\u7b56\\u5165\\u53e3")},
    {"name": U("\\u5e02\\u573a\\u76d1\\u7ba1\\u603b\\u5c40"), "url": "https://www.samr.gov.cn/xw/zj/", "status": "needs_adapter", "reason": U("\\u7f51\\u9875\\u5217\\u8868\\u53ef\\u6293\\uff0c\\u4f46\\u9700\\u8865\\u5f3a\\u65e5\\u671f\\u89e3\\u6790")},
    {"name": U("\\u56fd\\u8d44\\u59d4\\u653f\\u7b56\\u4e0e\\u65b0\\u95fb"), "url": "http://www.sasac.gov.cn/n2588035/n2588320/index.html", "status": "needs_adapter", "reason": U("\\u9002\\u5408\\u540e\\u7eed\\u505a\\u56fd\\u4f01\\u4e0e\\u592e\\u4f01\\u7a7a\\u95f4")},
    {"name": U("\\u6d77\\u5173\\u603b\\u7f72"), "url": "http://www.customs.gov.cn/customs/302249/302266/302267/index.html", "status": "blocked_or_needs_headers", "reason": U("\\u90e8\\u5206\\u8bf7\\u6c42\\u8fd4\\u56de 412\\uff0c\\u9700\\u8865\\u8bf7\\u6c42\\u5934\\u6216\\u4ee3\\u7406")},
    {"name": U("\\u56fd\\u5bb6\\u80fd\\u6e90\\u5c40"), "url": "https://www.nea.gov.cn/xwzx/nyyw.htm", "status": "needs_adapter", "reason": U("\\u80fd\\u6e90\\u57fa\\u5efa\\u7a7a\\u95f4\\u7684\\u91cd\\u8981\\u8865\\u5145\\u6e90")},
    {"name": U("\\u6d59\\u6c5f\\u7701\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "url": "https://www.zj.gov.cn/col/col1229019364/index.html", "status": "needs_adapter", "reason": U("\\u5730\\u65b9\\u653f\\u7b56\\u5e93\\u7b2c\\u4e8c\\u6279")},
    {"name": U("\\u6c5f\\u82cf\\u7701\\u653f\\u5e9c\\u653f\\u7b56\\u6587\\u4ef6"), "url": "https://www.jiangsu.gov.cn/col/col64797/index.html", "status": "needs_review", "reason": U("\\u9700\\u68c0\\u67e5\\u5217\\u8868\\u9875\\u65e5\\u671f\\u89c4\\u5219")},
    {"name": U("\\u4e0a\\u4ea4\\u6240\\u516c\\u544a"), "url": "https://www.sse.com.cn/disclosure/listedinfo/announcement/", "status": "needs_adapter", "reason": U("\\u9700\\u63a5\\u5165\\u52a8\\u6001 API\\uff0c\\u7528\\u4e8e\\u4e0a\\u5e02\\u516c\\u53f8\\u5e74\\u62a5\\u548c\\u516c\\u544a")},
    {"name": U("\\u6df1\\u4ea4\\u6240\\u516c\\u544a"), "url": "https://www.szse.cn/disclosure/listed/notice/index.html", "status": "needs_adapter", "reason": U("\\u9700\\u63a5\\u5165\\u52a8\\u6001 API\\uff0c\\u7528\\u4e8e\\u4e0a\\u5e02\\u516c\\u53f8\\u5e74\\u62a5\\u548c\\u516c\\u544a")},
    {"name": U("\\u5de8\\u6f6e\\u8d44\\u8baf"), "url": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search", "status": "needs_adapter", "reason": U("\\u516c\\u544a\\u641c\\u7d22\\u63a5\\u53e3\\u9700\\u5355\\u72ec\\u5c01\\u88c5")},
    {"name": U("\\u5fae\\u4fe1\\u516c\\u4f17\\u53f7"), "url": "manual://wechat-official-accounts", "status": "manual_or_authorized", "reason": U("\\u516c\\u4f17\\u53f7\\u9700\\u6388\\u6743\\u6216\\u7528\\u5408\\u89c4\\u8f6c\\u8f7d\\u6765\\u6e90\\u5904\\u7406")},
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
            self._current = {"href": attrs.get("href", ""), "title": attrs.get("title", ""), "text": []}

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
        "User-Agent": "Mozilla/5.0 BailingSourceCollector/2.0",
        "Accept": "text/html,application/json,application/xhtml+xml",
        "Referer": "https://www.gov.cn/",
    })
    with urlopen(req, timeout=22) as resp:
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
    value = re.sub("20\\d{2}[-/.\\u5e74]\\d{1,2}[-/.\\u6708]\\d{1,2}\\u65e5?", "", value)
    value = re.sub(r"\[\d{4}-\d{2}-\d{2}\]", "", value)
    value = clean_text(value).strip("-| ")
    return value[:180]


def extract_date(value):
    value = clean_text(value)
    match = re.search("(20\\d{2})[-/.\\u5e74](\\d{1,2})[-/.\\u6708](\\d{1,2})\\u65e5?", value)
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
        context = html[max(0, idx - 600): idx + 1200] if idx >= 0 else title
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


def score_item(category, index):
    base = {C["policy"]: 96, C["macro"]: 90, C["finance"]: 88, C["trade"]: 86, C["local"]: 84}.get(category, 82)
    return max(base - index * 2, 60)


def infer_tags(title, category):
    rules = [
        (U("\\u5341\\u4e94\\u4e94"), U("\\u5341\\u4e94\\u4e94")), (U("\\u89c4\\u5212"), U("\\u89c4\\u5212")),
        (U("\\u6295\\u8d44"), U("\\u6295\\u8d44")), (U("\\u57fa\\u91d1"), U("\\u8d44\\u672c\\u5e02\\u573a")),
        (U("\\u8d22\\u653f"), U("\\u8d22\\u653f")), (U("\\u91d1\\u878d"), U("\\u91d1\\u878d")),
        (U("\\u8d27\\u5e01"), U("\\u91d1\\u878d")), (U("\\u5229\\u7387"), U("\\u91d1\\u878d")),
        (U("\\u5de5\\u4e1a"), U("\\u5de5\\u4e1a")), (U("\\u5236\\u9020"), U("\\u5236\\u9020\\u4e1a")),
        (U("\\u4ef7\\u683c"), U("\\u4ef7\\u683c")), (U("\\u5c45\\u6c11\\u6d88\\u8d39"), U("\\u6d88\\u8d39")),
        (U("\\u751f\\u4ea7\\u8005"), U("\\u5de5\\u4e1a\\u4ef7\\u683c")), (U("\\u91c7\\u8d2d\\u7ecf\\u7406"), "PMI"),
        ("PMI", "PMI"), (U("\\u5229\\u6da6"), U("\\u7ecf\\u8425\\u5206\\u6790")),
        (U("\\u56fa\\u5b9a\\u8d44\\u4ea7"), U("\\u56fa\\u5b9a\\u8d44\\u4ea7\\u6295\\u8d44")),
        (U("\\u4eba\\u53e3"), U("\\u4eba\\u53e3")), (U("\\u80fd\\u6e90"), U("\\u80fd\\u6e90")),
        (U("\\u7535\\u529b"), U("\\u80fd\\u6e90")), (U("\\u6c11\\u8425"), U("\\u6c11\\u8425\\u7ecf\\u6d4e")),
        (U("\\u5916\\u8d44"), U("\\u5916\\u8d44")), (U("\\u5916\\u8d38"), U("\\u5916\\u8d38")),
        (U("\\u5546\\u52a1"), U("\\u5546\\u52a1")), (U("\\u76d1\\u7ba1"), U("\\u76d1\\u7ba1")),
        (U("\\u98ce\\u9669"), U("\\u98ce\\u9669")), (U("\\u8bc1\\u5238"), U("\\u8d44\\u672c\\u5e02\\u573a")),
    ]
    tags = [category]
    for keyword, tag in rules:
        if keyword in title and tag not in tags:
            tags.append(tag)
    if len(tags) == 1:
        tags.append(U("\\u653f\\u7b56\\u8ddf\\u8e2a") if category == C["policy"] else U("\\u5b8f\\u89c2\\u89c2\\u5bdf"))
    return tags[:5]


def infer_scene(title, category):
    if category in {C["policy"], C["local"]}:
        if any(w in title for w in [U("\\u6295\\u8d44"), U("\\u57fa\\u91d1"), U("\\u5916\\u8d44"), U("\\u6c11\\u8425"), U("\\u76ee\\u5f55")]):
            return U("\\u4ea7\\u4e1a\\u89c4\\u5212 / \\u62db\\u5546\\u7b56\\u7565 / \\u4f01\\u4e1a\\u6218\\u7565")
        if any(w in title for w in [U("\\u80fd\\u6e90"), U("\\u7535\\u529b"), U("\\u5e94\\u6025"), U("\\u5b89\\u5168")]):
            return U("\\u516c\\u5171\\u6cbb\\u7406 / \\u80fd\\u6e90\\u4e0e\\u57fa\\u7840\\u8bbe\\u65bd\\u54a8\\u8be2")
        return U("\\u653f\\u7b56\\u7814\\u7a76 / \\u5ba2\\u6237\\u7b80\\u62a5 / \\u9879\\u76ee\\u80cc\\u666f")
    if category == C["finance"]:
        return U("\\u6295\\u878d\\u8d44\\u5224\\u65ad / \\u8d22\\u653f\\u653f\\u7b56 / \\u91d1\\u878d\\u73af\\u5883\\u7814\\u5224")
    if category == C["trade"]:
        return U("\\u5916\\u8d38\\u5916\\u8d44 / \\u4f01\\u4e1a\\u51fa\\u6d77 / \\u62db\\u5546\\u7b56\\u7565")
    if any(w in title for w in [U("\\u4ef7\\u683c"), "CPI", "PPI", U("\\u751f\\u4ea7\\u8005"), U("\\u5c45\\u6c11\\u6d88\\u8d39")]):
        return U("\\u7ecf\\u8425\\u5206\\u6790 / \\u5e02\\u573a\\u6d4b\\u7b97")
    if any(w in title for w in [U("\\u91c7\\u8d2d\\u7ecf\\u7406"), "PMI", U("\\u5de5\\u4e1a"), U("\\u5229\\u6da6")]):
        return U("\\u884c\\u4e1a\\u666f\\u6c14 / \\u7ecf\\u8425\\u8bca\\u65ad")
    return U("\\u5b8f\\u89c2\\u80cc\\u666f / \\u884c\\u4e1a\\u6708\\u62a5")


def infer_value(title, category):
    if category in {C["policy"], C["local"]}:
        return U("\\u9002\\u5408\\u653e\\u5165\\u653f\\u7b56\\u96f7\\u8fbe\\u3001\\u5ba2\\u6237\\u5468\\u62a5\\u548c\\u9879\\u76ee\\u524d\\u671f\\u80cc\\u666f\\u7814\\u7a76\\uff0c\\u7528\\u4e8e\\u5224\\u65ad\\u76d1\\u7ba1\\u65b9\\u5411\\u3001\\u4ea7\\u4e1a\\u673a\\u4f1a\\u548c\\u9879\\u76ee\\u7ea6\\u675f\\u3002").replace("雷达e", U("\\u96f7\\u8fbe")).replace("雷达e", U("\\u96f7\\u8fbe"))
    if category == C["finance"]:
        return U("\\u9002\\u5408\\u7528\\u4e8e\\u5224\\u65ad\\u8d22\\u653f\\u91d1\\u878d\\u73af\\u5883\\u3001\\u878d\\u8d44\\u6761\\u4ef6\\u3001\\u5e02\\u573a\\u9884\\u671f\\u548c\\u5ba2\\u6237\\u6218\\u7565\\u7a97\\u53e3\\u3002")
    if category == C["trade"]:
        return U("\\u9002\\u5408\\u7528\\u4e8e\\u5916\\u8d38\\u4f01\\u4e1a\\u3001\\u8de8\\u5883\\u4e1a\\u52a1\\u3001\\u62db\\u5546\\u5f15\\u8d44\\u548c\\u4f01\\u4e1a\\u51fa\\u6d77\\u9879\\u76ee\\u80cc\\u666f\\u7814\\u7a76\\u3002")
    if any(w in title for w in [U("\\u4ef7\\u683c"), "CPI", "PPI", U("\\u751f\\u4ea7\\u8005"), U("\\u5c45\\u6c11\\u6d88\\u8d39")]):
        return U("\\u9002\\u5408\\u7528\\u4e8e\\u4ef7\\u683c\\u8d8b\\u52bf\\u3001\\u9700\\u6c42\\u53d8\\u5316\\u548c\\u884c\\u4e1a\\u7ecf\\u8425\\u538b\\u529b\\u5224\\u65ad\\u3002")
    return U("\\u9002\\u5408\\u7528\\u4e8e\\u5b8f\\u89c2\\u80cc\\u666f\\u3001\\u884c\\u4e1a\\u6708\\u62a5\\u548c\\u5ba2\\u6237\\u7b80\\u62a5\\uff0c\\u5e2e\\u52a9\\u987e\\u95ee\\u5feb\\u901f\\u5efa\\u7acb\\u4e8b\\u5b9e\\u5e95\\u5ea7\\u3002")


def infer_public_value(title, category):
    if category in {C["policy"], C["local"]}:
        return U("\\u5e2e\\u52a9\\u4f01\\u4e1a\\u4e3b\\u548c\\u884c\\u4e1a\\u4ece\\u4e1a\\u8005\\u53ca\\u65f6\\u4e86\\u89e3\\u653f\\u7b56\\u65b9\\u5411\\u3002")
    if category == C["finance"]:
        return U("\\u5e2e\\u52a9\\u666e\\u901a\\u7528\\u6237\\u7406\\u89e3\\u8d22\\u653f\\u91d1\\u878d\\u52a8\\u6001\\u5bf9\\u7ecf\\u8425\\u548c\\u6295\\u8d44\\u73af\\u5883\\u7684\\u5f71\\u54cd\\u3002")
    return U("\\u5e2e\\u52a9\\u5173\\u6ce8\\u7ecf\\u6d4e\\u548c\\u4ea7\\u4e1a\\u7684\\u4eba\\u5feb\\u901f\\u4e86\\u89e3\\u91cd\\u8981\\u6570\\u636e\\u53d8\\u5316\\u3002")


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


def collect_source(source, limit=10):
    if source["mode"] == "gov_json":
        return collect_gov_json(source, limit)
    if source["mode"] == "anchor_context":
        return collect_anchor_context(source, limit)
    return collect_html_list(source, limit)


SPACES = [
    {"id": "consulting", "name": U("\\u7ba1\\u7406\\u54a8\\u8be2"), "short": U("\\u54a8\\u8be2"), "audience": U("\\u54a8\\u8be2\\u987e\\u95ee / \\u9879\\u76ee\\u7ecf\\u7406"), "keywords": [U("\\u89c4\\u5212"), U("\\u6295\\u8d44"), U("\\u76d1\\u7ba1"), U("\\u8d22\\u653f"), U("\\u5de5\\u4e1a"), U("\\u4ef7\\u683c"), "PMI", U("\\u98ce\\u9669"), U("\\u7ecf\\u8425"), U("\\u5341\\u4e94\\u4e94")], "signals": [U("\\u653f\\u7b56\\u7a97\\u53e3"), U("\\u5ba2\\u6237\\u7b80\\u62a5"), U("\\u9879\\u76ee\\u80cc\\u666f"), U("\\u7ecf\\u8425\\u8bca\\u65ad")], "locked_tools": [U("\\u5ba2\\u6237\\u6668\\u62a5"), U("PPT \\u7d20\\u6750\\u5361"), U("\\u5f71\\u54cd\\u77e9\\u9635")]},
    {"id": "manufacturing", "name": U("\\u5236\\u9020\\u4e1a"), "short": U("\\u5236\\u9020"), "audience": U("\\u5236\\u9020\\u4f01\\u4e1a / \\u4ea7\\u4e1a\\u56ed\\u533a"), "keywords": [U("\\u5236\\u9020"), U("\\u5de5\\u4e1a"), U("\\u751f\\u4ea7\\u8005"), "PMI", U("\\u4ef7\\u683c"), U("\\u7269\\u6d41"), U("\\u6280\\u672f\\u4e2d\\u5fc3")], "signals": [U("\\u666f\\u6c14\\u53d8\\u5316"), U("\\u6210\\u672c\\u538b\\u529b"), U("\\u4ea7\\u4e1a\\u653f\\u7b56"), U("\\u4f9b\\u5e94\\u94fe")], "locked_tools": [U("\\u4ea7\\u4e1a\\u94fe\\u8ffd\\u8e2a"), U("\\u7ade\\u54c1\\u52a8\\u5411"), U("\\u6210\\u672c\\u9884\\u8b66")]},
    {"id": "energy_infra", "name": U("\\u80fd\\u6e90\\u4e0e\\u57fa\\u7840\\u8bbe\\u65bd"), "short": U("\\u80fd\\u6e90"), "audience": U("\\u80fd\\u6e90\\u3001\\u516c\\u7528\\u4e8b\\u4e1a\\u3001\\u57fa\\u5efa\\u5ba2\\u6237"), "keywords": [U("\\u80fd\\u6e90"), U("\\u7535\\u529b"), U("\\u5929\\u7136\\u6c14"), U("\\u77f3\\u6cb9"), U("\\u57fa\\u7840\\u8bbe\\u65bd"), U("\\u5e94\\u6025"), U("\\u751f\\u6001\\u4fdd\\u62a4"), U("\\u6295\\u8d44")], "signals": [U("\\u9879\\u76ee\\u7ea6\\u675f"), U("\\u76d1\\u7ba1\\u53d8\\u5316"), U("\\u57fa\\u7840\\u8bbe\\u65bd\\u673a\\u4f1a"), U("\\u5b89\\u5168\\u97e7\\u6027")], "locked_tools": [U("\\u9879\\u76ee\\u673a\\u4f1a\\u5e93"), U("\\u533a\\u57df\\u653f\\u7b56\\u6bd4\\u5bf9"), U("\\u98ce\\u9669\\u6761\\u6b3e\\u6458\\u8981")]},
    {"id": "finance", "name": C["finance"], "short": U("\\u91d1\\u878d"), "audience": U("\\u6295\\u878d\\u8d44\\u3001\\u8d22\\u52a1\\u3001\\u91d1\\u878d\\u673a\\u6784"), "keywords": [U("\\u8d22\\u653f"), U("\\u91d1\\u878d"), U("\\u57fa\\u91d1"), U("\\u56fd\\u503a"), U("\\u8d27\\u5e01"), U("\\u5229\\u7387"), U("\\u878d\\u8d44"), U("\\u9884\\u7b97")], "signals": [U("\\u8d44\\u91d1\\u73af\\u5883"), U("\\u878d\\u8d44\\u7a97\\u53e3"), U("\\u76d1\\u7ba1\\u503e\\u5411"), U("\\u8d22\\u653f\\u8282\\u594f")], "locked_tools": [U("\\u878d\\u8d44\\u73af\\u5883\\u96f7\\u8fbe"), U("\\u653f\\u7b56\\u539f\\u6587\\u6458\\u8981"), U("\\u673a\\u6784\\u89c2\\u70b9\\u6c47\\u603b")]},
    {"id": "regional", "name": U("\\u533a\\u57df\\u62db\\u5546"), "short": U("\\u533a\\u57df"), "audience": U("\\u5730\\u65b9\\u653f\\u5e9c / \\u56ed\\u533a / \\u62db\\u5546\\u56e2\\u961f"), "keywords": [U("\\u533a\\u57df"), U("\\u6295\\u8d44"), U("\\u5916\\u8d44"), U("\\u76ee\\u5f55"), U("\\u9884\\u7b97\\u5185"), U("\\u751f\\u6001\\u4fdd\\u62a4"), U("\\u6c11\\u8425"), U("\\u519c\\u4e1a"), U("\\u68c9\\u82b1")], "signals": [U("\\u62db\\u5546\\u65b9\\u5411"), U("\\u8d44\\u91d1\\u652f\\u6301"), U("\\u4ea7\\u4e1a\\u76ee\\u5f55"), U("\\u533a\\u57df\\u9879\\u76ee")], "locked_tools": [U("\\u62db\\u5546\\u8bdd\\u672f"), U("\\u653f\\u7b56\\u5bf9\\u6807"), U("\\u9879\\u76ee\\u7ebf\\u7d22")]},
    {"id": "macro_ops", "name": U("\\u5b8f\\u89c2\\u7ecf\\u8425"), "short": U("\\u5b8f\\u89c2"), "audience": U("\\u4f01\\u4e1a\\u4e3b / \\u7ecf\\u8425\\u7ba1\\u7406\\u8005"), "keywords": [U("\\u5c45\\u6c11\\u6d88\\u8d39"), U("\\u4ef7\\u683c"), "CPI", "PPI", U("\\u5229\\u6da6"), U("\\u56fa\\u5b9a\\u8d44\\u4ea7"), U("\\u4eba\\u53e3"), U("\\u91c7\\u8d2d\\u7ecf\\u7406"), "PMI"], "signals": [U("\\u9700\\u6c42\\u53d8\\u5316"), U("\\u4ef7\\u683c\\u8d8b\\u52bf"), U("\\u7ecf\\u8425\\u538b\\u529b"), U("\\u5e02\\u573a\\u5224\\u65ad")], "locked_tools": [U("\\u7ecf\\u8425\\u6668\\u62a5"), U("\\u6307\\u6807\\u770b\\u677f"), U("\\u7ba1\\u7406\\u5c42\\u7b80\\u62a5")]},
]


def item_text(item):
    return " ".join([item.get("title", ""), item.get("category", ""), item.get("source_name", ""), " ".join(item.get("tags", [])), item.get("scene", ""), item.get("consulting_value", "")])


def match_score(item, space):
    text = item_text(item)
    score = 0
    hits = []
    for keyword in space["keywords"]:
        if keyword in text:
            score += 12
            hits.append(keyword)
    if item.get("category") in {C["policy"], C["local"]}:
        score += 8
    if item.get("category") == C["macro"] and space["id"] in {"consulting", "manufacturing", "macro_ops"}:
        score += 8
    if item.get("category") == C["finance"] and space["id"] in {"consulting", "finance", "regional"}:
        score += 8
    score += min(item.get("score", 0) // 10, 9)
    return score, hits[:5]


def make_brief(space, top_items):
    if not top_items:
        return U("\\u8be5\\u7a7a\\u95f4\\u6682\\u65e0\\u8db3\\u591f\\u5339\\u914d\\u4fe1\\u606f\\uff0c\\u9700\\u8981\\u7ee7\\u7eed\\u8865\\u5145\\u5782\\u76f4\\u6e90\\u3002")
    main_category = Counter(item["category"] for item in top_items).most_common(1)[0][0]
    focus = U("\\u3001").join(space["signals"][:3])
    return U("\\u4eca\\u65e5\\u91cd\\u70b9\\u96c6\\u4e2d\\u5728") + main_category + U("\\uff0c\\u5efa\\u8bae\\u5173\\u6ce8") + focus + U("\\u3002")


def make_gaps(space):
    base = {
        "consulting": [U("\\u54a8\\u8be2\\u516c\\u53f8\\u89c2\\u70b9"), U("\\u5238\\u5546\\u884c\\u4e1a\\u62a5\\u544a"), U("\\u91cd\\u70b9\\u5ba2\\u6237\\u516c\\u544a")],
        "manufacturing": [U("\\u5de5\\u4fe1\\u90e8\\u6587\\u4ef6"), U("\\u9f99\\u5934\\u4f01\\u4e1a\\u5e74\\u62a5"), U("\\u4ea7\\u4e1a\\u94fe\\u4ef7\\u683c\\u6570\\u636e")],
        "energy_infra": [U("\\u80fd\\u6e90\\u5c40\\u653f\\u7b56"), U("\\u5730\\u65b9\\u9879\\u76ee\\u6e05\\u5355"), U("\\u91cd\\u5927\\u5de5\\u7a0b\\u62db\\u6295\\u6807")],
        "finance": [U("\\u5238\\u5546\\u7814\\u62a5"), U("\\u6295\\u8d44\\u673a\\u6784\\u89c2\\u70b9"), U("\\u91d1\\u878d\\u76d1\\u7ba1\\u603b\\u5c40")],
        "regional": [U("\\u7701\\u5e02\\u653f\\u7b56\\u5e93"), U("\\u56ed\\u533a\\u62db\\u5546\\u653f\\u7b56"), U("\\u5730\\u65b9\\u53d1\\u6539\\u59d4\\u9879\\u76ee")],
        "macro_ops": [U("\\u9ad8\\u9891\\u6307\\u6807"), U("\\u884c\\u4e1a\\u534f\\u4f1a\\u6570\\u636e"), U("\\u6d88\\u8d39\\u4e0e\\u5c31\\u4e1a\\u8865\\u5145\\u6e90")],
    }
    return base.get(space["id"], [])


def build_spaces(items):
    spaces = []
    for space in SPACES:
        ranked = []
        for item in items:
            score, hits = match_score(item, space)
            if score >= 18:
                ranked.append({
                    "item_id": item["id"],
                    "title": item["title"],
                    "url": item["url"],
                    "source_name": item["source_name"],
                    "category": item["category"],
                    "published_at": item["published_at"],
                    "score": score,
                    "matches": hits,
                    "scene": item.get("scene", ""),
                    "consulting_value": item.get("consulting_value", ""),
                })
        ranked.sort(key=lambda row: (row["score"], row["published_at"]), reverse=True)
        top_items = ranked[:10]
        spaces.append({**space, "item_count": len(ranked), "top_items": top_items, "brief": make_brief(space, top_items), "gaps": make_gaps(space)})
    return spaces


ROLES = [
    {"id": "public", "name": U("\\u516c\\u5f00\\u7528\\u6237"), "status": U("\\u53ef\\u76f4\\u63a5\\u4f7f\\u7528"), "description": U("\\u6d4f\\u89c8\\u767e\\u7075\\u516c\\u5f00\\u4fe1\\u606f\\u6d41\\u3001\\u884c\\u4e1a\\u7a7a\\u95f4\\u3001\\u539f\\u6587\\u94fe\\u63a5\\u548c\\u57fa\\u7840\\u641c\\u7d22\\u7b5b\\u9009\\u3002"), "features": [U("\\u516c\\u5f00\\u4fe1\\u606f\\u6d41"), U("\\u884c\\u4e1a\\u7a7a\\u95f4\\u6d4f\\u89c8"), U("\\u539f\\u6587\\u8df3\\u8f6c"), U("\\u57fa\\u7840\\u7b5b\\u9009")], "limits": [U("\\u65e0\\u4e2a\\u4eba\\u8ba2\\u9605"), U("\\u65e0\\u5ba2\\u6237\\u7b80\\u62a5"), U("\\u65e0\\u6df1\\u5ea6\\u6458\\u8981")]},
    {"id": "applicant", "name": U("\\u8ba4\\u8bc1\\u7533\\u8bf7\\u4e2d"), "status": U("\\u63d0\\u4ea4\\u8d44\\u6599\\u540e"), "description": U("\\u9009\\u62e9\\u884c\\u4e1a\\u65b9\\u5411\\uff0c\\u63d0\\u4ea4\\u8eab\\u4efd\\u6216\\u804c\\u4e1a\\u6750\\u6599\\uff0c\\u8fdb\\u5165\\u77e5\\u66f4\\u4e13\\u4e1a\\u5c42\\u5ba1\\u6838\\u3002"), "features": [U("\\u884c\\u4e1a\\u504f\\u597d"), U("\\u8bd5\\u7528\\u6668\\u62a5"), U("\\u6536\\u85cf\\u5939"), U("\\u7533\\u8bf7\\u8fdb\\u5ea6")], "limits": [U("\\u4e13\\u4e1a\\u62a5\\u544a\\u5bfc\\u51fa\\u53d7\\u9650"), U("\\u5ba2\\u6237\\u7a7a\\u95f4\\u4e0d\\u53ef\\u7528")]},
    {"id": "verified", "name": U("\\u77e5\\u66f4\\u8ba4\\u8bc1\\u987e\\u95ee"), "status": U("\\u5ba1\\u6838\\u901a\\u8fc7"), "description": U("\\u5f00\\u542f\\u987e\\u95ee\\u5de5\\u4f5c\\u53f0\\uff0c\\u7528\\u4e8e\\u5ba2\\u6237\\u6668\\u62a5\\u3001\\u4e13\\u9898\\u8ffd\\u8e2a\\u3001PPT \\u7d20\\u6750\\u5361\\u548c\\u9879\\u76ee\\u8d44\\u6599\\u6574\\u7406\\u3002"), "features": [U("\\u5ba2\\u6237\\u6668\\u62a5"), U("PPT \\u7d20\\u6750\\u5361"), U("\\u5f71\\u54cd\\u77e9\\u9635"), U("\\u4e13\\u9898\\u8ffd\\u8e2a"), U("\\u884c\\u4e1a\\u8ba2\\u9605")], "limits": [U("\\u9700\\u9075\\u5b88\\u6765\\u6e90\\u7248\\u6743\\u548c\\u5f15\\u7528\\u89c4\\u8303"), U("\\u516c\\u4f17\\u53f7\\u7b49\\u6388\\u6743\\u6e90\\u9700\\u5355\\u72ec\\u5f00\\u901a")]},
]


PRO_TOOLS = [
    {"id": "morning_brief", "name": U("\\u5ba2\\u6237\\u6668\\u62a5"), "stage": U("\\u8ba4\\u8bc1\\u540e\\u5f00\\u653e"), "description": U("\\u628a\\u884c\\u4e1a\\u7a7a\\u95f4\\u91cc\\u7684\\u9ad8\\u5206\\u7ebf\\u7d22\\u6574\\u7406\\u6210\\u5ba2\\u6237\\u53ef\\u8bfb\\u7684\\u6668\\u62a5\\u63d0\\u7eb2\\u3002"), "inputs": [U("\\u884c\\u4e1a\\u7a7a\\u95f4"), U("\\u5ba2\\u6237\\u884c\\u4e1a"), U("\\u5173\\u6ce8\\u5173\\u952e\\u8bcd")], "outputs": [U("\\u4eca\\u65e5\\u91cd\\u70b9"), U("\\u987e\\u95ee\\u89e3\\u8bfb"), U("\\u5efa\\u8bae\\u52a8\\u4f5c")]},
    {"id": "ppt_cards", "name": U("PPT \\u7d20\\u6750\\u5361"), "stage": U("\\u8ba4\\u8bc1\\u540e\\u5f00\\u653e"), "description": U("\\u628a\\u653f\\u7b56\\u3001\\u6570\\u636e\\u3001\\u516c\\u544a\\u8f6c\\u6210\\u53ef\\u8fdb\\u5165\\u54a8\\u8be2\\u6c47\\u62a5\\u7684\\u7d20\\u6750\\u5361\\u3002"), "inputs": [U("\\u539f\\u6587\\u94fe\\u63a5"), U("\\u6307\\u6807\\u6216\\u653f\\u7b56\\u6807\\u9898"), U("\\u9879\\u76ee\\u4e3b\\u9898")], "outputs": [U("\\u4e8b\\u5b9e\\u5361"), U("\\u5f71\\u54cd\\u5224\\u65ad"), U("\\u5f15\\u7528\\u94fe\\u63a5")]},
    {"id": "impact_matrix", "name": U("\\u5f71\\u54cd\\u77e9\\u9635"), "stage": U("\\u8ba4\\u8bc1\\u540e\\u5f00\\u653e"), "description": U("\\u6309\\u5ba2\\u6237\\u3001\\u884c\\u4e1a\\u3001\\u533a\\u57df\\u3001\\u65f6\\u95f4\\u7ef4\\u5ea6\\u8bc4\\u4f30\\u653f\\u7b56\\u548c\\u6570\\u636e\\u5f71\\u54cd\\u3002"), "inputs": [U("\\u653f\\u7b56\\u6761\\u76ee"), U("\\u5ba2\\u6237\\u7c7b\\u578b"), U("\\u533a\\u57df")], "outputs": [U("\\u673a\\u4f1a"), U("\\u98ce\\u9669"), U("\\u5f85\\u786e\\u8ba4\\u95ee\\u9898")]},
    {"id": "topic_tracker", "name": U("\\u4e13\\u9898\\u8ffd\\u8e2a"), "stage": U("\\u8ba4\\u8bc1\\u540e\\u5f00\\u653e"), "description": U("\\u56f4\\u7ed5\\u5341\\u4e94\\u4e94\\u3001\\u5916\\u8d44\\u3001\\u6c11\\u8425\\u7ecf\\u6d4e\\u3001\\u4ef7\\u683c\\u3001PMI \\u7b49\\u4e3b\\u9898\\u6301\\u7eed\\u8ffd\\u8e2a\\u3002"), "inputs": [U("\\u4e3b\\u9898\\u5173\\u952e\\u8bcd"), U("\\u4fe1\\u6e90\\u8303\\u56f4"), U("\\u66f4\\u65b0\\u9891\\u7387")], "outputs": [U("\\u53d8\\u5316\\u8bb0\\u5f55"), U("\\u5173\\u952e\\u8282\\u70b9"), U("\\u63d0\\u9192")]},
]


def collect_public_data():
    all_items, source_status = [], []
    for row in SOURCES:
        source = source_dict(row)
        started = datetime.now()
        try:
            items = collect_source(source)
            all_items.extend(items)
            source_status.append({"source_id": source["id"], "name": source["name"], "url": source.get("home_url") or source["url"], "status": "ok" if items else "empty", "items": len(items), "mode": source["mode"], "category": source["category"], "latency_ms": int((datetime.now() - started).total_seconds() * 1000)})
        except Exception as exc:
            source_status.append({"source_id": source["id"], "name": source["name"], "url": source.get("home_url") or source["url"], "status": "error", "items": 0, "mode": source["mode"], "category": source["category"], "error": str(exc)})
    all_items.sort(key=lambda item: item["published_at"], reverse=True)
    return {"product": C["product"], "professional_layer": C["pro"], "version": "source-expanded-clean-2", "generated_at": datetime.now().isoformat(timespec="seconds"), "item_count": len(all_items), "sources": source_status, "candidate_sources": CANDIDATE_SOURCES, "items": all_items}


def build_industry_data(public_data):
    spaces = build_spaces(public_data["items"])
    return {"product": C["product"], "professional_layer": C["pro"], "version": "industry-spaces-clean-2", "generated_at": datetime.now().isoformat(timespec="seconds"), "input_generated_at": public_data.get("generated_at"), "source_item_count": public_data.get("item_count", 0), "space_count": len(spaces), "spaces": spaces}


def build_auth_data(industry_data):
    spaces = []
    category_counter = Counter()
    for space in industry_data.get("spaces", []):
        top_items = space.get("top_items", [])
        spaces.append({"id": space["id"], "name": space["name"], "audience": space["audience"], "item_count": space["item_count"], "brief": space["brief"], "recommended_tools": space.get("locked_tools", [])[:3], "top_titles": [item["title"] for item in top_items[:3]]})
        for item in top_items:
            category_counter[item.get("category", U("\\u672a\\u5206\\u7c7b"))] += 1
    return {"product": C["pro"], "parent_product": C["product"], "version": "auth-workspace-clean-2", "generated_at": datetime.now().isoformat(timespec="seconds"), "industry_input_generated_at": industry_data.get("generated_at"), "source_item_count": industry_data.get("source_item_count", 0), "space_count": len(spaces), "roles": ROLES, "application_steps": [{"name": U("\\u9009\\u62e9\\u8eab\\u4efd"), "detail": U("\\u4e2a\\u4eba\\u7528\\u6237\\u3001\\u4f01\\u4e1a\\u7ecf\\u8425\\u8005\\u3001\\u54a8\\u8be2\\u987e\\u95ee\\u3001\\u884c\\u4e1a\\u7814\\u7a76\\u5458\\u3002")}, {"name": U("\\u9009\\u62e9\\u884c\\u4e1a"), "detail": U("\\u4ece\\u7ba1\\u7406\\u54a8\\u8be2\\u3001\\u5236\\u9020\\u4e1a\\u3001\\u80fd\\u6e90\\u57fa\\u5efa\\u3001\\u8d22\\u653f\\u91d1\\u878d\\u3001\\u533a\\u57df\\u62db\\u5546\\u7b49\\u7a7a\\u95f4\\u4e2d\\u9009\\u62e9\\u3002")}, {"name": U("\\u63d0\\u4ea4\\u8bc1\\u660e"), "detail": U("\\u53ef\\u7528\\u516c\\u53f8\\u90ae\\u7bb1\\u3001\\u540d\\u7247\\u3001\\u9879\\u76ee\\u7ecf\\u5386\\u6216\\u673a\\u6784\\u8bc1\\u660e\\u3002")}, {"name": U("\\u5f00\\u901a\\u77e5\\u66f4"), "detail": U("\\u5ba1\\u6838\\u540e\\u83b7\\u5f97\\u4e13\\u4e1a\\u5de5\\u5177\\u3001\\u8ba2\\u9605\\u548c\\u5de5\\u4f5c\\u53f0\\u80fd\\u529b\\u3002")}], "pro_tools": PRO_TOOLS, "spaces": spaces, "category_distribution": dict(category_counter)}


def js_json(value):
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def build_ui():
    return {
        "nav": [["home", U("\\u603b\\u89c8"), "green"], ["feed", U("\\u767e\\u7075\\u516c\\u5f00\\u7248"), "blue"], ["spaces", U("\\u884c\\u4e1a\\u7a7a\\u95f4"), "green"], ["zhigeng", U("\\u8ba4\\u8bc1\\u7533\\u8bf7"), "gold"], ["workspace", U("\\u77e5\\u66f4\\u5de5\\u4f5c\\u53f0"), "red"], ["admin", U("\\u540e\\u53f0\\u7ba1\\u7406"), "blue"]],
        "title": U("\\u767e\\u7075 / \\u77e5\\u66f4"),
        "tagline": U("\\u653f\\u7b56\\u3001\\u4ea7\\u4e1a\\u3001\\u5b8f\\u89c2\\u548c\\u987e\\u95ee\\u5de5\\u4f5c\\u6d41\\u7684\\u4e00\\u4f53\\u5316\\u60c5\\u62a5\\u5e73\\u53f0\\u3002"),
        "heroTitle": U("\\u628a\\u6743\\u5a01\\u653f\\u7b56\\u3001\\u884c\\u4e1a\\u7a7a\\u95f4\\u548c\\u987e\\u95ee\\u5de5\\u4f5c\\u6d41\\u653e\\u8fdb\\u4e00\\u4e2a\\u5e73\\u53f0\\u3002"),
        "heroSub": U("\\u767e\\u7075\\u8d1f\\u8d23\\u516c\\u5f00\\u4fe1\\u606f\\u805a\\u5408\\u548c\\u884c\\u4e1a\\u7a7a\\u95f4\\uff0c\\u77e5\\u66f4\\u8d1f\\u8d23\\u8ba4\\u8bc1\\u987e\\u95ee\\u7684\\u4e13\\u4e1a\\u5de5\\u4f5c\\u53f0\\u3002\\u5e73\\u53f0\\u5df2\\u63a5\\u5165\\u516c\\u5f00\\u6743\\u5a01\\u4fe1\\u6e90\\uff0c\\u5e76\\u63d0\\u4f9b\\u884c\\u4e1a\\u5206\\u53d1\\u3001\\u8ba4\\u8bc1\\u6d41\\u7a0b\\u3001\\u6536\\u85cf\\u3001\\u6668\\u62a5\\u751f\\u6210\\u548c\\u540e\\u53f0\\u7ba1\\u7406\\u3002"),
        "items": U("\\u771f\\u5b9e\\u6761\\u76ee"), "sources": U("\\u5df2\\u63a5\\u5165\\u6e90"), "policies": C["policy"], "latest": U("\\u6700\\u65b0\\u65e5\\u671f"),
        "feedTitle": U("\\u767e\\u7075\\u516c\\u5f00\\u7248\\u4fe1\\u606f\\u6d41\\u3002"), "feedSub": U("\\u4f18\\u5148\\u63a5\\u5165\\u516c\\u5f00\\u3001\\u6743\\u5a01\\u3001\\u53ef\\u9a8c\\u8bc1\\u7684\\u653f\\u7b56\\u3001\\u5b8f\\u89c2\\u548c\\u8d22\\u653f\\u91d1\\u878d\\u4fe1\\u6e90\\u3002"),
        "spacesTitle": U("\\u4ece\\u4fe1\\u606f\\u6d41\\u8fdb\\u5165\\u884c\\u4e1a\\u7a7a\\u95f4\\u3002"), "spacesSub": U("\\u540c\\u4e00\\u6279\\u6743\\u5a01\\u4fe1\\u606f\\u4f1a\\u6309\\u884c\\u4e1a\\u3001\\u573a\\u666f\\u548c\\u987e\\u95ee\\u4ef7\\u503c\\u91cd\\u65b0\\u5206\\u53d1\\uff0c\\u5e2e\\u52a9\\u4e0d\\u540c\\u7528\\u6237\\u66f4\\u5feb\\u770b\\u5230\\u81ea\\u5df1\\u5173\\u5fc3\\u7684\\u7ebf\\u7d22\\u3002"),
        "authTitle": U("\\u77e5\\u66f4\\u8ba4\\u8bc1\\uff0c\\u628a\\u516c\\u5f00\\u4fe1\\u606f\\u8f6c\\u6210\\u4e13\\u4e1a\\u5de5\\u4f5c\\u6d41\\u3002"), "authSub": U("\\u8d26\\u53f7\\u72b6\\u6001\\u3001\\u8ba4\\u8bc1\\u7533\\u8bf7\\u3001\\u884c\\u4e1a\\u504f\\u597d\\u548c\\u4e13\\u4e1a\\u6743\\u9650\\u5728\\u8fd9\\u91cc\\u7edf\\u4e00\\u7ba1\\u7406\\u3002"),
        "workspaceTitle": U("\\u77e5\\u66f4\\u5de5\\u4f5c\\u53f0\\u3002"), "workspaceSub": U("\\u8fd9\\u91cc\\u628a\\u6536\\u85cf\\u3001\\u8ba2\\u9605\\u3001\\u6668\\u62a5\\u70b9\\u548c\\u4e13\\u4e1a\\u5de5\\u5177\\u653e\\u5728\\u4e00\\u8d77\\uff0c\\u5f62\\u6210\\u987e\\u95ee\\u65e5\\u5e38\\u4f7f\\u7528\\u7684\\u5de5\\u4f5c\\u53f0\\u3002"),
        "adminTitle": U("\\u540e\\u53f0\\u7ba1\\u7406\\u3002"), "adminSub": U("\\u8fd9\\u4e00\\u5c42\\u7528\\u6765\\u89c2\\u5bdf\\u4fe1\\u6e90\\u5065\\u5eb7\\u5ea6\\u3001\\u5f85\\u9002\\u914d\\u4fe1\\u6e90\\u548c\\u540e\\u7eed\\u5f00\\u53d1\\u4efb\\u52a1\\u3002"),
    }


def render_app(public_data, industry_data, auth_data):
    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BAILING / ZHIGENG</title>
  <style>
    :root{--bg:#f6f7f3;--surface:#fff;--soft:#eef2eb;--ink:#171a17;--muted:#5f675e;--weak:#8c9589;--line:#d8e0d5;--green:#246f58;--green-soft:#e2f0ea;--red:#b25443;--red-soft:#f5e5e1;--blue:#2d6e96;--blue-soft:#e2eef5;--gold:#9b6d21;--gold-soft:#f3ead5;--nav:#18231d;--shadow:0 16px 36px rgba(31,44,34,.08);--mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;--sans:Inter,"PingFang SC","Microsoft YaHei",Arial,sans-serif}
    *{box-sizing:border-box}body{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:var(--sans);letter-spacing:0}a{color:inherit;text-decoration:none}button,input,select,textarea{font:inherit}
    .app{min-height:100vh;display:grid;grid-template-columns:260px minmax(0,1fr)}.side{position:sticky;top:0;height:100vh;background:var(--nav);color:#f6f3e9;padding:20px 14px;display:flex;flex-direction:column;gap:18px}.brand{padding:0 10px 14px;border-bottom:1px solid rgba(255,255,255,.12)}.brand-line{display:flex;align-items:center;gap:10px}.mark{width:34px;height:34px;border-radius:8px;display:grid;place-items:center;background:#d8efe4;color:#153a2c;font-size:18px;font-weight:900}.brand h1{margin:0;font-size:21px;line-height:1}.brand p{margin:8px 0 0;color:rgba(246,243,233,.64);font-size:12px;line-height:1.55}.nav{display:grid;gap:7px}.nav button{height:40px;border:0;border-radius:8px;background:transparent;color:rgba(246,243,233,.74);display:flex;align-items:center;gap:10px;text-align:left;padding:0 10px;cursor:pointer}.nav button:hover,.nav button.active{background:rgba(255,255,255,.08);color:#fff}.nav i{width:10px;height:10px;border-radius:999px;background:var(--green)}.nav i.gold{background:var(--gold)}.nav i.blue{background:var(--blue)}.nav i.red{background:var(--red)}
    .profile{margin-top:auto;border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:12px;background:rgba(255,255,255,.05)}.profile b{display:block;font-size:14px}.profile span{display:inline-flex;margin-top:8px;border-radius:999px;border:1px solid rgba(216,239,228,.3);padding:4px 8px;color:#d8efe4;font-size:11px}.profile p{margin:9px 0 0;color:rgba(246,243,233,.64);font-size:12px;line-height:1.55}
    .main{min-width:0;padding:20px 24px 42px;display:grid;gap:16px}.view{display:none}.view.active{display:grid;gap:16px}.hero{display:grid;grid-template-columns:minmax(0,1fr) 440px;gap:16px;align-items:stretch}.hero-copy{padding:18px 0}.eyebrow{margin:0 0 9px;color:var(--green);font:800 12px var(--mono)}.hero h2{margin:0;font-size:34px;line-height:1.16}.hero p{max-width:780px;margin:11px 0 0;color:var(--muted);font-size:14px;line-height:1.75}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.metric{border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:13px;box-shadow:var(--shadow)}.metric span{display:block;color:var(--muted);font-size:12px}.metric b{display:block;margin-top:7px;font:900 26px/1 var(--mono)}.metric small{display:block;margin-top:6px;color:var(--weak);font-size:11px}
    .toolbar{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:10px}.search{height:38px;min-width:min(460px,100%);flex:1 1 420px;display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:8px;background:var(--soft);padding:0 11px}.search input{width:100%;min-width:0;border:0;outline:0;background:transparent}.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{height:34px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--muted);padding:0 12px;font-size:12px;cursor:pointer}.chip.active{border-color:rgba(36,111,88,.35);background:var(--green-soft);color:var(--green);font-weight:800}
    .grid{display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:16px;align-items:start}.panel{border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}.panel-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line);background:#fbfcfa}.panel-head h3{margin:0;font-size:16px}.panel-head span{color:var(--weak);font:11px var(--mono);white-space:nowrap}.feed{display:grid;gap:10px;padding:14px}.card{border:1px solid var(--line);border-radius:8px;background:#fff;padding:13px;display:grid;gap:9px}.card:hover{border-color:#b7c5b2}.meta{display:flex;gap:7px;align-items:center;color:var(--muted);font-size:12px}.pill{display:inline-flex;align-items:center;min-height:22px;border-radius:999px;padding:0 7px;background:var(--blue-soft);color:var(--blue);font-weight:800}.pill.policy{background:var(--red-soft);color:var(--red)}.pill.finance{background:var(--gold-soft);color:var(--gold)}.meta strong{margin-left:auto;color:var(--green);font:900 12px var(--mono)}.card a.title{font-size:15px;font-weight:900;line-height:1.45}.card a.title:hover{color:var(--green)}.card p{margin:0;color:var(--muted);font-size:12px;line-height:1.65}.tags{display:flex;gap:6px;flex-wrap:wrap}.tags span{border-radius:4px;background:var(--soft);color:#4e594d;padding:4px 6px;font:11px var(--mono)}.actions{display:flex;gap:7px;flex-wrap:wrap}.actions button,.primary{height:32px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--muted);padding:0 10px;font-size:12px;cursor:pointer}.actions button:hover,.primary:hover{border-color:rgba(36,111,88,.35);background:var(--green-soft);color:var(--green)}.primary{display:inline-flex;align-items:center;background:var(--green);border-color:var(--green);color:#fff}.primary:hover{background:#1f604c;color:#fff}
    .side-stack{display:grid;gap:16px}.source-list,.mini-list{display:grid;gap:8px;padding:12px}.source-row,.mini-row{border:1px solid var(--line);border-radius:8px;background:#fbfcfa;padding:10px;display:grid;gap:6px}.source-row header,.mini-row header{display:flex;align-items:center;justify-content:space-between;gap:8px}.source-row strong,.mini-row strong{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.source-row em,.mini-row em{font-style:normal;color:var(--green);font:800 11px var(--mono);white-space:nowrap}.source-row p,.mini-row p{margin:0;color:var(--muted);font-size:12px;line-height:1.55}.empty em,.needs_adapter em{color:var(--gold)}.error em{color:var(--red)}
    .space-tabs{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}.space-tab{min-width:0;text-align:left;border:1px solid var(--line);border-radius:8px;background:#fff;padding:11px;box-shadow:var(--shadow);cursor:pointer}.space-tab.active,.space-tab:hover{border-color:rgba(36,111,88,.45);background:var(--green-soft)}.space-tab span{display:inline-flex;width:28px;height:24px;border-radius:6px;align-items:center;justify-content:center;background:var(--nav);color:#fff;font-size:12px;font-weight:900}.space-tab b{display:block;margin-top:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.space-tab em{display:block;margin-top:5px;color:var(--muted);font-style:normal;font:12px var(--mono)}.space-panel{display:none}.space-panel.active{display:grid;gap:16px}.space-head{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:16px;border:1px solid var(--line);border-radius:8px;background:#fff;padding:16px;box-shadow:var(--shadow)}.space-head p{margin:0;color:var(--muted);font-size:13px}.space-head h3{margin:6px 0 0;font-size:24px}.brief{align-self:center;border-left:3px solid var(--green);padding:9px 12px;background:var(--green-soft);border-radius:0 8px 8px 0;color:#245b47;font-size:13px;line-height:1.65}.workspace{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px}.cards2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .role-grid,.tool-grid,.admin-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:14px}.tool-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.role-card,.tool-card,.admin-card{border:1px solid var(--line);border-radius:8px;background:#fff;padding:13px}.role-card.active{border-color:rgba(155,109,33,.45);background:var(--gold-soft)}.role-card header,.tool-card header,.admin-card header{display:flex;justify-content:space-between;gap:8px;align-items:center}.role-card strong,.tool-card strong,.admin-card strong{font-size:15px}.role-card em,.tool-card em,.admin-card em{font-style:normal;border-radius:999px;background:var(--soft);color:var(--muted);padding:4px 8px;font-size:11px;white-space:nowrap}.role-card p,.tool-card p,.admin-card p{margin:9px 0 0;color:var(--muted);font-size:12px;line-height:1.6}.role-card ul,.admin-card ul{margin:10px 0 0;padding-left:18px;color:var(--weak);font-size:12px;line-height:1.7}.form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding:14px}.field{display:grid;gap:6px}.field.full{grid-column:1/-1}.field label{font-size:12px;color:var(--muted);font-weight:800}.field input,.field select,.field textarea{border:1px solid var(--line);border-radius:8px;background:#fff;padding:9px 10px;color:var(--ink);outline:0}.field textarea{min-height:92px;resize:vertical}.output{border:1px dashed var(--line);border-radius:8px;background:#fbfcfa;padding:12px;color:var(--muted);font-size:13px;line-height:1.7;white-space:pre-wrap}.toast{position:fixed;right:18px;bottom:18px;max-width:360px;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:var(--shadow);padding:12px;color:var(--ink);display:none}.toast.show{display:block}.toast b{display:block;font-size:14px}.toast p{margin:5px 0 0;color:var(--muted);font-size:12px;line-height:1.5}
    @media(max-width:1180px){.hero,.grid,.workspace{grid-template-columns:1fr}.space-tabs{grid-template-columns:repeat(3,minmax(0,1fr))}.tool-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.space-head{grid-template-columns:1fr}.cards2{grid-template-columns:1fr}}@media(max-width:860px){.app{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:16px 14px 34px}.hero h2{font-size:28px}.metrics,.role-grid,.tool-grid,.admin-grid,.form{grid-template-columns:1fr}.space-tabs{grid-template-columns:repeat(2,minmax(0,1fr))}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="side"><div class="brand"><div class="brand-line"><div class="mark">百</div><h1 id="brandTitle"></h1></div><p id="brandTagline"></p></div><nav class="nav" id="nav"></nav><section class="profile"><b id="profileName"></b><span id="profileRole"></span><p id="profileDesc"></p></section></aside>
    <main class="main"><section class="view active" id="view-home"></section><section class="view" id="view-feed"></section><section class="view" id="view-spaces"></section><section class="view" id="view-zhigeng"></section><section class="view" id="view-workspace"></section><section class="view" id="view-admin"></section></main>
  </div>
  <div class="toast" id="toast"><b></b><p></p></div>
  <script>
    const data = __DATA__;
    const spacesPayload = __SPACES__;
    const authPayload = __AUTH__;
    const UI = __UI__;
    document.title = UI.title; document.getElementById('brandTitle').textContent = UI.title; document.getElementById('brandTagline').textContent = UI.tagline;
    const state={view:'home',category:'全部',query:'',space:'',role:localStorage.getItem('bz_role')||'public',saved:JSON.parse(localStorage.getItem('bz_saved')||'[]'),subscriptions:JSON.parse(localStorage.getItem('bz_subscriptions')||'["十五五","投资","PMI"]'),briefs:JSON.parse(localStorage.getItem('bz_briefs')||'[]')};
    const qs=id=>document.getElementById(id); const esc=v=>String(v??'').replace(/[&<>"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s])); const save=()=>{localStorage.setItem('bz_role',state.role);localStorage.setItem('bz_saved',JSON.stringify(state.saved));localStorage.setItem('bz_subscriptions',JSON.stringify(state.subscriptions));localStorage.setItem('bz_briefs',JSON.stringify(state.briefs));};
    function toast(t,b){const el=qs('toast');el.querySelector('b').textContent=t;el.querySelector('p').textContent=b;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2600)}
    function pillClass(cat){return cat==='国家政策'||cat==='地方政策'?'policy':cat==='财政金融'?'finance':''}
    function categoryCounts(){return data.items.reduce((a,i)=>{a[i.category]=(a[i.category]||0)+1;return a},{})}
    function sourceStatusCounts(){return data.sources.reduce((a,s)=>{a[s.status]=(a[s.status]||0)+1;return a},{})}
    function renderNav(){qs('nav').innerHTML=UI.nav.map(([id,label,color])=>`<button class="${state.view===id?'active':''}" data-view="${id}"><i class="${color}"></i>${esc(label)}</button>`).join('');qs('nav').querySelectorAll('button').forEach(b=>b.onclick=()=>setView(b.dataset.view))}
    function setView(view){state.view=view;document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));document.querySelectorAll('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));render()}
    function updateProfile(){const role=(authPayload.roles||[]).find(r=>r.id===state.role)||authPayload.roles[0];qs('profileName').textContent=role.name;qs('profileRole').textContent=role.id;qs('profileDesc').textContent=role.description}
    function hero(title,sub,eyebrow='BAILING / ZHIGENG'){const counts=categoryCounts(), status=sourceStatusCounts(), latest=data.items.map(i=>i.published_at).sort().pop()||'';return `<section class="hero"><div class="hero-copy"><p class="eyebrow">${esc(eyebrow)}</p><h2>${esc(title)}</h2><p>${esc(sub)}</p></div><div class="metrics"><div class="metric"><span>${esc(UI.items)}</span><b>${data.items.length}</b><small>public verified sources</small></div><div class="metric"><span>${esc(UI.sources)}</span><b>${status.ok||0}</b><small>${data.sources.length} sources monitored</small></div><div class="metric"><span>${esc(UI.policies)}</span><b>${counts['国家政策']||0}</b><small>gov.cn / ndrc / local</small></div><div class="metric"><span>${esc(UI.latest)}</span><b style="font-size:20px">${esc(latest.slice(5))}</b><small>${esc(data.generated_at)}</small></div></div></section>`}
    function itemCard(item){const saved=state.saved.includes(item.id);return `<article class="card"><div class="meta"><span class="pill ${pillClass(item.category)}">${esc(item.category)}</span><span>${esc(item.published_at)}</span><span>${esc(item.source_name)}</span><strong>${esc(item.score||'')}</strong></div><a class="title" href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a><p>${esc(item.consulting_value||item.public_value||'')}</p><div class="tags">${(item.tags||[]).map(t=>`<span>${esc(t)}</span>`).join('')}</div><div class="actions"><button data-action="save" data-id="${esc(item.id)}">${saved?'已收藏':'收藏'}</button><button data-action="brief" data-id="${esc(item.id)}">生成晨报点</button><a class="primary" href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">原文</a></div></article>`}
    function attachActions(root=document){root.querySelectorAll('[data-action="save"]').forEach(btn=>btn.onclick=()=>{const id=btn.dataset.id;if(state.saved.includes(id)){state.saved=state.saved.filter(x=>x!==id);toast('已取消收藏','该条目已从收藏夹移除。')}else{state.saved.push(id);toast('已收藏','条目已加入本地收藏夹。')}save();render()});root.querySelectorAll('[data-action="brief"]').forEach(btn=>btn.onclick=()=>{const item=data.items.find(i=>i.id===btn.dataset.id);if(!item)return;state.briefs.unshift({id:'brief_'+Date.now(),title:item.title,created_at:new Date().toLocaleString(),body:`今日关注：${item.title}\n来源：${item.source_name}\n顾问判断：${item.consulting_value||item.public_value}\n建议动作：纳入客户晨报，结合客户行业判断机会、风险和待确认问题。\n原文：${item.url}`});save();toast('已生成晨报点','可在知更工作台查看。')})}
    function filteredItems(){return data.items.filter(i=>{const ok=state.category==='全部'||i.category===state.category;const text=[i.title,i.source_name,i.category,(i.tags||[]).join(' '),i.consulting_value].join(' ').toLowerCase();return ok&&(!state.query||text.includes(state.query.toLowerCase()))})}
    function renderHome(){qs('view-home').innerHTML=hero(UI.heroTitle,UI.heroSub)+`<section class="grid"><div class="panel"><div class="panel-head"><h3>最新信息</h3><span>${data.items.length} items</span></div><div class="feed">${data.items.slice(0,8).map(itemCard).join('')}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>产品闭环</h3><span>live</span></div><div class="mini-list"><div class="mini-row"><header><strong>百灵公开版</strong><em>L0</em></header><p>公开权威源采集、筛选、原文跳转。</p></div><div class="mini-row"><header><strong>百灵行业空间</strong><em>L1</em></header><p>把同一批信息映射到咨询、制造、能源、金融等空间。</p></div><div class="mini-row"><header><strong>知更工作台</strong><em>L3</em></header><p>认证后使用晨报、素材卡、专题追踪、影响矩阵。</p></div></div></div><div class="panel"><div class="panel-head"><h3>我的状态</h3><span>${esc(state.role)}</span></div><div class="mini-list"><div class="mini-row"><header><strong>收藏</strong><em>${state.saved.length}</em></header><p>保存你关注的政策、数据和行业线索。</p></div><div class="mini-row"><header><strong>晨报点</strong><em>${state.briefs.length}</em></header><p>从条目生成的客户晨报素材。</p></div></div></div></aside></section>`;attachActions(qs('view-home'))}
    function renderFeed(){const cats=['全部',...Object.keys(categoryCounts())];qs('view-feed').innerHTML=hero(UI.feedTitle,UI.feedSub,'BAILING PUBLIC FEED')+`<section class="toolbar"><label class="search"><span>搜索</span><input id="searchInput" value="${esc(state.query)}" placeholder="政策、行业、来源、关键词" /></label><div class="chips">${cats.map(c=>`<button class="chip ${state.category===c?'active':''}" data-cat="${esc(c)}">${esc(c)}</button>`).join('')}</div></section><section class="grid"><div class="panel"><div class="panel-head"><h3>信息流</h3><span>${filteredItems().length} matched</span></div><div class="feed">${filteredItems().map(itemCard).join('')||'<div class="mini-row"><p>没有匹配结果。</p></div>'}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>信源健康度</h3><span>${data.sources.length} sources</span></div><div class="source-list">${data.sources.map(s=>`<div class="source-row ${esc(s.status)}"><header><strong>${esc(s.name)}</strong><em>${esc(s.status)}</em></header><p>${esc(s.category)} · ${esc(s.mode)} · ${esc(s.items)} 条</p></div>`).join('')}</div></div><div class="panel"><div class="panel-head"><h3>待适配源</h3><span>backlog</span></div><div class="source-list">${data.candidate_sources.map(s=>`<div class="source-row ${esc(s.status)}"><header><strong>${esc(s.name)}</strong><em>${esc(s.status)}</em></header><p>${esc(s.reason)}</p></div>`).join('')}</div></div></aside></section>`;qs('searchInput').oninput=e=>{state.query=e.target.value;renderFeed()};qs('view-feed').querySelectorAll('[data-cat]').forEach(b=>b.onclick=()=>{state.category=b.dataset.cat;renderFeed()});attachActions(qs('view-feed'))}
    function renderSpaces(){if(!state.space)state.space=spacesPayload.spaces[0]?.id||'';qs('view-spaces').innerHTML=hero(UI.spacesTitle,UI.spacesSub,'BAILING INDUSTRY SPACES')+`<nav class="space-tabs">${spacesPayload.spaces.map(s=>`<button class="space-tab ${state.space===s.id?'active':''}" data-space="${esc(s.id)}"><span>${esc(s.short)}</span><b>${esc(s.name)}</b><em>${esc(s.item_count)} 条</em></button>`).join('')}</nav>${spacesPayload.spaces.map(space=>`<section class="space-panel ${state.space===space.id?'active':''}"><div class="space-head"><div><p>${esc(space.audience)}</p><h3>${esc(space.name)}空间</h3></div><div class="brief">${esc(space.brief)}</div></div><div class="workspace"><div class="cards2">${(space.top_items||[]).slice(0,10).map(item=>`<article class="card"><div class="meta"><span class="pill ${pillClass(item.category)}">${esc(item.category)}</span><span>${esc(item.published_at)}</span><strong>${esc(item.score)}</strong></div><a class="title" href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a><p>${esc(item.consulting_value)}</p><div class="tags">${(item.matches||[]).map(m=>`<span>${esc(m)}</span>`).join('')}</div></article>`).join('')}</div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>知更工具</h3><span>locked</span></div><div class="mini-list">${space.locked_tools.map(t=>`<div class="mini-row"><header><strong>${esc(t)}</strong><em>认证后</em></header><p>面向${esc(space.name)}空间的专业工具。</p></div>`).join('')}</div></div><div class="panel"><div class="panel-head"><h3>待补信源</h3><span>gap</span></div><div class="mini-list">${space.gaps.map(g=>`<div class="mini-row"><header><strong>${esc(g)}</strong><em>next</em></header><p>后续信源扩展方向。</p></div>`).join('')}</div></div></aside></div></section>`).join('')}`;qs('view-spaces').querySelectorAll('[data-space]').forEach(b=>b.onclick=()=>{state.space=b.dataset.space;renderSpaces()})}
    function renderZhigeng(){qs('view-zhigeng').innerHTML=hero(UI.authTitle,UI.authSub,'ZHIGENG AUTH')+`<section class="panel"><div class="panel-head"><h3>账号与权限</h3><span>${esc(state.role)}</span></div><div class="role-grid">${authPayload.roles.map(r=>`<article class="role-card ${state.role===r.id?'active':''}"><header><strong>${esc(r.name)}</strong><em>${esc(r.status)}</em></header><p>${esc(r.description)}</p><div class="tags">${r.features.map(f=>`<span>${esc(f)}</span>`).join('')}</div><ul>${r.limits.map(l=>`<li>${esc(l)}</li>`).join('')}</ul><div class="actions"><button data-role="${esc(r.id)}">切换为该状态</button></div></article>`).join('')}</div></section><section class="panel"><div class="panel-head"><h3>认证申请</h3><span>application</span></div><div class="form"><div class="field"><label>身份类型</label><select><option>咨询顾问</option><option>企业经营者</option><option>行业研究员</option><option>政府/园区人员</option></select></div><div class="field"><label>关注行业</label><select>${spacesPayload.spaces.map(s=>`<option>${esc(s.name)}</option>`).join('')}</select></div><div class="field full"><label>申请说明</label><textarea placeholder="简单说明你的行业、使用场景、希望追踪的信息源"></textarea></div><div class="field full"><button class="primary" id="applyBtn">提交认证申请</button></div></div></section>`;qs('view-zhigeng').querySelectorAll('[data-role]').forEach(b=>b.onclick=()=>{state.role=b.dataset.role;save();updateProfile();renderZhigeng();toast('状态已切换',`当前身份：${b.dataset.role}`)});qs('applyBtn').onclick=()=>{state.role='applicant';save();updateProfile();toast('申请已提交','当前状态切换为认证申请中。')}}
    function renderWorkspace(){const verified=state.role==='verified';qs('view-workspace').innerHTML=hero(UI.workspaceTitle,UI.workspaceSub,'ZHIGENG WORKSPACE')+`${!verified?'<div class="panel"><div class="panel-head"><h3>权限提示</h3><span>not verified</span></div><div class="mini-list"><div class="mini-row"><p>你当前还不是知更认证顾问，可以在“认证申请”里切换为认证顾问体验完整工作台。</p></div></div></div>':''}<section class="grid"><div class="panel"><div class="panel-head"><h3>专业工具</h3><span>${verified?'enabled':'preview'}</span></div><div class="tool-grid">${authPayload.pro_tools.map(t=>`<article class="tool-card"><header><strong>${esc(t.name)}</strong><em>${verified?'可使用':'认证后'}</em></header><p>${esc(t.description)}</p><div class="actions"><button data-tool="${esc(t.id)}">${verified?'运行':'查看说明'}</button></div></article>`).join('')}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>我的订阅</h3><span>${state.subscriptions.length}</span></div><div class="mini-list">${state.subscriptions.map(s=>`<div class="mini-row"><header><strong>${esc(s)}</strong><em>on</em></header><p>关键词追踪中。</p></div>`).join('')}<div class="actions"><button id="addSub">添加订阅</button></div></div></div></aside></section><section class="grid"><div class="panel"><div class="panel-head"><h3>晨报素材</h3><span>${state.briefs.length}</span></div><div class="feed">${state.briefs.map(b=>`<article class="card"><div class="meta"><span>${esc(b.created_at)}</span></div><a class="title">${esc(b.title)}</a><p>${esc(b.body)}</p></article>`).join('')||'<div class="mini-row"><p>还没有晨报素材。可在信息流点击“生成晨报点”。</p></div>'}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>收藏夹</h3><span>${state.saved.length}</span></div><div class="mini-list">${state.saved.map(id=>data.items.find(i=>i.id===id)).filter(Boolean).map(i=>`<div class="mini-row"><header><strong>${esc(i.title)}</strong><em>${esc(i.category)}</em></header><p>${esc(i.source_name)}</p></div>`).join('')||'<div class="mini-row"><p>暂无收藏。</p></div>'}</div></div></aside></section><section class="panel"><div class="panel-head"><h3>生成结果</h3><span>output</span></div><div class="feed"><div class="output" id="toolOutput">选择一个专业工具运行。</div></div></section>`;qs('view-workspace').querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{const tool=authPayload.pro_tools.find(t=>t.id===b.dataset.tool);const picked=data.items.slice(0,3).map(i=>`- ${i.title}（${i.source_name}）`).join('\\n');qs('toolOutput').textContent=`${tool.name}输出\\n\\n输入：${tool.inputs.join(' / ')}\\n\\n今日重点：\\n${picked}\\n\\n顾问建议：结合客户行业建立机会、风险、待确认问题三栏，并保留原文链接。`;toast('工具已运行',`${tool.name}生成了结果。`)});qs('addSub').onclick=()=>{const pool=['外资','财政','能源','价格','制造业','民营经济'];const next=pool.find(x=>!state.subscriptions.includes(x))||('专题'+Date.now());state.subscriptions.push(next);save();renderWorkspace()}}
    function renderAdmin(){const health=data.sources.reduce((a,s)=>{a[s.status]=(a[s.status]||0)+1;return a},{});qs('view-admin').innerHTML=hero(UI.adminTitle,UI.adminSub,'ADMIN')+`<section class="grid"><div class="panel"><div class="panel-head"><h3>信源运行</h3><span>${data.sources.length} sources</span></div><div class="source-list">${data.sources.map(s=>`<div class="source-row ${esc(s.status)}"><header><strong>${esc(s.name)}</strong><em>${esc(s.status)}</em></header><p>${esc(s.category)} · ${esc(s.items)} 条 · ${esc(s.url)}</p></div>`).join('')}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>状态统计</h3><span>health</span></div><div class="admin-grid" style="grid-template-columns:1fr">${Object.entries(health).map(([k,v])=>`<div class="admin-card"><header><strong>${esc(k)}</strong><em>${v}</em></header><p>本次采集状态。</p></div>`).join('')}</div></div><div class="panel"><div class="panel-head"><h3>下一批工程</h3><span>next</span></div><div class="mini-list"><div class="mini-row"><p>接入交易所/巨潮 API，用于年报、公告和公司动向。</p></div><div class="mini-row"><p>补充券商研报、投资机构观点和咨询公司公开洞察。</p></div><div class="mini-row"><p>搭建后端定时采集、去重、摘要和权限系统。</p></div></div></div></aside></section>`}
    function render(){updateProfile(); if(state.view==='home')renderHome(); if(state.view==='feed')renderFeed(); if(state.view==='spaces')renderSpaces(); if(state.view==='zhigeng')renderZhigeng(); if(state.view==='workspace')renderWorkspace(); if(state.view==='admin')renderAdmin();}
    renderNav(); render();
  </script>
</body>
</html>
"""
    html = html.replace("__DATA__", js_json(public_data)).replace("__SPACES__", js_json(industry_data)).replace("__AUTH__", js_json(auth_data)).replace("__UI__", js_json(build_ui()))
    APP_DIR.mkdir(exist_ok=True)
    (APP_DIR / "index.html").write_text(html, encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    public_data = collect_public_data()
    industry_data = build_industry_data(public_data)
    auth_data = build_auth_data(industry_data)
    (OUTPUT_DIR / "bailing-public-data.json").write_text(json.dumps(public_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "bailing-industry-spaces-data.json").write_text(json.dumps(industry_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "zhigeng-auth-workspace-data.json").write_text(json.dumps(auth_data, ensure_ascii=False, indent=2), encoding="utf-8")
    render_app(public_data, industry_data, auth_data)
    print(json.dumps({"items": public_data["item_count"], "sources": len(public_data["sources"]), "ok": sum(1 for s in public_data["sources"] if s["status"] == "ok"), "app": str(APP_DIR / "index.html")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
