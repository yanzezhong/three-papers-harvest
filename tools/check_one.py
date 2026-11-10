# -*- coding: utf-8 -*-
import sqlite3, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
con = sqlite3.connect(r'D:\three-papers-harvest\harvest.db')
c = con.cursor()
r = c.execute('SELECT md_path,content_chars FROM articles2026 WHERE rowid=213').fetchone()
print('DB row213:', r)
print('文件存在:', os.path.exists(r[0]) if r and r[0] else False)
if r and r[0]:
    print('文件大小:', os.path.getsize(r[0]))
r2 = c.execute("SELECT chars FROM contents WHERE url LIKE '%kibriyaa%'").fetchone()
print('contents表:', r2)
print('待抽取:', c.execute('SELECT COUNT(*) FROM articles2026 WHERE ph_hit=1 AND md_path IS NULL').fetchone()[0])
con.close()
