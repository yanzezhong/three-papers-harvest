# -*- coding: utf-8 -*-
"""把 browser_read 抓到的正文落盘并更新 harvest.db（绝对路径专用）"""
import sqlite3, sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = r'D:\three-papers-harvest\harvest.db'
MD_DIR = r'D:\three-papers-harvest\md'
PAPER_DIR = {'纽约时报 NYT': 'NYT', '华盛顿邮报 WaPo': 'WaPo', '华尔街日报 WSJ': 'WSJ'}

def slugify(title: str) -> str:
    s = re.sub(r'[^A-Za-z0-9\s-]', '', title)
    s = re.sub(r'\s+', '-', s.strip()).strip('-')
    return s[:80] or 'untitled'

def save(paper, url, pub_date, title, body, snapshot_url='', captures='', author=''):
    sub = PAPER_DIR.get(paper)
    if not sub:
        raise SystemExit('unknown paper: %s' % paper)
    fname = '%s_%s.md' % (pub_date, slugify(title))
    path = os.path.join(MD_DIR, sub, fname)
    fm = ['---',
          'paper: "%s"' % paper,
          'title: "%s"' % title.replace('"', '\\"'),
          'author: "%s"' % author,
          'published: "%s"' % pub_date,
          'original_url: "%s"' % url,
          'snapshot_url: "%s"' % snapshot_url,
          'snapshot_captures: "%s"' % captures,
          'harvested: "%s"' % __import__('datetime').datetime.now().isoformat(timespec='seconds'),
          'batch: "auto"',
          '---', '']
    content = '\n'.join(fm) + body.strip() + '\n'
    data = content.encode('utf-8')
    with open(path, 'wb') as f:
        f.write(data)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('UPDATE articles2026 SET md_path=?, content_chars=? WHERE url=?', (path, len(data), url))
    cur.execute('INSERT OR REPLACE INTO contents(url,paper,md_path,chars) VALUES (?,?,?,?)',
                (url, paper, path, len(data)))
    con.commit()
    con.close()
    print('SAVED', path, len(data), 'bytes, update_rows=', 1)

if __name__ == '__main__':
    # 参数: paper|url|pub_date|title|mdbody文件
    paper, url, pub_date, title, bodyfile = sys.argv[1:6]
    snap = sys.argv[6] if len(sys.argv) > 6 else ''
    caps = sys.argv[7] if len(sys.argv) > 7 else ''
    author = sys.argv[8] if len(sys.argv) > 8 else ''
    body = open(bodyfile, encoding='utf-8').read()
    save(paper, url, pub_date, title, body, snap, caps, author)
