import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
INPUT_PATH = OUTPUT_DIR / "bailing-public-data.json"
DATA_OUT = OUTPUT_DIR / "bailing-industry-spaces-data.json"
HTML_OUT = OUTPUT_DIR / "bailing-industry-spaces.html"


SPACES = [
    {
        "id": "consulting",
        "name": "管理咨询",
        "short": "咨询",
        "audience": "咨询顾问 / 项目经理",
        "keywords": ["规划", "投资", "监管", "财政", "工业", "价格", "PMI", "风险", "经营", "十五五"],
        "signals": ["政策窗口", "客户简报", "项目背景", "经营诊断"],
        "locked_tools": ["客户晨报", "PPT 素材卡", "影响矩阵"],
    },
    {
        "id": "manufacturing",
        "name": "制造业",
        "short": "制造",
        "audience": "制造企业 / 产业园区",
        "keywords": ["制造", "工业", "生产者", "PMI", "价格", "物流", "技术中心", "外商投资"],
        "signals": ["景气变化", "成本压力", "产业政策", "供应链"],
        "locked_tools": ["产业链追踪", "竞品动向", "成本预警"],
    },
    {
        "id": "energy_infra",
        "name": "能源与基础设施",
        "short": "能源",
        "audience": "能源、公用事业、基建客户",
        "keywords": ["能源", "电力", "天然气", "石油", "基础设施", "应急", "生态保护", "投资"],
        "signals": ["项目约束", "监管变化", "基础设施机会", "安全韧性"],
        "locked_tools": ["项目机会库", "区域政策比对", "风险条款摘要"],
    },
    {
        "id": "finance",
        "name": "财政金融",
        "short": "金融",
        "audience": "投融资、财务、金融机构",
        "keywords": ["财政", "金融", "基金", "国债", "货币", "利率", "融资", "预算"],
        "signals": ["资金环境", "融资窗口", "监管倾向", "财政节奏"],
        "locked_tools": ["融资环境雷达", "政策原文摘要", "机构观点汇总"],
    },
    {
        "id": "regional",
        "name": "区域招商",
        "short": "区域",
        "audience": "地方政府 / 园区 / 招商团队",
        "keywords": ["区域", "投资", "外资", "目录", "预算内", "生态保护", "民营", "农业", "棉花"],
        "signals": ["招商方向", "资金支持", "产业目录", "区域项目"],
        "locked_tools": ["招商话术", "政策对标", "项目线索"],
    },
    {
        "id": "macro_ops",
        "name": "宏观经营",
        "short": "宏观",
        "audience": "企业主 / 经营管理者",
        "keywords": ["居民消费", "价格", "CPI", "PPI", "利润", "固定资产", "人口", "采购经理", "PMI"],
        "signals": ["需求变化", "价格趋势", "经营压力", "市场判断"],
        "locked_tools": ["经营晨报", "指标看板", "管理层简报"],
    },
]


def h(value):
    return escape(str(value or ""), quote=True)


def item_text(item):
    parts = [
        item.get("title", ""),
        item.get("category", ""),
        item.get("source_name", ""),
        " ".join(item.get("tags", [])),
        item.get("scene", ""),
        item.get("consulting_value", ""),
    ]
    return " ".join(parts)


def match_score(item, space):
    text = item_text(item)
    score = 0
    hits = []
    for keyword in space["keywords"]:
        if keyword in text:
            score += 12
            hits.append(keyword)
    if item.get("category") == "国家政策":
        score += 8
    if item.get("category") == "宏观数据" and space["id"] in {"consulting", "manufacturing", "macro_ops"}:
        score += 8
    if item.get("category") == "财政金融" and space["id"] in {"consulting", "finance", "regional"}:
        score += 8
    score += min(item.get("score", 0) // 10, 9)
    return score, hits[:5]


def build_spaces(items):
    spaces = []
    for space in SPACES:
        ranked = []
        for item in items:
            score, hits = match_score(item, space)
            if score >= 18:
                ranked.append(
                    {
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
                    }
                )
        ranked.sort(key=lambda row: (row["score"], row["published_at"]), reverse=True)
        top_items = ranked[:10]
        spaces.append(
            {
                **space,
                "item_count": len(ranked),
                "top_items": top_items,
                "brief": make_brief(space, top_items),
                "gaps": make_gaps(space),
            }
        )
    return spaces


def make_brief(space, top_items):
    if not top_items:
        return f"{space['name']}空间暂无足够匹配信息，需要继续补充垂直源。"
    top_categories = Counter(item["category"] for item in top_items)
    main_category = top_categories.most_common(1)[0][0]
    focus = "、".join(space["signals"][:3])
    return f"今日重点集中在{main_category}，建议关注{focus}。"


def make_gaps(space):
    base = {
        "consulting": ["咨询公司观点", "券商行业报告", "重点客户公告"],
        "manufacturing": ["工信部文件", "龙头企业年报", "产业链价格数据"],
        "energy_infra": ["能源局政策", "地方项目清单", "重大工程招投标"],
        "finance": ["人民银行动态适配", "券商研报", "投资机构观点"],
        "regional": ["省市政策库", "园区招商政策", "地方发改委项目"],
        "macro_ops": ["高频指标", "行业协会数据", "消费与就业补充源"],
    }
    return base.get(space["id"], [])


def write_data(source_data, spaces):
    payload = {
        "product": "百灵",
        "professional_layer": "知更",
        "version": "industry-spaces-mvp-2",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_generated_at": source_data.get("generated_at"),
        "source_item_count": source_data.get("item_count", 0),
        "space_count": len(spaces),
        "spaces": spaces,
    }
    DATA_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def space_button(space, active=False):
    return f"""
      <button class="space-tab {'active' if active else ''}" data-space="{h(space['id'])}">
        <span>{h(space['short'])}</span>
        <b>{h(space['name'])}</b>
        <em>{h(space['item_count'])} 条</em>
      </button>
    """


def signal_chips(space):
    return "".join(f"<span>{h(signal)}</span>" for signal in space["signals"])


def locked_tools(space):
    return "".join(f"<button title=\"知更认证后开放\">{h(tool)}</button>" for tool in space["locked_tools"])


def item_card(item):
    matches = "".join(f"<span>{h(match)}</span>" for match in item.get("matches", []))
    return f"""
      <article class="intel-card">
        <div class="meta">
          <span>{h(item['published_at'][5:])}</span>
          <span>{h(item['category'])}</span>
          <strong>{h(item['score'])}</strong>
        </div>
        <a href="{h(item['url'])}" target="_blank" rel="noopener noreferrer">{h(item['title'])}</a>
        <p>{h(item['consulting_value'])}</p>
        <div class="matches">{matches or '<span>综合匹配</span>'}</div>
        <footer>{h(item['source_name'])}</footer>
      </article>
    """


def space_panel(space, active=False):
    items = "".join(item_card(item) for item in space["top_items"])
    gaps = "".join(f"<li>{h(gap)}</li>" for gap in space["gaps"])
    return f"""
      <section class="space-panel {'active' if active else ''}" data-panel="{h(space['id'])}">
        <div class="space-head">
          <div>
            <p>{h(space['audience'])}</p>
            <h2>{h(space['name'])}空间</h2>
          </div>
          <div class="brief">{h(space['brief'])}</div>
        </div>
        <div class="signals">{signal_chips(space)}</div>
        <div class="workspace">
          <div class="feed">{items}</div>
          <aside class="tools">
            <section>
              <h3>知更工具</h3>
              <div class="tool-grid">{locked_tools(space)}</div>
            </section>
            <section>
              <h3>待补信源</h3>
              <ul>{gaps}</ul>
            </section>
          </aside>
        </div>
      </section>
    """


def render_html(payload):
    spaces = payload["spaces"]
    tabs = "".join(space_button(space, index == 0) for index, space in enumerate(spaces))
    panels = "".join(space_panel(space, index == 0) for index, space in enumerate(spaces))
    total_matches = sum(space["item_count"] for space in spaces)
    generated = h(payload["generated_at"])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>百灵行业空间 MVP</title>
  <style>
    :root {{
      --bg:#f5f7f4;--surface:#fff;--soft:#eef3ee;--ink:#171a17;--muted:#5f675e;--weak:#8e978b;
      --line:#d8e0d5;--strong:#b8c6b4;--green:#246f58;--green-soft:#e2f0ea;--red:#b25544;
      --red-soft:#f5e5e1;--blue:#2d6994;--blue-soft:#e3eef5;--gold:#976b22;--gold-soft:#f2e8d4;
      --nav:#19241d;--shadow:0 16px 36px rgba(32,45,34,.08);--radius:8px;
      --mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;--sans:Inter,"PingFang SC","Microsoft YaHei",Arial,sans-serif;
    }}
    *{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:var(--sans);letter-spacing:0}}a{{color:inherit;text-decoration:none}}button{{font:inherit}}
    .app{{min-height:100vh;display:grid;grid-template-columns:260px minmax(0,1fr)}}.side{{position:sticky;top:0;height:100vh;background:var(--nav);color:#f6f3e9;padding:20px 14px;display:flex;flex-direction:column;gap:18px}}
    .brand{{padding:0 10px 14px;border-bottom:1px solid rgba(255,255,255,.12)}}.brand-line{{display:flex;align-items:center;gap:10px}}.mark{{width:34px;height:34px;border-radius:8px;background:#d8efe4;color:#153a2c;display:grid;place-items:center;font-size:18px;font-weight:900}}.brand h1{{margin:0;font-size:21px;line-height:1}}.brand p{{margin:8px 0 0;color:rgba(246,243,233,.62);font-size:12px;line-height:1.55}}
    .side-metric{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.side-metric div{{border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:10px;background:rgba(255,255,255,.05)}}.side-metric span{{display:block;color:rgba(246,243,233,.55);font-size:11px}}.side-metric b{{display:block;margin-top:5px;font:900 22px/1 var(--mono)}}.side-note{{margin-top:auto;border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:12px;background:rgba(255,255,255,.05);color:rgba(246,243,233,.66);font-size:12px;line-height:1.6}}
    .main{{padding:20px 24px 38px;min-width:0;display:grid;gap:16px}}.top{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end}}.top p{{margin:0 0 8px;color:var(--green);font:800 12px var(--mono)}}.top h2{{margin:0;font-size:32px;line-height:1.18}}.top small{{display:block;margin-top:9px;color:var(--muted);font-size:14px;line-height:1.65}}.top a{{height:36px;display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:8px;padding:0 12px;background:var(--surface);color:var(--green);font-weight:800;font-size:13px}}
    .tabs{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}}.space-tab{{min-width:0;text-align:left;border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:11px;cursor:pointer;box-shadow:var(--shadow)}}.space-tab:hover,.space-tab.active{{border-color:rgba(36,111,88,.45);background:var(--green-soft)}}.space-tab span{{display:inline-flex;width:28px;height:24px;border-radius:6px;align-items:center;justify-content:center;background:var(--nav);color:#f6f3e9;font-size:12px;font-weight:900}}.space-tab b{{display:block;margin-top:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}}.space-tab em{{display:block;margin-top:5px;color:var(--muted);font-style:normal;font:12px var(--mono)}}
    .space-panel{{display:none;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}}.space-panel.active{{display:block}}.space-head{{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:16px;padding:18px;border-bottom:1px solid var(--line);background:#fbfcfa}}.space-head p{{margin:0;color:var(--muted);font-size:13px}}.space-head h2{{margin:6px 0 0;font-size:24px}}.brief{{align-self:center;border-left:3px solid var(--green);padding:9px 12px;background:var(--green-soft);border-radius:0 8px 8px 0;color:#245b47;font-size:13px;line-height:1.65}}.signals{{display:flex;gap:7px;flex-wrap:wrap;padding:12px 18px;border-bottom:1px solid var(--line)}}.signals span{{min-height:25px;display:inline-flex;align-items:center;border-radius:999px;background:var(--soft);padding:0 9px;color:#4e594d;font-size:12px}}
    .workspace{{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:0}}.feed{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding:14px;border-right:1px solid var(--line)}}.intel-card{{min-width:0;border:1px solid var(--line);border-radius:8px;background:#fff;padding:13px;display:flex;flex-direction:column;gap:8px}}.intel-card:hover{{border-color:var(--strong)}}.meta{{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:12px}}.meta span{{border-radius:999px;background:var(--soft);padding:3px 7px}}.meta strong{{margin-left:auto;color:var(--green);font:900 12px var(--mono)}}.intel-card a{{font-size:15px;font-weight:900;line-height:1.45}}.intel-card a:hover{{color:var(--green)}}.intel-card p{{margin:0;color:var(--muted);font-size:12px;line-height:1.65}}.matches{{display:flex;gap:6px;flex-wrap:wrap}}.matches span{{border-radius:4px;background:var(--blue-soft);color:var(--blue);padding:4px 6px;font:11px var(--mono)}}.intel-card footer{{margin-top:auto;color:var(--weak);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .tools{{display:grid;align-content:start;gap:14px;padding:14px;background:#fbfcfa}}.tools section{{border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:12px}}.tools h3{{margin:0 0 10px;font-size:14px}}.tool-grid{{display:grid;gap:7px}}.tool-grid button{{height:34px;border:1px solid var(--line);border-radius:8px;background:var(--soft);color:var(--muted);font-size:12px;text-align:left;padding:0 10px}}.tools ul{{margin:0;padding-left:18px;color:var(--muted);font-size:12px;line-height:1.8}}
    @media(max-width:1180px){{.tabs{{grid-template-columns:repeat(3,minmax(0,1fr))}}.workspace{{grid-template-columns:1fr}}.feed{{border-right:0;border-bottom:1px solid var(--line)}}.tools{{grid-template-columns:1fr 1fr}}}}
    @media(max-width:820px){{.app{{grid-template-columns:1fr}}.side{{position:relative;height:auto}}.main{{padding:16px 14px 34px}}.top{{grid-template-columns:1fr}}.top h2{{font-size:26px}}.tabs{{grid-template-columns:repeat(2,minmax(0,1fr))}}.space-head{{grid-template-columns:1fr}}.feed{{grid-template-columns:1fr}}.tools{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="side">
      <div class="brand">
        <div class="brand-line"><div class="mark">百</div><h1>百灵</h1></div>
        <p>行业空间版，把同一批权威信息映射到不同人群和行业场景。</p>
      </div>
      <div class="side-metric">
        <div><span>行业空间</span><b>{len(spaces)}</b></div>
        <div><span>匹配线索</span><b>{total_matches}</b></div>
        <div><span>原始条目</span><b>{payload['source_item_count']}</b></div>
        <div><span>版本</span><b style="font-size:16px">MVP-2</b></div>
      </div>
      <div class="side-note">知更将在这些空间之上承接认证顾问能力：晨报、专题、客户简报、项目素材和深度摘要。</div>
    </aside>
    <main class="main">
      <header class="top">
        <div>
          <p>BAILING INDUSTRY SPACES</p>
          <h2>从信息流进入行业空间。</h2>
          <small>生成时间 {generated}，基于第一步真实公开采集数据重组。</small>
        </div>
        <a href="bailing-public-mvp.html">返回公开版</a>
      </header>
      <nav class="tabs" aria-label="行业空间">{tabs}</nav>
      {panels}
    </main>
  </div>
  <script>
    const tabs = Array.from(document.querySelectorAll(".space-tab"));
    const panels = Array.from(document.querySelectorAll(".space-panel"));
    tabs.forEach((tab) => {{
      tab.addEventListener("click", () => {{
        const id = tab.dataset.space;
        tabs.forEach((button) => button.classList.toggle("active", button.dataset.space === id));
        panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === id));
      }});
    }});
  </script>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")


def main():
    source_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    spaces = build_spaces(source_data.get("items", []))
    payload = write_data(source_data, spaces)
    render_html(payload)
    print(f"Wrote {DATA_OUT}")
    print(f"Wrote {HTML_OUT}")
    for space in spaces:
        print(f"{space['name']}: {space['item_count']} matched items")


if __name__ == "__main__":
    main()
