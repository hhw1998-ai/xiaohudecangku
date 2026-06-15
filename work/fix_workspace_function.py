import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "index.html"


WORKSPACE = r"""function renderWorkspace(){const verified=state.role==='verified';const result=state.toolResult;let resultHtml='<div class="output" id="toolOutput">选择一个专业工具运行。</div>';if(result&&result.type==='brief'){const lines=(result.payload.items||[]).map(i=>`- ${esc(i.title)}（${esc(i.source_name)}）`).join('\\n');resultHtml=`<div class="output" id="toolOutput"><strong>${esc(result.payload.title)}</strong>\\n${esc(result.payload.summary)}\\n\\n${lines}</div>`}else if(result){const lines=(result.payload.matrix||[]).map(x=>`- [${esc(x.impact_strength)}] ${esc(x.title)}\\n  ${esc(x.consulting_action)}\\n  ${esc(x.url)}`).join('\\n\\n');resultHtml=`<div class="output" id="toolOutput"><strong>政策影响矩阵：${esc(result.payload.topic)}</strong>\\n${lines}</div>`}qs('view-workspace').innerHTML=hero(UI.workspaceTitle,UI.workspaceSub,'ZHIGENG WORKSPACE')+`${!verified?'<div class="panel"><div class="panel-head"><h3>权限提示</h3><span>not verified</span></div><div class="mini-list"><div class="mini-row"><p>你当前还不是知更认证顾问，可以在“认证申请”里切换为认证顾问体验完整工作台。</p></div></div></div>':''}<section class="grid"><div class="panel"><div class="panel-head"><h3>专业工具</h3><span>${verified?'api enabled':'preview'}</span></div><div class="tool-grid">${authPayload.pro_tools.map((t,idx)=>`<article class="tool-card"><header><strong>${esc(t.name)}</strong><em>${verified?'实时API':'认证后'}</em></header><p>${esc(t.description)}</p><div class="actions"><button data-tool="${idx===0?'brief':'matrix'}">${verified?'运行':'查看说明'}</button></div></article>`).join('')}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>我的订阅</h3><span>${state.subscriptions.length}</span></div><div class="mini-list">${state.subscriptions.map(s=>`<div class="mini-row"><header><strong>${esc(s)}</strong><em>on</em></header><p>关键词追踪中。</p></div>`).join('')}<div class="actions"><button id="addSub">添加订阅</button></div></div></div></aside></section><section class="grid"><div class="panel"><div class="panel-head"><h3>晨报素材</h3><span>${state.briefs.length}</span></div><div class="feed">${state.briefs.map(b=>`<article class="card"><div class="meta"><span>${esc(b.created_at)}</span></div><a class="title">${esc(b.title)}</a><p>${esc(b.body)}</p></article>`).join('')||'<div class="mini-row"><p>还没有晨报素材。点击专业工具可实时生成。</p></div>'}</div></div><aside class="side-stack"><div class="panel"><div class="panel-head"><h3>收藏夹</h3><span>${state.saved.length}</span></div><div class="mini-list">${state.saved.map(id=>data.items.find(i=>i.id===id)).filter(Boolean).map(i=>`<div class="mini-row"><header><strong>${esc(i.title)}</strong><em>${esc(i.category)}</em></header><p>${esc(i.source_name)}</p></div>`).join('')||'<div class="mini-row"><p>暂无收藏。</p></div>'}</div></div></aside></section><section class="panel"><div class="panel-head"><h3>生成结果</h3><span>${apiState.status}</span></div><div class="feed">${resultHtml}</div></section>`;qs('view-workspace').querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>verified?runTool(b.dataset.tool):toast('需要认证','请先切换为认证顾问体验完整工作台'));qs('addSub').onclick=()=>{const pool=['外资','财政','能源','价格','制造业','民营经济','新能源','机器人'];const next=pool.find(x=>!state.subscriptions.includes(x))||('专题'+Date.now());state.subscriptions.push(next);save();renderWorkspace()}}
    """


def main():
    html = APP.read_text(encoding="utf-8")
    html, count = re.subn(
        r"function renderWorkspace\(\).*?(?=\n    function renderAdmin\(\))",
        WORKSPACE,
        html,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("renderWorkspace replacement failed")
    APP.write_text(html, encoding="utf-8")
    print("fixed renderWorkspace")


if __name__ == "__main__":
    main()
