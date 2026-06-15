import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
DATA_PATH = OUTPUT_DIR / "consulting-radar-live-data.json"
OUT_PATH = OUTPUT_DIR / "consulting-radar-live.html"


def h(value):
    return escape(str(value or ""), quote=True)


def card(item):
    tags = "".join(f"<span class=\"tag\">{h(tag)}</span>" for tag in item.get("tags", []))
    return f"""
      <article class="item">
        <div class="time">{h(item.get("published_at", "")[5:])}</div>
        <div class="dot"></div>
        <div class="card" data-category="{h(item["category"])}">
          <div class="card-head">
            <div class="source"><span class="source-type {source_class(item)}"></span><span class="source-name">{h(item["source_name"])}</span></div>
            <div class="score">{h(item["score"])}</div>
          </div>
          <a class="card-title" href="{h(item["url"])}" target="_blank" rel="noopener noreferrer">{h(item["title"])}</a>
          <p class="summary">真实采集：{h(item["source_name"])} 于 {h(item["published_at"])} 发布。系统已根据标题初步识别标签、咨询场景和顾问价值。</p>
          <div class="tags">{tags}</div>
          <div class="intel-meta">
            <div class="intel-field"><span>咨询场景</span><b>{h(item["consulting_scene"])}</b></div>
            <div class="intel-field"><span>采集方式</span><b>{h(item["ingestion"])}</b></div>
            <div class="intel-field"><span>原文状态</span><b>已保留链接</b></div>
          </div>
          <div class="reason"><b>咨询价值：</b>{h(item["consulting_value"])}</div>
        </div>
      </article>
    """


def source_class(item):
    if item["category"] == "政策":
        return "policy"
    if item["category"] == "行业":
        return ""
    return "company"


def render():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    items = data["items"]
    counts = Counter(item["category"] for item in items)
    latest = max((item["published_at"] for item in items), default="")
    source_rows = "".join(
        f"""
        <div class="source-row">
          <strong>{h(source["name"])}</strong><span class="badge auto">{h(source["status"])}</span>
          <small>{h(source["url"])} · {h(source.get("items", 0))} 条 · 解析提示 {h(source.get("selector_hint", "-"))}</small>
        </div>
        """
        for source in data["sources"]
    )
    cards = "".join(card(item) for item in items)
    generated = data.get("generated_at", "")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Consulting Radar Live</title>
  <style>
    :root {{
      --bg:#f6f5f1;--panel:#fff;--panel-soft:#faf9f5;--ink:#171717;--muted:#67645d;--weak:#9b9589;
      --line:#ddd8ce;--line-strong:#c8c0b3;--nav:#20241f;--nav-soft:#2b3029;--teal:#087f7b;
      --teal-soft:#e4f3ef;--amber:#b87308;--amber-soft:#fff1d6;--red:#b84538;--red-soft:#fae7e3;
      --green-soft:#e6f1e8;--shadow:0 10px 30px rgba(54,45,30,.08);--radius:8px;
      --mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;--sans:Inter,"PingFang SC","Microsoft YaHei",Arial,sans-serif;
    }}
    *{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:var(--sans);letter-spacing:0}}
    a{{color:inherit;text-decoration:none}}button,input{{font:inherit}}.app{{min-height:100vh;display:grid;grid-template-columns:232px minmax(0,1fr)}}
    .sidebar{{position:sticky;top:0;height:100vh;padding:20px 14px;background:var(--nav);color:#f7f3e8;display:flex;flex-direction:column;gap:18px}}
    .brand{{display:grid;gap:3px;padding:0 10px 12px;border-bottom:1px solid rgba(255,255,255,.12)}}.brand-title{{display:flex;align-items:center;gap:8px;font-weight:800;font-size:18px}}
    .brand-mark{{width:26px;height:26px;border:1px solid rgba(255,255,255,.35);border-radius:6px;display:grid;place-items:center;color:#8de1d2;font-family:var(--mono);font-size:12px;font-weight:800}}
    .brand-sub{{color:rgba(247,243,232,.58);font-size:12px;line-height:1.5}}.nav-group{{display:grid;gap:4px}}.nav-label{{padding:0 10px 4px;color:rgba(247,243,232,.42);font-size:11px;font-family:var(--mono)}}
    .nav-link{{border:0;width:100%;display:flex;align-items:center;gap:10px;min-height:40px;padding:0 10px;border-radius:8px;background:transparent;color:rgba(247,243,232,.74);cursor:pointer;text-align:left}}
    .nav-link:hover,.nav-link.active{{background:var(--nav-soft);color:#fff}}.nav-icon{{width:18px;height:18px;display:inline-grid;place-items:center;color:#8de1d2}}.nav-spacer{{flex:1}}
    .nav-note{{padding:12px;border:1px solid rgba(255,255,255,.12);border-radius:var(--radius);background:rgba(255,255,255,.05);color:rgba(247,243,232,.68);font-size:12px;line-height:1.55}}
    .main{{min-width:0;padding:20px 24px 36px;display:grid;gap:16px}}.topbar{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:start}}
    .title-block h1{{margin:0;font-size:26px;line-height:1.2}}.title-block p{{margin:7px 0 0;color:var(--muted);font-size:13px;line-height:1.6}}
    .status-strip{{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:8px}}.metric{{min-width:0;padding:10px 12px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);box-shadow:var(--shadow)}}
    .metric-label{{color:var(--muted);font-size:11px;line-height:1.2}}.metric-value{{margin-top:5px;font-family:var(--mono);font-size:22px;font-weight:800;line-height:1}}
    .toolbar{{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel)}}
    .search{{min-width:min(420px,100%);flex:1 1 420px;display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:8px;padding:0 11px;height:38px;background:var(--panel-soft)}}
    .search input{{min-width:0;width:100%;border:0;outline:0;background:transparent;color:var(--ink)}}.filters{{display:flex;gap:6px;flex-wrap:wrap}}
    .chip{{border:1px solid var(--line);border-radius:999px;background:var(--panel-soft);color:var(--muted);height:34px;padding:0 12px;cursor:pointer;font-size:12px}}.chip.active{{border-color:rgba(8,127,123,.35);background:var(--teal-soft);color:var(--teal);font-weight:700}}
    .content-grid{{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:16px;align-items:start}}.panel{{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);box-shadow:var(--shadow);overflow:hidden}}
    .panel-head{{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line);background:var(--panel-soft)}}.panel-title{{margin:0;font-size:15px;line-height:1.2}}.panel-sub{{color:var(--weak);font-family:var(--mono);font-size:11px;white-space:nowrap}}
    .timeline{{--time:82px;display:grid;padding:14px 0}}.day{{display:grid;grid-template-columns:var(--time) 26px minmax(0,1fr);align-items:center;padding:8px 16px}}.day-date{{text-align:right;padding-right:8px;color:var(--muted);font-size:12px;font-weight:700}}.day-line{{height:1px;background:var(--line-strong)}}
    .item{{position:relative;display:grid;grid-template-columns:var(--time) 26px minmax(0,1fr);padding:0 16px 10px}}.item::before{{content:"";position:absolute;top:0;bottom:0;left:calc(16px + var(--time) + 13px);width:1px;background:var(--line)}}
    .time{{padding:17px 8px 0 0;text-align:right;font-family:var(--mono);font-size:14px;font-weight:800;color:var(--ink)}}.dot{{position:relative;z-index:1;justify-self:center;margin-top:21px;width:8px;height:8px;border-radius:999px;background:var(--teal);box-shadow:0 0 0 3px var(--panel)}}
    .card{{min-width:0;padding:13px 14px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);transition:border-color .16s ease,transform .16s ease,box-shadow .16s ease}}.card:hover{{border-color:var(--line-strong);transform:translateY(-1px);box-shadow:0 12px 28px rgba(54,45,30,.1)}}
    .card-head{{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px}}.source{{min-width:0;display:flex;align-items:center;gap:7px;color:var(--muted);font-size:12px}}.source-name{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.source-type{{flex:0 0 auto;width:7px;height:7px;border-radius:999px;background:var(--teal)}}.source-type.policy{{background:var(--red)}}
    .score{{flex:0 0 auto;display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border:1px solid var(--line);border-radius:999px;background:var(--panel-soft);color:var(--teal);font-family:var(--mono);font-size:11px;font-weight:800}}
    .card-title{{display:block;font-size:15px;font-weight:800;line-height:1.45}}.card-title:hover{{color:var(--teal)}}.summary{{margin:7px 0 0;color:var(--muted);font-size:13px;line-height:1.65}}.tags{{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}}.tag{{display:inline-flex;align-items:center;min-height:22px;padding:0 7px;border-radius:4px;background:#eee9dd;color:#5c564d;font-family:var(--mono);font-size:11px}}
    .intel-meta{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px}}.intel-field{{min-width:0;padding:7px 8px;border:1px dashed var(--line);border-radius:6px;background:var(--panel-soft)}}.intel-field span{{display:block;color:var(--weak);font-size:10px;line-height:1.2}}.intel-field b{{display:block;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;line-height:1.25}}
    .reason{{margin-top:12px;padding:9px 10px;border-radius:6px;background:var(--green-soft);color:#245c39;font-size:12px;line-height:1.6}}.card[data-category="政策"] .reason{{background:var(--red-soft);color:#8d332b}}
    .side-stack{{display:grid;gap:16px}}.source-matrix{{display:grid;gap:8px;padding:12px}}.source-row{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:9px 10px;border:1px solid var(--line);border-radius:7px;background:var(--panel-soft)}}.source-row strong{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}}.source-row small{{grid-column:1/-1;color:var(--weak);font-size:12px;line-height:1.5}}.badge{{display:inline-flex;align-items:center;min-height:22px;padding:0 7px;border-radius:999px;border:1px solid rgba(8,127,123,.25);background:var(--teal-soft);color:var(--teal);font-size:11px;white-space:nowrap}}
    .digest{{display:grid;gap:10px;padding:12px}}.digest-line{{display:grid;grid-template-columns:28px minmax(0,1fr);gap:9px;align-items:start}}.rank{{width:28px;height:28px;border-radius:6px;display:grid;place-items:center;background:#eee9dd;color:var(--ink);font-family:var(--mono);font-weight:800;font-size:12px}}.digest-line p{{margin:0;font-size:13px;line-height:1.55}}.digest-line small{{color:var(--weak);font-size:11px}}
    @media(max-width:1120px){{.content-grid{{grid-template-columns:1fr}}.side-stack{{grid-template-columns:repeat(2,minmax(0,1fr))}}.side-stack .panel:first-child{{grid-column:1/-1}}}}
    @media(max-width:860px){{.app{{grid-template-columns:1fr}}.sidebar{{display:none}}.main{{padding:16px 14px 36px}}.topbar{{grid-template-columns:1fr}}.status-strip{{grid-template-columns:repeat(2,minmax(0,1fr))}}.side-stack{{grid-template-columns:1fr}}.intel-meta{{grid-template-columns:1fr}}.item,.day{{grid-template-columns:58px 22px minmax(0,1fr)}}.timeline{{--time:58px}}.time{{font-size:12px}}}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-title"><span class="brand-mark">CR</span><span>Consulting Radar</span></div>
        <div class="brand-sub">Live MVP：公开权威信源真实采集结果</div>
      </div>
      <div class="nav-group">
        <div class="nav-label">LIVE FEED</div>
        <button class="nav-link active" data-filter="全部"><span class="nav-icon">◆</span>全部</button>
        <button class="nav-link" data-filter="政策"><span class="nav-icon">◇</span>政策</button>
        <button class="nav-link" data-filter="行业"><span class="nav-icon">▣</span>行业数据</button>
      </div>
      <div class="nav-spacer"></div>
      <div class="nav-note">本页由采集器生成，数据来自公开网页列表。生成时间：{h(generated)}</div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="title-block">
          <h1>咨询顾问信息雷达 · Live MVP</h1>
          <p>第三步成果：已接入国家发改委政策发布、国家统计局数据发布两个公开网页源，真实抓取标题、日期和原文链接，并自动生成初步咨询价值判断。</p>
        </div>
        <div class="status-strip">
          <div class="metric"><div class="metric-label">真实条目</div><div class="metric-value">{len(items)}</div></div>
          <div class="metric"><div class="metric-label">政策条目</div><div class="metric-value">{counts.get("政策", 0)}</div></div>
          <div class="metric"><div class="metric-label">行业条目</div><div class="metric-value">{counts.get("行业", 0)}</div></div>
          <div class="metric"><div class="metric-label">最新日期</div><div class="metric-value" style="font-size:18px">{h(latest[5:])}</div></div>
        </div>
      </header>
      <section class="toolbar" aria-label="筛选工具栏">
        <label class="search"><span>⌕</span><input id="searchInput" type="search" placeholder="搜索真实采集标题、标签、咨询场景" /></label>
        <div class="filters">
          <button class="chip active" data-filter="全部">全部</button>
          <button class="chip" data-filter="政策">政策</button>
          <button class="chip" data-filter="行业">行业</button>
        </div>
      </section>
      <section class="content-grid">
        <section class="panel">
          <div class="panel-head"><h2 class="panel-title">真实采集时间线</h2><span class="panel-sub">public HTML list</span></div>
          <div class="timeline" id="timeline">
            <div class="day"><div class="day-date">实时结果</div><div></div><div class="day-line"></div></div>
            {cards}
          </div>
        </section>
        <aside class="side-stack">
          <section class="panel">
            <div class="panel-head"><h2 class="panel-title">采集源状态</h2><span class="panel-sub">2 sources</span></div>
            <div class="source-matrix">{source_rows}</div>
          </section>
          <section class="panel">
            <div class="panel-head"><h2 class="panel-title">晨报候选</h2><span class="panel-sub">自动摘要雏形</span></div>
            <div class="digest">
              <div class="digest-line"><div class="rank">1</div><p>发改委政策条目适合进入政策雷达。<br><small>重点关注投资、能源、公用事业、外资等关键词。</small></p></div>
              <div class="digest-line"><div class="rank">2</div><p>统计局数据条目适合进入宏观和行业监测。<br><small>重点关注 CPI/PPI、PMI、工业利润、固定资产投资。</small></p></div>
              <div class="digest-line"><div class="rank">3</div><p>下一步可补充正文抽取和 AI 摘要。<br><small>目前已保留原文链接，避免复制全文。</small></p></div>
            </div>
          </section>
        </aside>
      </section>
    </main>
  </div>
  <script>
    const cards = Array.from(document.querySelectorAll(".card"));
    const buttons = Array.from(document.querySelectorAll("[data-filter]"));
    const searchInput = document.getElementById("searchInput");
    let currentFilter = "全部";
    function applyFilters() {{
      const query = searchInput.value.trim().toLowerCase();
      cards.forEach((card) => {{
        const item = card.closest(".item");
        const category = card.dataset.category;
        const okCategory = currentFilter === "全部" || category === currentFilter;
        const okQuery = !query || card.textContent.toLowerCase().includes(query);
        item.style.display = okCategory && okQuery ? "grid" : "none";
      }});
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
