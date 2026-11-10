# -*- coding: utf-8 -*-
"""登记一篇已抽取文章: UPDATE articles2026 + INSERT contents"""
import sqlite3, sys, os

DB = r'D:\three-papers-harvest\harvest.db'
url = sys.argv[1]
md_path = sys.argv[2]

size = os.path.getsize(md_path)
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('UPDATE articles2026 SET md_path=?, content_chars=? WHERE url=?', (md_path, size, url))
if c.rowcount == 0:
    print('ERROR: no article row for', url)
    sys.exit(1)
row = c.execute('SELECT paper FROM articles2026 WHERE url=?', (url,)).fetchone()
c.execute('INSERT OR REPLACE INTO contents(url,paper,md_path,chars) VALUES(?,?,?,?)',
          (url, row[0], md_path, size))
conn.commit()
print('OK', url[:60], 'bytes=', size)
conn.close()
