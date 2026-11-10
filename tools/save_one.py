# -*- coding: utf-8 -*-
"""从 JSON 落盘一篇文章并更新库：python save_one.py <json>
JSON: {paper,url,pub_date,title,snapshot,captures,author,body}
"""
import json, sys
sys.path.insert(0, r'D:\three-papers-harvest')
from save_article import save  # save_article 自行包装 stdout

d = json.load(open(sys.argv[1], encoding='utf-8'))
save(d['paper'], d['url'], d['pub_date'], d['title'], d['body'],
     d.get('snapshot',''), d.get('captures',''), d.get('author',''))
