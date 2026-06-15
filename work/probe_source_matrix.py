import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "source-probe-report.json"


SOURCE_MATRIX = [
    # Central government and macro
    ("gov-policy-latest", "国务院最新政策", "国家政策", "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json"),
    ("gov-news-important", "中国政府网要闻", "国家政策", "https://www.gov.cn/xinwen/yaowen/"),
    ("gov-policy-policyfiles", "中国政府网政策文件", "国家政策", "https://www.gov.cn/zhengce/zhengcewenjianku/"),
    ("ndrc-news", "国家发改委新闻发布", "国家政策", "https://www.ndrc.gov.cn/xwdt/xwfb/"),
    ("ndrc-policy-orders", "国家发改委政策发布", "国家政策", "https://www.ndrc.gov.cn/xxgk/zcfb/fzggwl/"),
    ("ndrc-policy-notices", "国家发改委通知", "国家政策", "https://www.ndrc.gov.cn/xxgk/zcfb/tz/"),
    ("ndrc-policy-announcements", "国家发改委公告", "国家政策", "https://www.ndrc.gov.cn/xxgk/zcfb/gg/"),
    ("stats-release", "国家统计局数据发布", "宏观数据", "https://www.stats.gov.cn/sj/zxfb/"),
    ("stats-news", "国家统计局统计新闻", "宏观数据", "https://www.stats.gov.cn/xw/tjxw/"),
    # Finance and regulators
    ("mof-news", "财政部财政新闻", "财政金融", "https://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/"),
    ("mof-policy", "财政部政策发布", "财政金融", "https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/"),
    ("pbc-news", "人民银行工作动态", "财政金融", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html"),
    ("pbc-policy", "人民银行货币政策", "财政金融", "https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/index.html"),
    ("csrc-news", "证监会要闻", "财政金融", "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml"),
    ("csrc-press", "证监会新闻发布", "财政金融", "http://www.csrc.gov.cn/csrc/c100029/common_list.shtml"),
    ("nfra-news", "金融监管总局要闻", "财政金融", "https://www.nfra.gov.cn/cn/view/pages/index/index.html"),
    # Industry ministries and regulators
    ("miit-policy", "工信部文件发布", "产业监管", "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html"),
    ("miit-news", "工信部司局动态", "产业监管", "https://www.miit.gov.cn/xwdt/gxdt/sjdt/index.html"),
    ("mofcom-policy", "商务部政策发布", "外贸外资", "https://www.mofcom.gov.cn/zwgk/zcfb/"),
    ("mofcom-news", "商务部新闻发布", "外贸外资", "https://www.mofcom.gov.cn/xwfb/"),
    ("samr-news", "市场监管总局新闻", "产业监管", "https://www.samr.gov.cn/xw/zj/"),
    ("samr-policy", "市场监管总局政策", "产业监管", "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/"),
    ("sasac-policy", "国资委政策", "国企央企", "http://www.sasac.gov.cn/n2588035/n2588320/index.html"),
    ("sasac-news", "国资委新闻", "国企央企", "http://www.sasac.gov.cn/n2588025/index.html"),
    ("customs-news", "海关总署新闻", "外贸外资", "http://www.customs.gov.cn/customs/302249/302266/302267/index.html"),
    ("moa-news", "农业农村部新闻", "农业农村", "http://www.moa.gov.cn/xw/zwdt/"),
    ("mnr-news", "自然资源部新闻", "资源环境", "https://www.mnr.gov.cn/dt/ywbb/"),
    ("mee-news", "生态环境部新闻", "资源环境", "https://www.mee.gov.cn/ywdt/"),
    ("nea-news", "国家能源局新闻", "能源", "https://www.nea.gov.cn/xwzx/nyyw.htm"),
    # Local policy entry points
    ("beijing-policy", "北京市政府政策文件", "地方政策", "https://www.beijing.gov.cn/zhengce/zhengcefagui/"),
    ("shanghai-policy", "上海市政府政策文件", "地方政策", "https://www.shanghai.gov.cn/nw12344/index.html"),
    ("guangdong-policy", "广东省政府政策文件", "地方政策", "https://www.gd.gov.cn/zwgk/wjk/"),
    ("zhejiang-policy", "浙江省政府政策文件", "地方政策", "https://www.zj.gov.cn/col/col1229019364/index.html"),
    ("jiangsu-policy", "江苏省政府政策文件", "地方政策", "https://www.jiangsu.gov.cn/col/col64797/index.html"),
    ("shandong-policy", "山东省政府政策文件", "地方政策", "http://www.shandong.gov.cn/col/col107851/index.html"),
    ("sichuan-policy", "四川省政府政策文件", "地方政策", "https://www.sc.gov.cn/10462/zfwjts/zfwj.shtml"),
    ("hubei-policy", "湖北省政府政策文件", "地方政策", "https://www.hubei.gov.cn/zfwj/"),
    ("anhui-policy", "安徽省政府政策文件", "地方政策", "https://www.ah.gov.cn/public/column/1681?type=4&action=list"),
    # Capital market and company announcements
    ("sse-announcements", "上交所上市公司公告", "公司公告", "https://www.sse.com.cn/disclosure/listedinfo/announcement/"),
    ("szse-announcements", "深交所上市公司公告", "公司公告", "https://www.szse.cn/disclosure/listed/notice/index.html"),
    ("bse-announcements", "北交所上市公司公告", "https://www.bse.cn/disclosure/announcement.html", "公司公告"),
    ("cninfo", "巨潮资讯公告", "公司公告", "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search"),
    # Industry media candidates
    ("36kr-news", "36氪快讯", "产业媒体", "https://36kr.com/newsflashes"),
    ("thepaper-finance", "澎湃财经", "产业媒体", "https://www.thepaper.cn/channel_25950"),
]


def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 BailingProbe/1.0",
        "Accept": "text/html,application/json,application/xhtml+xml",
        "Referer": "https://www.gov.cn/",
    })
    with urlopen(req, timeout=12) as resp:
        raw = resp.read(400000)
        ct = resp.headers.get("content-type", "")
        final = resp.geturl()
    for enc in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return raw.decode(enc), ct, final
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), ct, final


def classify(text, ct, error=None):
    if error:
        if "HTTP Error 412" in error or "HTTP Error 403" in error:
            return "blocked_or_headers"
        if "timed out" in error:
            return "timeout"
        return "error"
    if "application/json" in ct:
        return "json_candidate"
    dates = len(re.findall(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}", text))
    lis = len(re.findall(r"<li\b", text, re.I))
    anchors = len(re.findall(r"<a\b", text, re.I))
    if dates >= 5 and (lis >= 5 or anchors >= 20):
        return "direct_parse_candidate"
    if anchors >= 20 and dates >= 1:
        return "adapter_candidate"
    if len(text) < 8000 and anchors < 5:
        return "dynamic_shell"
    return "needs_review"


def main():
    results = []
    for row in SOURCE_MATRIX:
        if len(row) != 4:
            # tolerate accidentally swapped fields
            sid, name, url, category = row
        else:
            sid, name, category, url = row
        started = datetime.now()
        try:
            text, ct, final = fetch(url)
            title = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
            title_text = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
            status = classify(text, ct)
            error = ""
        except Exception as exc:
            text, ct, final, title_text = "", "", url, ""
            status = classify("", "", str(exc))
            error = str(exc)
        results.append({
            "id": sid,
            "name": name,
            "category": category,
            "url": url,
            "final_url": final,
            "status": status,
            "title": title_text,
            "content_type": ct,
            "date_count": len(re.findall(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}", text)),
            "li_count": len(re.findall(r"<li\b", text, re.I)),
            "anchor_count": len(re.findall(r"<a\b", text, re.I)),
            "length": len(text),
            "latency_ms": int((datetime.now() - started).total_seconds() * 1000),
            "error": error,
        })
        print(f"{name}: {status}")
    OUT.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
