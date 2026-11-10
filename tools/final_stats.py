# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
con = sqlite3.connect(r'D:\three-papers-harvest\harvest.db')
c = con.cursor()
print('总文章:', c.execute('SELECT COUNT(*) FROM articles2026').fetchone()[0])
print('已有md:', c.execute('SELECT COUNT(*) FROM articles2026 WHERE md_path IS NOT NULL').fetchone()[0])
print('待抽取:', c.execute('SELECT COUNT(*) FROM articles2026 WHERE ph_hit=1 AND md_path IS NULL').fetchone()[0])
print('待抽取按日期:')
for r in c.execute("SELECT pub_date, COUNT(*) FROM articles2026 WHERE ph_hit=1 AND md_path IS NULL GROUP BY pub_date ORDER BY pub_date DESC"):
    print(' ', r)
print('已扫列表页:', c.execute('SELECT COUNT(*) FROM listings_scanned').fetchone()[0])
print('需图片回填(有md无images):', c.execute('SELECT COUNT(*) FROM articles2026 WHERE md_path IS NOT NULL AND url NOT IN (SELECT DISTINCT article_url FROM images)').fetchone()[0])
print('本轮新增列表页:', c.execute("SELECT COUNT(*) FROM listings_scanned WHERE scanned_at LIKE '2026-11-02 2%'").fetchone()[0])
con.close()
