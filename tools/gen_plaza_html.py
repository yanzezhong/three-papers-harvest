import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('plaza_data.json', encoding='utf-8'))
# 截断超长全文，控制体积
for u, t in list(data['full'].items()):
    if len(t) > 80000:
        data['full'][u] = t[:80000] + "\n\n…（超长截断）"

TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>内容广场 · 三报快照全文库</title>
<style>
:root{--bg:#f7f8fa;--card:#fff;--tx:#1c1e21;--tx2:#65676b;--bd:#e4e6eb;--accent:#1d6feb;--accent2:#e7f0fd;--ok:#0a8f5b;--okbg:#e6f6ef;--warn:#b0700c;--warnbg:#fdf3e3;--graybg:#eef0f3;--chip:#f0f2f5}
@media (prefers-color-scheme:dark){:root{--bg:#101214;--card:#1b1d21;--tx:#e8eaed;--tx2:#9aa3af;--bd:#2a2e34;--accent:#5b9df7;--accent2:#152742;--ok:#34d399;--okbg:#0f2c1e;--warn:#fbbf24;--warnbg:#332711;--graybg:#23262b;--chip:#24272c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",sans-serif;line-height:1.6;-webkit-text-size-adjust:100%}
.wrap{max-width:760px;margin:0 auto;padding:16px 14px 70px}
header.top{padding:6px 0 12px}
h1{font-size:1.35rem;margin:0}
.sub{color:var(--tx2);font-size:.82rem;margin-top:3px}
.tabs{display:flex;gap:18px;border-bottom:1px solid var(--bd);margin:12px 0 0;padding-bottom:8px}
.tab{font-size:.95rem;color:var(--tx2);cursor:pointer;padding:4px 2px}
.tab.on{color:var(--tx);font-weight:700;border-bottom:2px solid var(--accent)}
.toolbar{position:sticky;top:0;z-index:9;background:var(--bg);padding:10px 0 8px;border-bottom:1px solid var(--bd)}
.search{width:100%;padding:9px 12px;border-radius:10px;border:1px solid var(--bd);background:var(--card);color:var(--tx);font-size:.95rem;outline:none}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.chip{border:1px solid var(--bd);background:var(--card);color:var(--tx2);border-radius:999px;padding:4px 12px;font-size:.8rem;cursor:pointer;user-select:none}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.stat{font-size:.78rem;color:var(--tx2);margin:10px 2px 2px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:16px;margin:12px 0}
.thumb{width:calc(100% + 32px);margin:-16px -16px 12px;height:180px;object-fit:cover;display:block;border-radius:13px 13px 0 0}
.rimgs{margin:14px 0}
.rimgs img{width:100%;max-height:420px;object-fit:contain;display:block;margin-bottom:10px;border-radius:8px;background:var(--chip)}
.trow{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.title{font-size:1.02rem;font-weight:700;line-height:1.4;margin:0}
.title a{color:var(--tx);text-decoration:none}
.score{flex-shrink:0;font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:8px;white-space:nowrap}
.sc-full{color:var(--ok);background:var(--okbg)}
.sc-ph{color:var(--warn);background:var(--warnbg)}
.sc-list{color:var(--tx2);background:var(--graybg)}
.imgcnt{margin-left:auto;color:var(--accent);font-weight:600}.lede{font-size:.85rem;color:var(--tx2);margin:8px 0 0;padding:8px 10px;background:var(--chip);border-radius:8px}
.meta{font-size:.78rem;color:var(--tx2);margin:10px 0 0;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.meta .dot{margin:0 4px}
.xsum{font-size:.88rem;color:var(--tx2);margin:10px 0 0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{font-size:.72rem;color:var(--tx2);background:var(--chip);border-radius:6px;padding:2px 8px}
.acts{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;font-size:.83rem}
.acts a,.acts button{color:var(--accent);text-decoration:none;background:none;border:none;cursor:pointer;padding:0;font-size:.83rem;font-family:inherit}
.pager{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin:22px 0 8px}
.pg{border:1px solid var(--bd);background:var(--card);color:var(--tx2);border-radius:8px;padding:5px 12px;font-size:.85rem;cursor:pointer}
.pg.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.reader{position:fixed;inset:0;background:var(--bg);z-index:99;display:none;overflow-y:auto}
.reader.open{display:block}
.rwrap{max-width:720px;margin:0 auto;padding:18px 16px 60px}
.rbar{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center;z-index:2}
.rbar button{border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:8px;padding:6px 14px;cursor:pointer;font-size:.9rem}
.rmeta{font-size:.78rem;color:var(--tx2);margin:12px 0 4px;line-height:1.8}
.rmeta a{color:var(--accent)}
.rbody{font-family:Georgia,"Times New Roman",serif;font-size:1.02rem;line-height:1.85}
.rbody h1{font-size:1.3rem;line-height:1.35;margin:1.2em 0 .6em}
.rbody h2{font-size:1.15rem;margin:1.4em 0 .6em;font-family:-apple-system,sans-serif;border-bottom:1px solid var(--bd);padding-bottom:4px}
.rbody h3{font-size:1.02rem;margin:1.2em 0 .5em;font-family:-apple-system,sans-serif}
.rbody blockquote{margin:1em 0;padding:8px 14px;border-left:3px solid var(--accent);background:var(--chip);color:var(--tx2);border-radius:0 8px 8px 0}
.rbody ul,.rbody ol{margin:.6em 0;padding-left:1.4em}
.rbody li{margin:.3em 0}
.rbody code{background:var(--chip);border-radius:4px;padding:1px 6px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88em}
.rbody hr{border:none;border-top:1px solid var(--bd);margin:1.6em 0}
.rbody a{color:var(--accent)}
.rbody strong{font-weight:700}
.rbody p{margin:0 0 1.05em}
.empty{text-align:center;color:var(--tx2);padding:40px 0}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
<h1>📰 内容广场 <span style="font-size:.85rem;color:var(--tx2);font-weight:400">· 三报快照全文库</span></h1>
<div class="sub">纽约时报 / 华盛顿邮报 / 华尔街日报 · 2026 年快照存档 · 数据截至 2026-11-01 · 自动抽取进行中</div>
<div class="tabs">
<div class="tab on" data-f="all">全部</div>
<div class="tab" data-f="full">已抽全文</div>
<div class="tab" data-f="ph">仅有快照</div>
</div>
</header>
<div class="toolbar">
<input class="search" id="q" type="search" placeholder="搜索标题关键字…">
<div class="chips" id="chipsPaper">
<div class="chip on" data-v="all">全部报纸</div>
<div class="chip" data-v="NYT">纽约时报</div>
<div class="chip" data-v="WaPo">华盛顿邮报</div>
<div class="chip" data-v="WSJ">华尔街日报</div>
</div>
</div>
<div class="stat" id="stat"></div>
<div id="list"></div>
<div class="pager" id="pager"></div>
</div>
<div class="reader" id="reader">
<div class="rwrap">
<div class="rbar"><b id="rPaper"></b><button onclick="closeReader()">✕ 关闭</button></div>
<div class="rmeta" id="rMeta"></div>
<h1 id="rTitle" style="font-size:1.4rem;line-height:1.35"></h1>
<div class="rbody" id="rBody"></div>
</div>
</div>
<script>
const DATA = __DATA__;
const FULL = DATA.full, L = DATA.list;
let fTab="all", fPaper="all", kw="", page=1; const PS=15;
const PNAME={NYT:"纽约时报",WaPo:"华盛顿邮报",WSJ:"华尔街日报"};
const esc=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
function filtered(){
  return L.filter(a=>{
    if(fTab==="full"&&!a.full)return false;
    if(fTab==="ph"&&a.full)return false;
    if(fPaper!=="all"&&a.paper!==fPaper)return false;
    if(kw&&!(a.t+" "+a.u).toLowerCase().includes(kw))return false;
    return true;
  });
}
function badge(a){
  if(a.full)return '<span class="score sc-full">✅ 全文</span>';
  if(a.ph)return '<span class="score sc-ph">📷 有快照</span>';
  return '<span class="score sc-list">📋 仅清单</span>';
}
function card(a){
  const d=a.date?a.date.slice(5).replace("-","月")+"日":"—";
  const meta=`<span>文章</span><span class="dot">·</span><span>${PNAME[a.paper]||a.paper}</span><span class="dot">·</span><span>${esc(a.date)}</span>`+
    (a.full?`<span class="dot">·</span><span>${a.w} 词 (约 ${a.m} 分钟)</span>`:"");
  const tags=[`<span class="tag">${a.paper}</span>`];
  if(a.sec)tags.push(`<span class="tag">${esc(a.sec)}</span>`);
  tags.push('<span class="tag">英文</span>');
  if(a.ph)tags.push('<span class="tag">已存档</span>');
  const acts=[];
  if(a.full)acts.push(`<button onclick="openReader('${esc(a.u)}')">📖 阅读全文</button>`);
  acts.push(`<a href="${esc(a.u)}" target="_blank" rel="noopener">原文 ↗</a>`);
  if(a.ph)acts.push(`<a href="https://archive.ph/${esc(a.ph)}" target="_blank" rel="noopener">存档 ↗</a>`);
  const title=a.full?`<a href="javascript:void(0)" onclick="openReader('${esc(a.u)}')">${esc(a.t)}</a>`:`<a href="${esc(a.u)}" target="_blank" rel="noopener">${esc(a.t)}</a>`;
  const thumb=a.imgs&&a.imgs.length?`<img class="thumb" src="${esc(a.imgs[0])}" loading="lazy" alt="">`:"";
  return `<div class="card">${thumb}<div class="trow"><div class="title">${title}</div>${badge(a)}</div>`+
    (a.lede?`<div class="lede">⭐ ${esc(a.lede)}</div>`:"")+
    `<div class="meta">${meta}${a.imgs&&a.imgs.length?`<span class="imgcnt">📷 ${a.imgs.length}图</span>`:""}</div>`+
    (a.x&&!a.full?`<div class="xsum">${esc(a.x)}…</div>`:"")+
    `<div class="tags">${tags.join("")}</div><div class="acts">${acts.join("")}</div></div>`;
}
function render(){
  const fs=filtered();const pages=Math.max(1,Math.ceil(fs.length/PS));
  if(page>pages)page=1;const slice=fs.slice((page-1)*PS,page*PS);
  document.getElementById("stat").textContent=`共 ${fs.length} 条 · 第 ${page}/${pages} 页`;
  document.getElementById("list").innerHTML=slice.length?slice.map(card).join(""):'<div class="empty">没有匹配的内容</div>';
  let p=`<button class="pg" ${page<=1?"disabled":""} onclick="goto(${page-1})">上一页</button>`;
  const st=Math.max(1,page-3),en=Math.min(pages,st+6);
  for(let i=st;i<=en;i++)p+=`<button class="pg ${i===page?"on":""}" onclick="goto(${i})">${i}</button>`;
  if(en<pages)p+=`<span class="pg" style="border:none">… 共${pages}页</span>`;
  p+=`<button class="pg" ${page>=pages?"disabled":""} onclick="goto(${page+1})">下一页</button>`;
  document.getElementById("pager").innerHTML=p;
}
function goto(p){page=p;render();window.scrollTo(0,0);}
__MDJS__
function openReader(u){
  const a=L.find(x=>x.u===u),t=FULL[u]||"（正文缺失）";
  document.getElementById("rPaper").textContent=PNAME[a.paper]||a.paper;
  document.getElementById("rMeta").innerHTML=`${esc(a.date)} 发布 · ${a.w?a.w+" 词 · 约 "+a.m+" 分钟 · ":""}原文: <a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.slice(0,80))}…</a>${a.ph?` · 存档: <a href="https://archive.ph/${esc(a.ph)}" target="_blank" rel="noopener">archive.ph/${esc(a.ph)}</a>`:""}<br>来自快照全文抽取 · 质量提示：图片未保留，正文为纯文本版`;
  document.getElementById("rTitle").textContent=a.t;
  const a2=L.find(x=>x.u===u);
  let bodyMd=FULL[u]||"（正文缺失）";
  let imgsHtml="";
  const inlineImgs=bodyMd.includes("](img/");
  if(inlineImgs){
    bodyMd=bodyMd.split("](img/").join("](md/"+a2.paper+"/img/");
  } else if(a2&&a2.imgs&&a2.imgs.length){
    imgsHtml=`<div class="rimgs">${a2.imgs.map(p=>`<img src="${esc(p)}" loading="lazy" alt="文章配图">`).join("")}</div>`;
  }
  document.getElementById("rBody").innerHTML=imgsHtml+md(bodyMd);
  document.getElementById("reader").classList.add("open");
  window.scrollTo(0,0);
}
function closeReader(){document.getElementById("reader").classList.remove("open");}
document.getElementById("chipsPaper").addEventListener("click",e=>{const c=e.target.closest(".chip");if(!c)return;
  fPaper=c.dataset.v;document.querySelectorAll("#chipsPaper .chip").forEach(x=>x.classList.toggle("on",x===c));page=1;render();});
document.querySelectorAll(".tab").forEach(t=>t.addEventListener("click",()=>{
  fTab=t.dataset.f;document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("on",x===t));page=1;render();}));
document.getElementById("q").addEventListener("input",e=>{kw=e.target.value.trim().toLowerCase();page=1;render();});
render();
</script>
</body></html>'''

payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
mdjs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'md_renderer.js')
if not os.path.exists(mdjs_path):
    mdjs_path = os.path.join('D:' + chr(92) + 'three-papers-harvest', 'tools', 'md_renderer.js')
mdjs = open(mdjs_path, encoding='utf-8').read()
out = TEMPLATE.replace('__MDJS__', mdjs).replace('__DATA__', payload)
open('内容广场.html', 'w', encoding='utf-8').write(out)
print(f"生成完成: 内容广场.html {os.path.getsize('内容广场.html'):,} bytes")
