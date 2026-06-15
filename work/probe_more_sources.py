import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "more-source-probe.json"


SOURCES = [
    ("miit-policy", "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html"),
    ("miit-news", "https://www.miit.gov.cn/xwdt/gxdt/sjdt/index.html"),
    ("samr-news", "https://www.samr.gov.cn/xw/zj/"),
    ("samr-policy", "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/"),
    ("sasac-news", "http://www.sasac.gov.cn/n2588025/index.html"),
    ("sasac-policy", "http://www.sasac.gov.cn/n2588035/n2588320/index.html"),
    ("nea-news", "https://www.nea.gov.cn/xwzx/nyyw.htm"),
    ("customs-news", "http://www.customs.gov.cn/customs/302249/302266/302267/index.html"),
    ("zhejiang-policy", "https://www.zj.gov.cn/col/col1229019364/index.html"),
    ("jiangsu-policy", "https://www.jiangsu.gov.cn/col/col64797/index.html"),
    ("sichuan-policy", "https://www.sc.gov.cn/10462/zfwjts/zfwj.shtml"),
    ("hubei-policy", "https://www.hubei.gov.cn/zfwj/"),
    ("anhui-policy", "https://www.ah.gov.cn/public/column/1681?type=4&action=list"),
    ("sse-announcements", "https://www.sse.com.cn/disclosure/listedinfo/announcement/"),
    ("szse-announcements", "https://www.szse.cn/disclosure/listed/notice/index.html"),
    ("cninfo", "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search"),
    ("mckinsey-cn", "https://www.mckinsey.com.cn/insights/"),
    ("bcg-cn", "https://www.bcg.com/zh-cn/publications"),
    ("deloitte-cn", "https://www2.deloitte.com/cn/zh/insights.html"),
    ("pwc-cn", "https://www.pwccn.com/zh/research-and-insights.html"),
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
                self.links.append({"title": title[:120], "href": href})
            self.current = None


def clean(value):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 BailingProbe/2.0",
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Referer": "https://www.gov.cn/",
    })
    with urlopen(req, timeout=15) as resp:
        raw = resp.read(600000)
        ct = resp.headers.get("content-type", "")
        final = resp.geturl()
    for enc in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return raw.decode(enc), ct, final
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), ct, final


def main():
    rows = []
    for sid, url in SOURCES:
        try:
            html, ct, final = fetch(url)
            parser = LinkParser()
            parser.feed(html)
            dated = re.findall(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}", html)
            rows.append({
                "id": sid,
                "url": url,
                "final": final,
                "status": "ok",
                "content_type": ct,
                "size": len(html),
                "links": len(parser.links),
                "dates": len(dated),
                "samples": parser.links[:8],
            })
        except Exception as exc:
            rows.append({"id": sid, "url": url, "status": "error", "error": str(exc)})
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
