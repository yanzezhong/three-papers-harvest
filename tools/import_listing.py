# -*- coding: utf-8 -*-
"""列表页条目导入：python import_listing.py <json_path>
JSON: {"paper":..., "pub_date":..., "listing_url":..., "note":..., "articles":[{"url","title","ph_id"}]}
"""
import json, sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    con = sqlite3.connect(r'D:\three-papers-harvest\harvest.db')
    c = con.cursor()
    n = 0
    for a in d['articles']:
        cur = c.execute(
            'INSERT OR IGNORE INTO articles2026(paper,url,pub_date,title,ph_hit,ph_id,src) VALUES(?,?,?,?,1,?,?)',
            (d['paper'], a['url'], d['pub_date'], a['title'], a.get('ph_id'), d.get('src','archive.ph列表页')))
        n += cur.rowcount if cur.rowcount > 0 else 0
    if d.get('listing_url'):
        c.execute('INSERT INTO listings_scanned(listing_url,scanned_at,note) VALUES(?,datetime("now","localtime"),?)',
                  (d['listing_url'], d.get('note','')))
    con.commit()
    print('新增条目:', n)
    print('待抽取总数:', c.execute('SELECT COUNT(*) FROM articles2026 WHERE ph_hit=1 AND md_path IS NULL').fetchone()[0])
    con.close()

if __name__ == '__main__':
    main(sys.argv[1])
