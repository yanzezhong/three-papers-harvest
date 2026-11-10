"""三报图片下载器 — 独立脚本模式（零 token）v2（并行版）
- 4 线程并行下载 pending 图片，经代理落到 md/<报纸>/img/<文章目录>/
- WaPo/WSJ：无图片记录时先用 r.jina.ai 读原文收集图片 URL（解析 imrs.php 的 src= 参数取原图）
- 每张下载成功后调用 inline_images.py 将图片内联进正文
- 每轮结束刷新内容广场
- 限额：下载 ≤60 张，jina ≤15 次，运行 ≤9 分钟
"""
import sqlite3, os, sys, subprocess, re, time, json, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"D:\three-papers-harvest"
DB = os.path.join(BASE, "harvest.db")
PROXY = "http://127.0.0.1:7890"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
LIMIT_DL = 400
LIMIT_JINA = 15
BUDGET_S = 540
WORKERS = 4
PAPER_DIR = {"纽约时报 NYT": "NYT", "华盛顿邮报 WaPo": "WaPo", "华尔街日报 WSJ": "WSJ"}
T0 = time.time()

def log(*a):
    print(time.strftime("%H:%M:%S"), *a, file=sys.stderr, flush=True)

def curl_download(url, out_path, timeout=60):
    r = subprocess.run(["curl", "-sL", "-x", PROXY, "-m", str(timeout), "--connect-timeout", "10",
                        "-A", UA, "-o", out_path, "-w", "%{http_code}", url],
                       capture_output=True, timeout=timeout + 20)
    code = r.stdout.decode().strip()
    if code == "200" and os.path.exists(out_path) and os.path.getsize(out_path) > 2048:
        with open(out_path, "rb") as f:
            magic = f.read(12)
        if magic[:3] == b"\xff\xd8\xff" or magic[:8] == b"\x89PNG\r\n\x1a\n" or magic[:3] == b"GIF" or magic[4:8] in (b"ftyp",) or (magic[:4] == b"RIFF" and magic[8:12] == b"WEBP"):
            return True
    if os.path.exists(out_path):
        os.remove(out_path)
    return False

def jina(url):
    r = subprocess.run(["curl", "-sL", "-x", PROXY, "-m", "90", "-A", UA,
                        f"https://r.jina.ai/{url}"], capture_output=True, timeout=110)
    return r.stdout.decode("utf-8", "ignore")

def collect_wapo_wsj_urls(article_url):
    txt = jina(article_url)
    if "One more step" in txt or len(txt) < 500:
        return []
    urls = re.findall(r'!\[[^\]]*\]\((https?://[^)]+)\)', txt)
    out = []
    for u in urls:
        u = u.strip()
        if u.startswith("data:"):
            continue
        if "imrs.php" in u and "src=" in u:
            m = re.search(r'src=([^&]+)', u)
            if m:
                orig = urllib.parse.unquote(m.group(1))
                if orig.startswith("http"):
                    out.append(orig)
                continue
        if re.search(r'\.(jpg|jpeg|png|webp|gif)(\?|$)', u, re.I):
            out.append(u)
    seen, dedup = set(), []
    for u in out:
        if u not in seen:
            seen.add(u); dedup.append(u)
    return dedup[:15]

db = sqlite3.connect(DB, timeout=30)
db.execute("ALTER TABLE images ADD COLUMN note TEXT") if not [r for r in db.execute("PRAGMA table_info(images)") if r[1] == 'note'] else None
db.row_factory = sqlite3.Row
meta = {r["url"]: r for r in db.execute("SELECT url, paper, pub_date, title FROM articles2026")}

def slugify(t, n=6):
    words = re.findall(r"[A-Za-z0-9]+", t or "")
    slug = "-".join(w.lower() for w in words[:n])
    return (slug or "article")[:60]

def article_dir(paper, pub_date, title):
    pdir = PAPER_DIR.get(paper, "NYT")
    d = os.path.join(BASE, "md", pdir, "img", f"{pub_date}_{slugify(title)}")
    os.makedirs(d, exist_ok=True)
    return d

# ============ A. WaPo/WSJ 图片 URL 收集（jina，零 token） ============
jina_used = 0
pending_papers = db.execute("""
 SELECT DISTINCT a.paper FROM articles2026 a
 WHERE a.md_path IS NOT NULL
   AND (a.paper LIKE '%WaPo%' OR a.paper LIKE '%WSJ%')
   AND NOT EXISTS(SELECT 1 FROM images i WHERE i.article_url=a.url)
 ORDER BY a.pub_date DESC LIMIT ?""", (LIMIT_JINA,)).fetchall()
for (paper,) in pending_papers:
    if jina_used >= LIMIT_JINA or time.time() - T0 > BUDGET_S:
        break
    rows = db.execute("""SELECT url, pub_date, title FROM articles2026
        WHERE paper=? AND md_path IS NOT NULL
        AND NOT EXISTS(SELECT 1 FROM images i WHERE i.article_url=articles2026.url)
        ORDER BY pub_date DESC LIMIT 5""", (paper,)).fetchall()
    if not rows:
        continue
    log(f"[jina收集] {paper} {len(rows)} 篇")
    for r in rows:
        if jina_used >= LIMIT_JINA or time.time() - T0 > BUDGET_S:
            break
        urls = collect_wapo_wsj_urls(r["url"])
        jina_used += 1
        if urls:
            db.executemany("INSERT OR IGNORE INTO images(paper,article_url,img_url,status,added_at) VALUES(?,?,?,'pending',datetime('now'))",
                           [(paper, r["url"], u) for u in urls])
            db.commit()
            log(f"  +{len(urls)} 图片URL | {r['title'][:40]}")
        else:
            db.execute("INSERT OR IGNORE INTO images(paper,article_url,img_url,status,added_at) VALUES(?,?,?,'no_images',datetime('now'))",
                       (paper, r["url"], "NONE"))
            db.commit()

# ============ B. 预标记已知不可下载项 ============
MEDIA_RE = re.compile(r'/[^/]+/[0-9a-f]{20,}\.(avif|webp|jpe?g|png|gif)$', re.I)

def is_archive_junk(u):
    """archive.ph 站内素材判定：/o/ 代理形式与哈希缓存媒体(<ID>/<40位hex>.<ext>)均属真实图片，放行。"""
    low = u.lower()
    if "archive.ph" not in low and "archive.today" not in low:
        return False
    if "/o/" in low:
        return False
    if "scr.png" in low:
        return True
    return not MEDIA_RE.search(u)

for r0 in db.execute("SELECT id, img_url FROM images WHERE status='pending' AND img_url!='NONE'").fetchall():
    low0 = r0["img_url"].lower()
    if is_archive_junk(r0["img_url"]):
        db.execute("UPDATE images SET status='failed', note='archive内部资源' WHERE id=?", (r0["id"],))
    elif "px.washingtonpost" in low0 or "generic-newsletter" in low0:
        db.execute("UPDATE images SET status='failed', note='追踪像素' WHERE id=?", (r0["id"],))
db.commit()

# ============ C. 构建下载任务（主线程生成路径） ============
pend = db.execute("""SELECT i.id, i.paper, i.article_url, i.img_url FROM images i
 WHERE i.status='pending' AND i.img_url != 'NONE'
 ORDER BY i.id LIMIT ?""", (LIMIT_DL,)).fetchall()
log(f"[下载] pending {len(pend)} 张, {WORKERS} 线程并行")
tasks = []
for r in pend:
    if time.time() - T0 > BUDGET_S:
        log("时间预算用尽"); break
    lowu = r["img_url"].lower()
    if is_archive_junk(r["img_url"]):
        db.execute("UPDATE images SET status='failed', note='archive内部资源' WHERE id=?", (r["id"],)); continue
    if "px.washingtonpost" in lowu or "generic-newsletter" in lowu:
        db.execute("UPDATE images SET status='failed', note='追踪像素' WHERE id=?", (r["id"],)); continue
    m = meta.get(r["article_url"])
    paper = r["paper"] or (m["paper"] if m else "NYT")
    pub = (m["pub_date"] if m else "") or "nodate"
    title = (m["title"] if m else "") or "article"
    d = article_dir(paper, pub, title)
    ext = ".jpg"
    m2 = re.search(r'\.(jpe?g|png|webp|gif)(?:\?|$)', r["img_url"], re.I)
    if m2: ext = "." + m2.group(1).lower()
    idx = db.execute("SELECT COUNT(*) FROM images WHERE article_url=? AND local_path IS NOT NULL",
                     (r["article_url"],)).fetchone()[0] + 1
    out = os.path.join(d, f"{idx:02d}{ext}")
    tasks.append((r["id"], r["article_url"], r["img_url"], out))
db.commit()

# ============ D. 并行下载 ============
ok = fail = 0
results = []
if tasks:
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(curl_download, t[2], t[3], 60): t for t in tasks}
        for fut in as_completed(futs):
            tid, aurl, url, out = futs[fut]
            try:
                okd = fut.result()
            except Exception:
                okd = False
            results.append((tid, aurl, url, okd, out))
            log(f"  {'✅' if okd else '❌'} {os.path.basename(out)} ({os.path.getsize(out):,}B)" if okd else f"  ❌ {url[:70]}")

# ============ E. 主线程写库 + 受影响文章统一内联 ============
affected = set()
for tid, aurl, url, okd, out in results:
    if okd:
        db.execute("UPDATE images SET status='downloaded', local_path=? WHERE id=?", (out, tid))
        ok += 1; affected.add(aurl)
    else:
        px = db.execute("SELECT proxied_url FROM images WHERE id=?", (tid,)).fetchone()[0]
        if px and curl_download(px, out, timeout=90):
            db.execute("UPDATE images SET status='downloaded', local_path=? WHERE id=?", (out, tid))
            ok += 1; affected.add(aurl); log(f"  ✅(archive代理) {os.path.basename(out)}")
        else:
            db.execute("UPDATE images SET status='failed' WHERE id=?", (tid,))
            fail += 1
db.commit()
for u in affected:
    try:
        subprocess.run([sys.executable, os.path.join(BASE, "tools", "inline_images.py"), u],
                       capture_output=True, timeout=120)
    except Exception:
        pass
if affected:
    log(f"[内联] {len(affected)} 篇文章已重排")

st = db.execute("SELECT status, COUNT(*) FROM images GROUP BY status").fetchall()
log("图片状态:", dict(st))
st2 = db.execute("SELECT COUNT(*) FROM images WHERE status='pending'").fetchone()[0]
db.close()

# ============ F. 每轮结束刷新内容广场 ============
try:
    for g in ("gen_plaza_data.py", "gen_plaza_html.py"):
        subprocess.run(["python", os.path.join(BASE, "tools", g)], capture_output=True, cwd=BASE, timeout=180)
    log("内容广场已刷新")
except Exception as _e:
    log("广场刷新失败:", str(_e)[:80])
print(json.dumps({"type": "complete", "ok": True, "summary": f"downloaded={ok} failed={fail} pending_left={st2}"}), flush=True)
