# -*- coding: utf-8 -*-
"""生成只看纽约时报的预览页（纯静态 HTML，无 JS 依赖）"""
import sqlite3, os, sys, html, re
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\three-papers-harvest'
con = sqlite3.connect(os.path.join(BASE, 'harvest.db'))
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("""SELECT url, title, pub_date, md_path FROM articles2026
    WHERE paper LIKE '%NYT%' AND md_path IS NOT NULL
    ORDER BY pub_date DESC, title""").fetchall()

cards = []
n_with_img = 0
n_img_total = 0
for a in rows:
    cur2 = con.cursor()
    imgs = [r[0] for r in cur2.execute(
        "SELECT local_path FROM images WHERE article_url=? AND local_path IS NOT NULL ORDER BY id",
        (a['url'],))]
    rel = [os.path.relpath(p, BASE).replace(os.sep, '/') for p in imgs]
    body = ''
    if os.path.exists(a['md_path']):
        t = open(a['md_path'], encoding='utf-8', errors='ignore').read()
        if t.startswith('---'):
            i = t.find('\n---', 3)
            body = t[i + 4:] if i > 0 else t
        else:
            body = t
    if rel:
        # md 里的引用是 img/<stem>/01.jpg，预览页需加上 md/NYT/img/ 前缀（不能再带 stem）
        body = body.replace('](img/', '](md/NYT/img/')
    else:
        body = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', body)

    # 极简 markdown → HTML
    h = html.escape(body)
    h = re.sub(r'^### (.*)$', r'<h3>\1</h3>', h, flags=re.M)
    h = re.sub(r'^## (.*)$', r'<h2>\1</h2>', h, flags=re.M)
    h = re.sub(r'^# (.*)$', r'<h1>\1</h1>', h, flags=re.M)
    h = re.sub(r'^&gt; (.*)$', r'<blockquote>\1</blockquote>', h, flags=re.M)
    h = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', h)
    paras = []
    for p in re.split(r'\n{2,}', h):
        p = p.strip()
        if not p:
            continue
        paras.append(p if p.startswith('<') else '<p>' + p.replace('\n', '<br>') + '</p>')
    h = '\n'.join(paras)

    thumbs = ''.join(f'<img src="{html.escape(u)}" loading="lazy" alt="">' for u in rel[:5])
    if rel:
        n_with_img += 1
        n_img_total += len(rel)
    cards.append(f'''<details class="item">
<summary><span class="ttl">{html.escape(a['title'] or '')}</span>
<span class="meta">{a['pub_date']} · <b class="pill">{len(rel)} 图</b>
<a class="ext" href="{html.escape(a['url'])}" target="_blank" rel="noopener">原文 ↗</a></span>
{f'<span class="thumbs">{thumbs}</span>' if thumbs else ''}
</summary>
<div class="body">{h}</div>
</details>''')

doc = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>纽约时报 · 图文核对</title><style>
:root{{--bg:#f7f8fa;--card:#fff;--tx:#1c1e21;--tx2:#65676b;--bd:#e4e6eb;--ac:#1d6feb}}
@media (prefers-color-scheme:dark){{:root{{--bg:#101214;--card:#1b1d21;--tx:#e8eaed;--tx2:#9aa3af;--bd:#2a2e34;--ac:#5b9df7}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);font-family:-apple-system,"PingFang SC","Segoe UI",sans-serif;line-height:1.65}}
.wrap{{max-width:860px;margin:0 auto;padding:18px 14px 70px}}
h1.top{{font-size:1.3rem;margin:0 0 4px}}
.sub{{color:var(--tx2);font-size:.86rem;margin-bottom:16px}}
.item{{background:var(--card);border:1px solid var(--bd);border-radius:10px;margin-bottom:10px;overflow:hidden}}
.item summary{{padding:11px 14px;cursor:pointer;list-style:none}}
.item summary::-webkit-details-marker{{display:none}}
.ttl{{font-weight:600;font-size:.97rem;display:block}}
.meta{{display:block;color:var(--tx2);font-size:.79rem;margin-top:3px}}
.pill{{background:var(--ac);color:#fff;border-radius:9px;padding:1px 7px;font-weight:600}}
.ext{{color:var(--ac);text-decoration:none;margin-left:8px}}
.thumbs{{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}}
.thumbs img{{width:82px;height:60px;object-fit:cover;border-radius:6px;background:#ddd}}
.body{{padding:2px 16px 18px;border-top:1px solid var(--bd)}}
.body img{{max-width:100%;border-radius:8px;margin:14px 0;display:block}}
.body p{{font-size:.96rem}}
.body h1{{font-size:1.18rem}}.body h2{{font-size:1.05rem}}.body h3{{font-size:.98rem}}
blockquote{{border-left:3px solid var(--bd);margin:12px 0;padding:2px 12px;color:var(--tx2)}}
</style></head><body><div class="wrap">
<h1 class="top">纽约时报 · 图文核对</h1>
<div class="sub">共 {len(rows)} 篇 · 有图 {n_with_img} 篇 · 图片合计 {n_img_total} 张 · 点条目展开全文与配图</div>
{''.join(cards)}
</div></body></html>'''

out = os.path.join(BASE, 'nyt_preview.html')
open(out, 'w', encoding='utf-8').write(doc)
con.close()
print('生成', out, len(doc), 'bytes |', len(rows), '篇 | 有图', n_with_img, '| 图', n_img_total)
