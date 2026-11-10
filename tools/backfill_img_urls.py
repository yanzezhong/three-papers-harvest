# -*- coding: utf-8 -*-
"""零 token 图片URL回填：curl 抓 archive.ph 快照页 HTML，解析 img src 入 images 表。
用法: python backfill_img_urls.py [起始序号] [数量]
"""
import sqlite3, sys, io, re, os, time, json, subprocess, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = sys.stdout
BASE = r"D:\three-papers-harvest"
DB = os.path.join(BASE, "harvest.db")
PROXY = "http://127.0.0.1:7890"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
SLEEP = 1.5

def classify(u):
    """与 insert_images.py 一致：/o/ 形式还原原始URL存 img_url，整条存 proxied_url"""
    m = re.match(r'^https?://[^/]+/o/[^/]+/(.+)$', u)
    if m and not re.search(r'\.(avif|webp|jpe?g|png|gif)(\?|$)', u.split('/o/')[-1]):
        return m.group(1), u
    if m and not re.match(r'^[0-9a-f]{40}\.(avif|webp|jpe?g|png|gif)$', u.rsplit('/', 1)[-1]):
        return m.group(1), u
    return u, ''

def fetch(url):
    r = subprocess.run(["curl", "-sL", "-x", PROXY, "-m", "50", "--connect-timeout", "10",
                        "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, timeout=70)
    out = r.stdout.decode("utf-8", "ignore")
    body, _, code = out.rpartition("\n")
    return body if code.strip() == "200" else None

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    con = sqlite3.connect(DB, timeout=30)
    cur = con.cursor()
    rows = cur.execute("""SELECT a.url, a.ph_id, a.paper, a.title FROM articles2026 a
        WHERE a.md_path IS NOT NULL AND NOT EXISTS (SELECT 1 FROM images i WHERE i.article_url = a.url)
        ORDER BY a.pub_date DESC""").fetchall()
    batch = rows[start:start + limit]
    print(f"待回填总数 {len(rows)}，本批 {len(batch)}（{start}~{start+len(batch)-1}）")
    done = fail = 0
    for idx, (url, ph_id, paper, title) in enumerate(batch):
        snap = f"https://archive.ph/{ph_id}" if ph_id else f"https://archive.ph/newest/{url}"
        html = fetch(snap)
        if not html:
            print(f"[{start+idx}] FETCH_FAIL {title[:50]}")
            fail += 1
            time.sleep(SLEEP)
            continue
        srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)', html)
        urls, seen = [], set()
        for s in srcs:
            if not s or s.startswith("data:"):
                continue
            if s.startswith("/"):
                s = "https://archive.ph" + s
            elif s.startswith("//"):
                s = "https:" + s
            if s not in seen:
                seen.add(s)
                urls.append(s)
        if not urls:
            cur.execute("INSERT OR IGNORE INTO images(paper,article_url,img_url,status,added_at) VALUES(?,?,?,'no_images',datetime('now'))",
                        (paper, url, "NONE"))
            con.commit()
            print(f"[{start+idx}] NO_IMAGES {title[:50]}")
        else:
            n = 0
            for u in urls:
                img_url, proxied = classify(u)
                cur.execute("INSERT OR IGNORE INTO images(paper,article_url,img_url,proxied_url,local_path,status) VALUES (?,?,?,?,NULL,'pending')",
                            (paper, url, img_url, proxied))
                n += max(cur.rowcount, 0)
            con.commit()
            print(f"[{start+idx}] +{n} {title[:50]}")
        done += 1
        time.sleep(SLEEP)
    print(f"完成 {done} 篇，抓取失败 {fail} 篇")
    con.close()

if __name__ == '__main__':
    main()
