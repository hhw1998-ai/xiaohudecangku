import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "index.html"
PUBLIC = ROOT / "outputs" / "bailing-public-data.json"
SPACES = ROOT / "outputs" / "bailing-industry-spaces-data.json"
AUTH = ROOT / "outputs" / "zhigeng-auth-workspace-data.json"


def js_json(path):
    return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False).replace("</", "<\\/")


def replace_const(html, name, value):
    pattern = rf"const {name} = .*?;\n"
    replacement = f"const {name} = {value};\n"
    html, count = re.subn(pattern, replacement, html, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not replace {name}")
    return html


def patch_admin_landscape(html):
    old = """<div class="panel"><div class="panel-head"><h3>下一批工程</h3><span>next</span></div><div class="mini-list"><div class="mini-row"><p>接入交易所/巨潮 API，用于年报、公告和公司动向。</p></div><div class="mini-row"><p>补充券商研报、投资机构观点和咨询公司公开洞察。</p></div><div class="mini-row"><p>搭建后端定时采集、去重、摘要和权限系统。</p></div></div></div>"""
    new = """<div class="panel"><div class="panel-head"><h3>信源版图</h3><span>roadmap</span></div><div class="mini-list">${(data.source_landscape||[]).map(x=>`<div class="mini-row"><header><strong>${esc(x.name)}</strong><em>${esc(x.connected)} / ${esc(x.target)}</em></header><p>${esc(x.note)}；缺口 ${Math.max(0,(x.target||0)-(x.connected||0))} 个。</p></div>`).join('')||'<div class="mini-row"><p>暂无信源版图数据。</p></div>'}</div></div><div class="panel"><div class="panel-head"><h3>下一批工程</h3><span>next</span></div><div class="mini-list"><div class="mini-row"><p>接入交易所/巨潮 API，用于年报、公告和公司动向。</p></div><div class="mini-row"><p>补充券商研报、投资机构观点和咨询公司公开洞察。</p></div><div class="mini-row"><p>搭建后端定时采集、去重、摘要和权限系统。</p></div></div></div>"""
    if old in html:
        return html.replace(old, new, 1)
    return html


def main():
    html = APP.read_text(encoding="utf-8")
    html = replace_const(html, "data", js_json(PUBLIC))
    html = replace_const(html, "spacesPayload", js_json(SPACES))
    html = replace_const(html, "authPayload", js_json(AUTH))
    html = patch_admin_landscape(html)
    APP.write_text(html, encoding="utf-8")
    print("Injected expanded data into app/index.html")


if __name__ == "__main__":
    main()
