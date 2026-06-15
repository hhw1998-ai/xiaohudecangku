import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
DATA_PATH = OUTPUT_DIR / "bailing-public-data.json"
OUT_PATH = OUTPUT_DIR / "bailing-public-mvp.html"


def h(value):
    return escape(str(value or ""), quote=True)


def source_class(category):
    if category == "国家政策":
        return "policy"
    if category == "财政金融":
        return "finance"
    return "data"


def status_label(status):
    return {
        "ok": "已接入",
        "empty": "待微调",
        "error": "异常",
        "needs_adapter": "待适配",
        "manual_or_authorized": "候选",
    }.get(status, status)


def item_card(item):
    tags = "".join(f"<span class=\"tag\">{h(tag)}</span>" for tag in item.get("tags", []))
    return f"""
      <article class="feed-item">
        <div class="time">{h(item.get("published_at", "")[5:])}</div>
        <div class="rail-dot {source_class(item.get("category"))}"></div>
        <div class="news-card" data-category="{h(item.get("category"))}" data-source="{h(item.get("source_name"))}">
          <div class="news-meta">
            <span class="source-pill {source_class(item.get("category"))}">{h(item.get("category"))}</span>
            <span>{h(item.get("source_name"))}</span>
            <span class="score">{h(item.get("score"))}</span>
          </div>
          <a class="news-title" href="{h(item.get("url"))}" target="_blank" rel="noopener noreferrer">{h(item.get("title"))}</a>
          <div class="tags">{tags}</div>
          <div class="value-grid">
            <div><span>顾问场景</span><b>{h(item.get("scene"))}</b></div>
            <div><span>公众价值</span><b>{h(item.get("public_value"))}</b></div>
          </div>
          <p class="consulting-value">{h(item.get("consulting_value"))}</p>
        </div>
      </article>
    """


def source_row(source):
    return f"""
      <div class="source-row {h(source.get("status"))}">
        <div>
          <strong>{h(source.get("name"))}</strong>
          <small>{h(source.get("category", "候选源"))} · {h(source.get("mode", "adapter"))}</small>
        </div>
        <a href="{h(source.get("url"))}" target="_blank" rel="noopener noreferrer">{status_label(source.get("status"))}</a>
        <em>{h(source.get("items", 0))} 条</em>
      </div>
    """


def candidate_row(source):
    return f"""
      <div class="candidate-row">
        <strong>{h(source.get("name"))}</strong>
        <span>{status_label(source.get("status"))}</span>
        <p>{h(source.get("reason"))}</p>
      </div>
    """


def render():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    items = data.get("items", [])
    sources = data.get("sources", [])
    candidates = data.get("candidate_sources", [])
    counts = Counter(item.get("category") for item in items)
    source_counts = Counter(source.get("status") for source in sources)
    latest = max((item.get("published_at", "") for item in items), default="")
    cards = "".join(item_card(item) for item in items)
    source_rows = "".join(source_row(source) for source in sources)
    candidate_rows = "".join(candidate_row(source) for source in candidates)
    top_items = sorted(items, key=lambda item: item.get("score", 0), reverse=True)[:5]
    brief_lines = "".join(
        f"<li><b>{h(item.get('category'))}</b><a href=\"{h(item.get('url'))}\" target=\"_blank\" rel=\"noopener noreferrer\">{h(item.get('title'))}</a></li>"
        for item in top_items
    )
    generated = h(data.get("generated_at") or datetime.now().isoformat(timespec="seconds"))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>百灵公开版 MVP</title>
  <style>
    :root {{
      --bg:#f7f8f4;--surface:#ffffff;--soft:#f0f3ed;--ink:#171a17;--muted:#62685f;--weak:#92998f;
      --line:#dce2d7;--line-strong:#bcc8b9;--green:#22765f;--green-soft:#e5f2ed;--red:#b94e3f;
      --red-soft:#f7e8e4;--blue:#2c6f9e;--blue-soft:#e5f0f7;--gold:#9c6d1f;--gold-soft:#f3ead7;
      --nav:#1d261f;--shadow:0 14px 34px rgba(34,46,36,.08);--radius:8px;
      --mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;--sans:Inter,"PingFang SC","Microsoft YaHei",Arial,sans-serif;
    }}
    *{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:var(--sans);letter-spacing:0}}a{{color:inherit;text-decoration:none}}
    button,input{{font:inherit}}.app{{min-height:100vh;display:grid;grid-template-columns:248px minmax(0,1fr)}}.side{{position:sticky;top:0;height:100vh;background:var(--nav);color:#f6f3e9;padding:20px 14px;display:flex;flex-direction:column;gap:18px}}
    .brand{{padding:0 10px 14px;border-bottom:1px solid rgba(255,255,255,.12)}}.brand-main{{display:flex;align-items:center;gap:10px}}.mark{{width:34px;height:34px;border-radius:8px;display:grid;place-items:center;background:#d7efe6;color:#163a2d;font-weight:900;font-size:18px}}
    .brand h1{{margin:0;font-size:21px;line-height:1}}.brand p{{margin:7px 0 0;color:rgba(246,243,233,.62);font-size:12px;line-height:1.55}}.nav{{display:grid;gap:6px}}.nav-label{{padding:0 10px;color:rgba(246,243,233,.45);font:11px var(--mono)}}.nav button{{height:40px;border:0;border-radius:8px;background:transparent;color:rgba(246,243,233,.74);text-align:left;padding:0 10px;cursor:pointer;display:flex;align-items:center;gap:10px}}.nav button.active,.nav button:hover{{background:rgba(255,255,255,.08);color:#fff}}.nav i{{width:10px;height:10px;border-radius:999px;background:var(--green)}}.nav i.policy{{background:var(--red)}}.nav i.finance{{background:var(--gold)}}.grow{{flex:1}}.zhigeng{{border:1px solid rgba(255,255,255,.14);border-radius:8px;background:rgba(255,255,255,.06);padding:12px}}.zhigeng b{{display:block;font-size:14px}}.zhigeng span{{display:inline-flex;margin-top:8px;border:1px solid rgba(215,239,230,.28);border-radius:999px;padding:4px 8px;color:#d7efe6;font-size:11px}}.zhigeng p{{margin:9px 0 0;color:rgba(246,243,233,.64);font-size:12px;line-height:1.55}}
    .main{{padding:20px 24px 38px;min-width:0;display:grid;gap:16px}}.hero{{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:16px;align-items:stretch}}.hero-copy{{padding:22px 0}}.eyebrow{{margin:0 0 9px;color:var(--green);font:700 12px var(--mono)}}.hero h2{{margin:0;font-size:34px;line-height:1.16}}.hero p{{max-width:760px;margin:11px 0 0;color:var(--muted);font-size:14px;line-height:1.75}}.metrics{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}.metric{{padding:13px;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:var(--shadow)}}.metric span{{display:block;color:var(--muted);font-size:12px}}.metric b{{display:block;margin-top:7px;font:900 26px/1 var(--mono)}}.metric small{{display:block;margin-top:5px;color:var(--weak);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .toolbar{{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--surface)}}.search{{height:38px;min-width:min(470px,100%);flex:1 1 430px;display:flex;align-items:center;gap:8px;padding:0 11px;border:1px solid var(--line);border-radius:8px;background:var(--soft)}}.search input{{width:100%;min-width:0;border:0;outline:0;background:transparent}}.chips{{display:flex;gap:6px;flex-wrap:wrap}}.chip{{height:34px;border:1px solid var(--line);border-radius:999px;background:var(--surface);padding:0 12px;color:var(--muted);font-size:12px;cursor:pointer}}.chip.active{{border-color:rgba(34,118,95,.35);background:var(--green-soft);color:var(--green);font-weight:800}}
    .grid{{display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:16px;align-items:start}}.panel{{border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}}.panel-head{{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line);background:#fbfcfa}}.panel-head h3{{margin:0;font-size:15px}}.panel-head span{{color:var(--weak);font:11px var(--mono);white-space:nowrap}}
    .timeline{{--time:74px;padding:14px 0}}.feed-item{{position:relative;display:grid;grid-template-columns:var(--time) 24px minmax(0,1fr);padding:0 16px 10px}}.feed-item:before{{content:"";position:absolute;top:0;bottom:0;left:calc(16px + var(--time) + 12px);width:1px;background:var(--line)}}.time{{padding:17px 8px 0 0;text-align:right;color:var(--muted);font:800 13px var(--mono)}}.rail-dot{{position:relative;z-index:1;justify-self:center;margin-top:21px;width:8px;height:8px;border-radius:999px;background:var(--blue);box-shadow:0 0 0 3px var(--surface)}}.rail-dot.policy{{background:var(--red)}}.rail-dot.finance{{background:var(--gold)}}.news-card{{min-width:0;border:1px solid var(--line);border-radius:8px;padding:13px 14px;background:var(--surface);transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease}}.news-card:hover{{transform:translateY(-1px);border-color:var(--line-strong);box-shadow:0 12px 28px rgba(34,46,36,.1)}}.news-meta{{display:flex;align-items:center;gap:8px;min-width:0;margin-bottom:8px;color:var(--muted);font-size:12px}}.news-meta span:nth-child(2){{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.source-pill{{flex:0 0 auto;display:inline-flex;align-items:center;min-height:22px;padding:0 7px;border-radius:999px;background:var(--blue-soft);color:var(--blue);font-weight:800}}.source-pill.policy{{background:var(--red-soft);color:var(--red)}}.source-pill.finance{{background:var(--gold-soft);color:var(--gold)}}.score{{margin-left:auto;font:800 11px var(--mono);color:var(--green);border:1px solid var(--line);border-radius:999px;padding:3px 7px;background:#fbfcfa}}.news-title{{display:block;font-size:15px;font-weight:900;line-height:1.45}}.news-title:hover{{color:var(--green)}}.tags{{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}}.tag{{display:inline-flex;align-items:center;min-height:22px;padding:0 7px;border-radius:4px;background:var(--soft);color:#4f584e;font:11px var(--mono)}}.value-grid{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:10px}}.value-grid div{{min-width:0;border:1px dashed var(--line);border-radius:6px;background:#fbfcfa;padding:8px}}.value-grid span{{display:block;color:var(--weak);font-size:11px}}.value-grid b{{display:block;margin-top:4px;font-size:12px;line-height:1.45}}.consulting-value{{margin:10px 0 0;padding:9px 10px;border-radius:6px;background:var(--green-soft);color:#245b47;font-size:12px;line-height:1.65}}
    .side-stack{{display:grid;gap:16px}}.morning{{padding:12px 16px 16px}}.morning ol{{margin:0;padding-left:18px;display:grid;gap:10px}}.morning li{{font-size:13px;line-height:1.5}}.morning b{{display:inline-flex;margin-right:6px;color:var(--green)}}.morning a:hover{{color:var(--green)}}.source-list,.candidate-list{{display:grid;gap:8px;padding:12px}}.source-row{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 8px;padding:10px;border:1px solid var(--line);border-radius:8px;background:#fbfcfa}}.source-row strong{{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}}.source-row small{{display:block;margin-top:4px;color:var(--weak);font-size:11px}}.source-row a{{align-self:start;border-radius:999px;border:1px solid rgba(34,118,95,.25);background:var(--green-soft);color:var(--green);padding:4px 8px;font-size:11px;white-space:nowrap}}.source-row.empty a{{border-color:rgba(156,109,31,.25);background:var(--gold-soft);color:var(--gold)}}.source-row.error a{{border-color:rgba(185,78,63,.25);background:var(--red-soft);color:var(--red)}}.source-row em{{grid-column:1/-1;color:var(--muted);font-style:normal;font:12px var(--mono)}}.candidate-row{{padding:10px;border:1px dashed var(--line);border-radius:8px;background:#fbfcfa}}.candidate-row strong{{font-size:13px}}.candidate-row span{{float:right;color:var(--gold);font-size:11px;font-weight:800}}.candidate-row p{{clear:both;margin:7px 0 0;color:var(--muted);font-size:12px;line-height:1.55}}.empty-note{{display:none;padding:28px;color:var(--muted);text-align:center}}
    @media(max-width:1160px){{.hero,.grid{{grid-template-columns:1fr}}.side-stack{{grid-template-columns:repeat(2,minmax(0,1fr))}}.side-stack .panel:first-child{{grid-column:1/-1}}}}
    @media(max-width:820px){{.app{{grid-template-columns:1fr}}.side{{position:relative;height:auto}}.main{{padding:16px 14px 34px}}.hero h2{{font-size:28px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.side-stack{{grid-template-columns:1fr}}.timeline{{--time:56px}}.feed-item{{grid-template-columns:var(--time) 22px minmax(0,1fr);padding-left:10px;padding-right:10px}}.feed-item:before{{left:calc(10px + var(--time) + 11px)}}.time{{font-size:12px}}.value-grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="side">
      <div class="brand">
        <div class="brand-main"><div class="mark">百</div><h1>百灵</h1></div>
        <p>面向公众和企业经营者的政策、宏观、产业信息聚合入口。</p>
      </div>
      <nav class="nav" aria-label="分类筛选">
        <div class="nav-label">PUBLIC FEED</div>
        <button class="active" data-filter="全部"><i></i>全部信息</button>
        <button data-filter="国家政策"><i class="policy"></i>国家政策</button>
        <button data-filter="宏观数据"><i></i>宏观数据</button>
        <button data-filter="财政金融"><i class="finance"></i>财政金融</button>
      </nav>
      <div class="grow"></div>
      <section class="zhigeng">
        <b>知更 · 顾问专业层</b>
        <span>认证功能预留</span>
        <p>后续承接登录、行业空间、客户晨报、专题追踪、深度摘要和顾问工作流。</p>
      </section>
    </aside>
    <main class="main">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">BAILING PUBLIC MVP-1</p>
          <h2>把权威政策、宏观数据和财政金融动态收进一个可验证的信息流。</h2>
          <p>这一版先跑通公开权威源的采集、去重、分类、价值判断和原文跳转。它既能给普通用户看大势，也为后续“知更”顾问认证层打底。</p>
        </div>
        <div class="metrics">
          <div class="metric"><span>真实采集条目</span><b>{len(items)}</b><small>来自公开网页或公开 JSON</small></div>
          <div class="metric"><span>已接入源</span><b>{source_counts.get("ok", 0)}</b><small>{len(sources)} 个源在监测</small></div>
          <div class="metric"><span>国家政策</span><b>{counts.get("国家政策", 0)}</b><small>国务院、发改委等</small></div>
          <div class="metric"><span>最新日期</span><b style="font-size:21px">{h(latest[5:])}</b><small>生成时间 {generated}</small></div>
        </div>
      </section>
      <section class="toolbar" aria-label="筛选工具栏">
        <label class="search"><span>搜索</span><input id="searchInput" type="search" placeholder="输入政策、行业、机构、关键词" /></label>
        <div class="chips">
          <button class="chip active" data-filter="全部">全部</button>
          <button class="chip" data-filter="国家政策">国家政策</button>
          <button class="chip" data-filter="宏观数据">宏观数据</button>
          <button class="chip" data-filter="财政金融">财政金融</button>
        </div>
      </section>
      <section class="grid">
        <section class="panel">
          <div class="panel-head"><h3>百灵实时信息流</h3><span>public source feed</span></div>
          <div class="timeline" id="timeline">{cards}<div class="empty-note" id="emptyNote">没有匹配的信息</div></div>
        </section>
        <aside class="side-stack">
          <section class="panel">
            <div class="panel-head"><h3>今日晨报候选</h3><span>知更预览</span></div>
            <div class="morning"><ol>{brief_lines}</ol></div>
          </section>
          <section class="panel">
            <div class="panel-head"><h3>信源健康度</h3><span>{source_counts.get("ok", 0)} ok</span></div>
            <div class="source-list">{source_rows}</div>
          </section>
          <section class="panel">
            <div class="panel-head"><h3>下一批信源队列</h3><span>adapter backlog</span></div>
            <div class="candidate-list">{candidate_rows}</div>
          </section>
        </aside>
      </section>
    </main>
  </div>
  <script>
    const cards = Array.from(document.querySelectorAll(".news-card"));
    const buttons = Array.from(document.querySelectorAll("[data-filter]"));
    const searchInput = document.getElementById("searchInput");
    const emptyNote = document.getElementById("emptyNote");
    let currentFilter = "全部";
    function applyFilters() {{
      const query = searchInput.value.trim().toLowerCase();
      let visible = 0;
      cards.forEach((card) => {{
        const item = card.closest(".feed-item");
        const category = card.dataset.category;
        const okCategory = currentFilter === "全部" || category === currentFilter;
        const okQuery = !query || card.textContent.toLowerCase().includes(query);
        const show = okCategory && okQuery;
        item.style.display = show ? "grid" : "none";
        if (show) visible += 1;
      }});
      emptyNote.style.display = visible ? "none" : "block";
    }}
    buttons.forEach((button) => {{
      button.addEventListener("click", () => {{
        currentFilter = button.dataset.filter || "全部";
        buttons.forEach((b) => b.classList.toggle("active", b.dataset.filter === currentFilter));
        applyFilters();
      }});
    }});
    searchInput.addEventListener("input", applyFilters);
  </script>
</body>
</html>
"""
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    render()
