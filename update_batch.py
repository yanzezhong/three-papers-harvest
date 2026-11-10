# -*- coding: utf-8 -*-
"""本轮收尾：把已落盘的 6 篇 WaPo md 登记进 harvest.db"""
import sqlite3, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = r'D:\three-papers-harvest\harvest.db'
MD = r'D:\three-papers-harvest\md\WaPo'
P = '华盛顿邮报 WaPo'
items = [
    ('https://www.washingtonpost.com/politics/2026/10/25/alaska-senate-candidate-mary-peltola-reschedules-events-after-car-crash/',
     '2026-10-25_Alaska-Senate-candidate-Mary-Peltola-reschedules-events-after-car-crash.md'),
    ('https://www.washingtonpost.com/politics/2026/10/25/scott-colom-black-democrat-has-chance-win-mississippis-senate-race/',
     '2026-10-25_Scott-Colom-a-Black-Democrat-has-a-chance-to-win-in-Mississippis-Senate-race.md'),
    ('https://www.washingtonpost.com/politics/2026/10/25/trump-escalates-campaign-rhetoric-calling-el-sayed-jihadist/',
     '2026-10-25_Trump-escalates-campaign-rhetoric-calling-El-Sayed-a-jihadist.md'),
    ('https://www.washingtonpost.com/politics/2026/10/25/todd-blanche-defends-doj-lawsuit-over-senate-election-alaska/',
     '2026-10-25_Todd-Blanche-defends-DOJ-lawsuit-over-Senate-election-in-Alaska.md'),
    ('https://www.washingtonpost.com/politics/2026/10/25/trump-michigan-elsayed-rogers-senate-midterms/a5a25674-d06f-11f1-9931-2a41b76fc976_story.html',
     '2026-10-25_Trumps-midterm-swing-brings-him-to-Michigan-as-Republicans-aim-to-underm.md'),
    ('https://www.washingtonpost.com/politics/2026/10/25/demetre-daskalakis-left-cdc-fight-rfk-jr-did-he-make-right-call/',
     '2026-10-25_Demetre-Daskalakis-left-the-CDC-to-fight-RFK-Jr-Did-he-make-the-right-call.md'),
]
con = sqlite3.connect(DB)
cur = con.cursor()
for url, fn in items:
    path = os.path.join(MD, fn)
    size = os.path.getsize(path)
    cur.execute('UPDATE articles2026 SET md_path=?, content_chars=? WHERE url=?', (path, size, url))
    print('UPDATE rows=%d  %s  %dB' % (cur.rowcount, fn, size))
    cur.execute('INSERT OR REPLACE INTO contents(url,paper,md_path,chars) VALUES (?,?,?,?)', (url, P, path, size))
con.commit()
cur.execute('SELECT COUNT(*) FROM articles2026 WHERE md_path IS NOT NULL')
print('已抽取总数:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM articles2026 WHERE ph_hit=1 AND md_path IS NULL')
print('剩余待抽取:', cur.fetchone()[0])
con.close()
