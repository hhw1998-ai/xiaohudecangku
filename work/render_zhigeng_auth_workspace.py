import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
INPUT_PATH = OUTPUT_DIR / "bailing-industry-spaces-data.json"
DATA_OUT = OUTPUT_DIR / "zhigeng-auth-workspace-data.json"
HTML_OUT = OUTPUT_DIR / "zhigeng-auth-workspace.html"


ROLES = [
    {
        "id": "public",
        "name": "公开用户",
        "status": "可直接使用",
        "description": "浏览百灵公开信息流、行业空间、原文链接和基础搜索筛选。",
        "features": ["公开信息流", "行业空间浏览", "原文跳转", "基础筛选"],
        "limits": ["无个人订阅", "无客户简报", "无深度摘要", "无专题追踪"],
    },
    {
        "id": "applicant",
        "name": "认证申请中",
        "status": "提交资料后",
        "description": "选择行业方向，提交身份或职业材料，进入知更专业层审核。",
        "features": ["行业偏好", "试用晨报", "收藏夹", "申请进度"],
        "limits": ["专业报告导出受限", "客户空间不可用", "专题追踪数量受限"],
    },
    {
        "id": "verified",
        "name": "知更认证顾问",
        "status": "审核通过",
        "description": "开启顾问工作台，用于客户晨报、专题追踪、PPT 素材卡和项目资料整理。",
        "features": ["客户晨报", "PPT 素材卡", "影响矩阵", "专题追踪", "行业订阅", "项目资料夹"],
        "limits": ["需遵守来源版权和引用规范", "公众号等授权源需单独开通"],
    },
]


PRO_TOOLS = [
    {
        "id": "morning_brief",
        "name": "客户晨报",
        "stage": "认证后开放",
        "description": "把行业空间里的高分线索整理成客户可读的晨报提纲。",
        "inputs": ["行业空间", "客户行业", "关注关键词"],
        "outputs": ["今日重点", "顾问解读", "建议动作"],
    },
    {
        "id": "ppt_cards",
        "name": "PPT 素材卡",
        "stage": "认证后开放",
        "description": "把政策、数据、公告转成可进入咨询汇报的素材卡。",
        "inputs": ["原文链接", "指标或政策标题", "项目主题"],
        "outputs": ["事实卡", "影响判断", "引用链接"],
    },
    {
        "id": "impact_matrix",
        "name": "影响矩阵",
        "stage": "认证后开放",
        "description": "按客户、行业、区域、时间维度评估政策和数据影响。",
        "inputs": ["政策条目", "客户类型", "区域"],
        "outputs": ["机会", "风险", "待确认问题"],
    },
    {
        "id": "topic_tracker",
        "name": "专题追踪",
        "stage": "认证后开放",
        "description": "围绕十五五、外资、民营经济、价格、PMI 等主题持续追踪。",
        "inputs": ["主题关键词", "信源范围", "更新频率"],
        "outputs": ["变化记录", "关键节点", "提醒"],
    },
]


APPLICATION_STEPS = [
    {"name": "选择身份", "detail": "个人用户、企业经营者、咨询顾问、行业研究员。"},
    {"name": "选择行业", "detail": "从管理咨询、制造业、能源基建、财政金融、区域招商等空间中选择。"},
    {"name": "提交证明", "detail": "可用公司邮箱、名片、项目经历或机构证明。"},
    {"name": "开通知更", "detail": "审核后获得专业工具、订阅和工作台能力。"},
]


def h(value):
    return escape(str(value or ""), quote=True)


def summarize_spaces(spaces):
    return [
        {
            "id": space["id"],
            "name": space["name"],
            "audience": space["audience"],
            "item_count": space["item_count"],
            "brief": space["brief"],
            "recommended_tools": space.get("locked_tools", [])[:3],
            "top_titles": [item["title"] for item in space.get("top_items", [])[:3]],
        }
        for space in spaces
    ]


def build_payload(industry_data):
    spaces = summarize_spaces(industry_data.get("spaces", []))
    total_items = industry_data.get("source_item_count", 0)
    category_counter = Counter()
    for space in industry_data.get("spaces", []):
        for item in space.get("top_items", []):
            category_counter[item.get("category", "未分类")] += 1
    return {
        "product": "知更",
        "parent_product": "百灵",
        "version": "auth-workspace-mvp-3",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "industry_input_generated_at": industry_data.get("generated_at"),
        "source_item_count": total_items,
        "space_count": len(spaces),
        "roles": ROLES,
        "application_steps": APPLICATION_STEPS,
        "pro_tools": PRO_TOOLS,
        "spaces": spaces,
        "category_distribution": dict(category_counter),
    }


def role_card(role, active=False):
    features = "".join(f"<span>{h(feature)}</span>" for feature in role["features"])
    limits = "".join(f"<li>{h(limit)}</li>" for limit in role["limits"])
    return f"""
      <article class="role-card {'active' if active else ''}" data-role="{h(role['id'])}">
        <div class="role-head">
          <strong>{h(role['name'])}</strong>
          <em>{h(role['status'])}</em>
        </div>
        <p>{h(role['description'])}</p>
        <div class="feature-list">{features}</div>
        <ul>{limits}</ul>
      </article>
    """


def tool_card(tool):
    inputs = "".join(f"<span>{h(item)}</span>" for item in tool["inputs"])
    outputs = "".join(f"<span>{h(item)}</span>" for item in tool["outputs"])
    return f"""
      <article class="tool-card">
        <div class="tool-top">
          <strong>{h(tool['name'])}</strong>
          <em>{h(tool['stage'])}</em>
        </div>
        <p>{h(tool['description'])}</p>
        <div class="io-grid">
          <div><b>输入</b>{inputs}</div>
          <div><b>输出</b>{outputs}</div>
        </div>
      </article>
    """


def step_card(step, index):
    return f"""
      <div class="step">
        <span>{index + 1}</span>
        <strong>{h(step['name'])}</strong>
        <p>{h(step['detail'])}</p>
      </div>
    """


def space_card(space):
    tools = "".join(f"<span>{h(tool)}</span>" for tool in space.get("recommended_tools", []))
    titles = "".join(f"<li>{h(title)}</li>" for title in space.get("top_titles", []))
    return f"""
      <article class="space-card">
        <div>
          <strong>{h(space['name'])}</strong>
          <em>{h(space['item_count'])} 条线索</em>
        </div>
        <p>{h(space['brief'])}</p>
        <div class="tool-tags">{tools}</div>
        <ul>{titles}</ul>
      </article>
    """


def render_html(payload):
    roles = "".join(role_card(role, index == 2) for index, role in enumerate(payload["roles"]))
    steps = "".join(step_card(step, index) for index, step in enumerate(payload["application_steps"]))
    tools = "".join(tool_card(tool) for tool in payload["pro_tools"])
    spaces = "".join(space_card(space) for space in payload["spaces"])
    generated = h(payload["generated_at"])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>知更认证工作台 MVP</title>
  <style>
    :root {{
      --bg:#f6f7f3;--surface:#fff;--soft:#eef2eb;--ink:#171a17;--muted:#5f675e;--weak:#8c9589;
      --line:#d7dfd3;--strong:#b6c4b1;--green:#246f58;--green-soft:#e2f0ea;--gold:#9b6d21;
      --gold-soft:#f3ead5;--red:#b25443;--red-soft:#f5e5e1;--blue:#2d6e96;--blue-soft:#e2eef5;
      --nav:#19241d;--shadow:0 16px 36px rgba(31,44,34,.08);--radius:8px;
      --mono:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;--sans:Inter,"PingFang SC","Microsoft YaHei",Arial,sans-serif;
    }}
    *{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font-family:var(--sans);letter-spacing:0}}a{{color:inherit;text-decoration:none}}button{{font:inherit}}
    .app{{min-height:100vh;display:grid;grid-template-columns:258px minmax(0,1fr)}}.side{{position:sticky;top:0;height:100vh;background:var(--nav);color:#f6f3e9;padding:20px 14px;display:flex;flex-direction:column;gap:18px}}
    .brand{{padding:0 10px 14px;border-bottom:1px solid rgba(255,255,255,.12)}}.brand-line{{display:flex;gap:10px;align-items:center}}.mark{{width:34px;height:34px;border-radius:8px;display:grid;place-items:center;background:#f3ead5;color:#3b2c14;font-size:18px;font-weight:900}}.brand h1{{margin:0;font-size:21px;line-height:1}}.brand p{{margin:8px 0 0;color:rgba(246,243,233,.64);font-size:12px;line-height:1.55}}
    .nav{{display:grid;gap:7px}}.nav a{{height:38px;display:flex;align-items:center;border-radius:8px;padding:0 10px;color:rgba(246,243,233,.74);background:rgba(255,255,255,.04);font-size:13px}}.nav a:hover{{background:rgba(255,255,255,.08);color:#fff}}.side-note{{margin-top:auto;border:1px solid rgba(255,255,255,.12);border-radius:8px;background:rgba(255,255,255,.05);padding:12px;color:rgba(246,243,233,.66);font-size:12px;line-height:1.6}}
    .main{{min-width:0;padding:20px 24px 38px;display:grid;gap:16px}}.hero{{display:grid;grid-template-columns:minmax(0,1fr) 430px;gap:16px;align-items:stretch}}.hero-copy{{padding:18px 0}}.eyebrow{{margin:0 0 9px;color:var(--gold);font:800 12px var(--mono)}}.hero h2{{margin:0;font-size:34px;line-height:1.16}}.hero p{{max-width:760px;margin:11px 0 0;color:var(--muted);font-size:14px;line-height:1.75}}.metrics{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}.metric{{border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:13px;box-shadow:var(--shadow)}}.metric span{{display:block;color:var(--muted);font-size:12px}}.metric b{{display:block;margin-top:7px;font:900 26px/1 var(--mono)}}.metric small{{display:block;margin-top:6px;color:var(--weak);font-size:11px}}
    .section{{border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:var(--shadow);overflow:hidden}}.section-head{{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line);background:#fbfcfa}}.section-head h3{{margin:0;font-size:16px}}.section-head span{{color:var(--weak);font:11px var(--mono);white-space:nowrap}}
    .roles{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:14px}}.role-card{{border:1px solid var(--line);border-radius:8px;padding:13px;background:#fff}}.role-card.active{{border-color:rgba(155,109,33,.45);background:var(--gold-soft)}}.role-head{{display:flex;align-items:center;justify-content:space-between;gap:10px}}.role-head strong{{font-size:15px}}.role-head em{{font-style:normal;border-radius:999px;background:var(--soft);padding:4px 8px;color:var(--muted);font-size:11px;white-space:nowrap}}.role-card.active .role-head em{{background:#fff7e8;color:var(--gold)}}.role-card p{{margin:9px 0 0;color:var(--muted);font-size:12px;line-height:1.6}}.feature-list{{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}}.feature-list span{{border-radius:4px;background:var(--green-soft);color:var(--green);padding:4px 6px;font:11px var(--mono)}}.role-card ul{{margin:10px 0 0;padding-left:18px;color:var(--weak);font-size:12px;line-height:1.7}}
    .flow{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:14px}}.step{{border:1px solid var(--line);border-radius:8px;background:#fff;padding:13px;min-height:126px}}.step span{{width:28px;height:28px;border-radius:7px;background:var(--nav);color:#f6f3e9;display:grid;place-items:center;font:900 13px var(--mono)}}.step strong{{display:block;margin-top:10px;font-size:14px}}.step p{{margin:7px 0 0;color:var(--muted);font-size:12px;line-height:1.6}}
    .tools{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:14px}}.tool-card{{border:1px solid var(--line);border-radius:8px;background:#fff;padding:13px;display:grid;gap:10px}}.tool-top{{display:flex;align-items:center;justify-content:space-between;gap:10px}}.tool-top strong{{font-size:15px}}.tool-top em{{font-style:normal;border-radius:999px;background:var(--gold-soft);color:var(--gold);padding:4px 8px;font-size:11px;white-space:nowrap}}.tool-card p{{margin:0;color:var(--muted);font-size:12px;line-height:1.6}}.io-grid{{display:grid;grid-template-columns:1fr;gap:7px}}.io-grid div{{border:1px dashed var(--line);border-radius:7px;background:#fbfcfa;padding:8px}}.io-grid b{{display:block;margin-bottom:6px;color:var(--ink);font-size:12px}}.io-grid span{{display:inline-flex;margin:0 5px 5px 0;border-radius:4px;background:var(--blue-soft);color:var(--blue);padding:4px 6px;font:11px var(--mono)}}
    .spaces{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:14px}}.space-card{{border:1px solid var(--line);border-radius:8px;background:#fff;padding:13px}}.space-card>div:first-child{{display:flex;justify-content:space-between;gap:10px;align-items:center}}.space-card strong{{font-size:15px}}.space-card em{{font-style:normal;color:var(--green);font:800 12px var(--mono);white-space:nowrap}}.space-card p{{margin:9px 0 0;color:var(--muted);font-size:12px;line-height:1.6}}.tool-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}}.tool-tags span{{border-radius:4px;background:var(--soft);color:#4e594d;padding:4px 6px;font:11px var(--mono)}}.space-card ul{{margin:10px 0 0;padding-left:18px;color:var(--muted);font-size:12px;line-height:1.6}}
    @media(max-width:1180px){{.hero{{grid-template-columns:1fr}}.tools{{grid-template-columns:repeat(2,minmax(0,1fr))}}.spaces{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
    @media(max-width:860px){{.app{{grid-template-columns:1fr}}.side{{position:relative;height:auto}}.main{{padding:16px 14px 34px}}.hero h2{{font-size:27px}}.roles,.flow,.tools,.spaces{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="side">
      <div class="brand">
        <div class="brand-line"><div class="mark">知</div><h1>知更</h1></div>
        <p>百灵之上的专业认证层，面向顾问和行业研究型用户。</p>
      </div>
      <nav class="nav">
        <a href="bailing-public-mvp.html">百灵公开版</a>
        <a href="bailing-industry-spaces.html">百灵行业空间</a>
        <a href="#roles">账号权限</a>
        <a href="#tools">专业工具</a>
      </nav>
      <div class="side-note">这一版是静态权限原型：先验证账号层、认证层、行业空间和专业工具之间的产品逻辑。</div>
    </aside>
    <main class="main">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">ZHIGENG AUTH WORKSPACE</p>
          <h2>让公开信息进入顾问工作流。</h2>
          <p>知更不是另一个资讯页，而是把百灵的信息流和行业空间转成认证顾问可使用的晨报、素材卡、专题追踪和影响判断。</p>
        </div>
        <div class="metrics">
          <div class="metric"><span>承接行业空间</span><b>{payload['space_count']}</b><small>来自百灵行业空间 MVP-2</small></div>
          <div class="metric"><span>底层公开条目</span><b>{payload['source_item_count']}</b><small>保留原文链接和来源</small></div>
          <div class="metric"><span>专业工具</span><b>{len(payload['pro_tools'])}</b><small>认证后开放</small></div>
          <div class="metric"><span>生成时间</span><b style="font-size:18px">{generated[5:10]}</b><small>{generated}</small></div>
        </div>
      </section>
      <section class="section" id="roles">
        <div class="section-head"><h3>账号与权限</h3><span>public / applicant / verified</span></div>
        <div class="roles">{roles}</div>
      </section>
      <section class="section">
        <div class="section-head"><h3>认证申请流程</h3><span>4 steps</span></div>
        <div class="flow">{steps}</div>
      </section>
      <section class="section" id="tools">
        <div class="section-head"><h3>知更专业工具</h3><span>locked preview</span></div>
        <div class="tools">{tools}</div>
      </section>
      <section class="section">
        <div class="section-head"><h3>行业空间接入</h3><span>{payload['space_count']} spaces</span></div>
        <div class="spaces">{spaces}</div>
      </section>
    </main>
  </div>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")


def main():
    industry_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    payload = build_payload(industry_data)
    DATA_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    render_html(payload)
    print(f"Wrote {DATA_OUT}")
    print(f"Wrote {HTML_OUT}")
    print(f"Roles: {len(payload['roles'])}; tools: {len(payload['pro_tools'])}; spaces: {payload['space_count']}")


if __name__ == "__main__":
    main()
