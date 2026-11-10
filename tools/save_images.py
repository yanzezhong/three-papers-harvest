# -*- coding: utf-8 -*-
"""save_images.py — 把一篇文档的 img src 列表写入 images 表
用法: python save_images.py imgs.json   ({"paper":..., "article_url":..., "srcs":[...]})
规则: data: 开头或空值跳过; https://archive.ph/o/<ID>/<原始URL> 拆分存 img_url/proxied_url;
      其他形式原样存 img_url, proxied_url 为 NULL。UNIQUE(article_url,img_url) 忽略重复。
"""
import json, sys, sqlite3
from pathlib import Path
from datetime import date

DB = Path(r"D:\three-papers-harvest\harvest.db")

def split_src(src):
    p = src.split("/o/", 1)
    if len(p) == 2 and p[0].startswith("https://") and "archive.ph" in p[0]:
        return p[1], src          # 原始URL, 整条proxied
    return src, None

def main():
    d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    paper, aurl, srcs = d["paper"], d["article_url"], d["srcs"]
    rows, skipped = [], 0
    for s in srcs:
        s = (s or "").strip()
        if not s or s.startswith("data:"):
            skipped += 1
            continue
        img_url, proxied = split_src(s)
        if not img_url:
            skipped += 1
            continue
        rows.append((paper, aurl, img_url, proxied, "pending"))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    ins = 0
    for r in rows:
        cur.execute("INSERT OR IGNORE INTO images(paper,article_url,img_url,proxied_url,status,added_at) VALUES(?,?,?,?,?,?)",
                    (r[0], r[1], r[2], r[3], r[4], date.today().isoformat()))
        ins += cur.rowcount
    if not rows:
        cur.execute("INSERT OR IGNORE INTO images(paper,article_url,img_url,local_path,status,added_at) VALUES(?,?,NULL,NULL,'no_images',?)",
                    (paper, aurl, date.today().isoformat()))
        ins += cur.rowcount
    con.commit()
    total = cur.execute("SELECT COUNT(*) FROM images WHERE article_url=?", (aurl,)).fetchone()[0]
    con.close()
    print(json.dumps({"ok": True, "inserted": ins, "skipped": skipped, "total_for_article": total}, ensure_ascii=False))

if __name__ == "__main__":
    main()
