import sqlite3, json, re, os, sys, html
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"D:\three-papers-harvest"
# 无锁只读（immutable）：快照库为展示用途，接受读取瞬间的一致性
ro = "file:" + os.path.join(BASE, "harvest.db").replace(chr(92), "/") + "?immutable=1"
db = sqlite3.connect(ro, uri=True)
db.row_factory = sqlite3.Row

PAPER_EN = {"纽约时报 NYT": "NYT", "华盛顿邮报 WaPo": "WaPo", "华尔街日报 WSJ": "WSJ"}

def clean_text(t):
    t = re.sub(r'^---.*?---\s*', '', t, flags=re.S)      # 去 YAML
    t = re.sub(r'\n?---\s*$', '', t.strip())
    return t.strip()

def section_of(url, paper):
    try:
        path = url.split('/')[3:]
        if paper == "NYT" and len(path) > 4:
            return path[3].replace('-', ' ')
        if paper == "WaPo":
            for seg in path:
                if re.match(r'^[a-z-]+$', seg) and seg not in ('2026','2025','story.html') and not seg.isdigit():
                    return seg.replace('-', ' ')
    except Exception:
        pass
    return ""

articles, fulltexts = [], {}
img_rows = {}
for r in db.execute("SELECT article_url, local_path FROM images WHERE status='downloaded' AND local_path IS NOT NULL ORDER BY id"):
    img_rows.setdefault(r[0], []).append(r[1])
for r in db.execute("SELECT * FROM articles2026 ORDER BY pub_date DESC, paper"):
    p_en = PAPER_EN.get(r['paper'], r['paper'])
    has_md = bool(r['md_path'])
    excerpt = ""
    words = mins = 0
    if has_md and os.path.exists(r['md_path']):
        txt = clean_text(open(r['md_path'], encoding='utf-8').read())
        excerpt = re.sub(r'\s+', ' ', txt)[:320]
        words = max(1, round(r['content_chars'] / 6.2))
        mins = max(1, round(words / 220))
        fulltexts[r['url']] = txt
    imgs = [os.path.relpath(p, BASE).replace(os.sep, '/') for p in img_rows.get(r['url'], [])][:8]
    sec = section_of(r['url'], p_en)
    lede = excerpt.split('. ')[0][:180] if excerpt else ""
    articles.append({
        "paper": p_en, "date": r['pub_date'] or "", "t": r['title'],
        "u": r['url'], "ph": r['ph_id'] or "", "sec": sec,
        "full": 1 if has_md else 0, "w": words, "m": mins,
        "x": excerpt, "lede": lede, "imgs": imgs,
    })

data = {"list": articles, "full": fulltexts}
json.dump(data, open('plaza_data.json', 'w', encoding='utf-8'), ensure_ascii=False)

total = len(articles)
n_full = sum(a['full'] for a in articles)
print(f"数据: {total} 条 | 全文 {n_full} | 内嵌字符量约 {sum(len(a['x']) for a in articles) + sum(len(v) for v in fulltexts.values())}")
