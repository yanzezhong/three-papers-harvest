# -*- coding: utf-8 -*-
"""把图片URL列表插入 images 表。用法: python insert_images.py <article_url> <paper> <urls_json_file>
JSON 文件内容为字符串数组。data: 开头自动跳过。/o/<ID>/<原始URL> 形式还原原始URL存 img_url，整条存 proxied_url；
哈希缓存形式(<子域>.archive.ph/<ID>/<hash>.<ext>)存 img_url，proxied_url=''。
"""
import sqlite3, sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DB = r'D:\three-papers-harvest\harvest.db'

def classify(u):
    m = re.match(r'^https?://[^/]+/o/[^/]+/(.+)$', u)
    if m and not re.search(r'\.(avif|webp|jpe?g|png|gif)(\?|$)', u.split('/o/')[-1]):
        # /o/ 形式且尾段不是纯哈希文件名 → 还原原始 URL
        return m.group(1), u
    if m and not re.match(r'^[0-9a-f]{40}\.(avif|webp|jpe?g|png|gif)$', u.rsplit('/',1)[-1]):
        return m.group(1), u
    return u, ''

def main():
    article_url, paper = sys.argv[1], sys.argv[2]
    urls = json.load(open(sys.argv[3], encoding='utf-8'))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for u in urls:
        if not u or u.startswith('data:'):
            continue
        img_url, proxied = classify(u)
        cur.execute('INSERT OR IGNORE INTO images(paper,article_url,img_url,proxied_url,local_path,status) VALUES (?,?,?,?,NULL,\'pending\')',
                    (paper, article_url, img_url, proxied))
        n += cur.rowcount if cur.rowcount > 0 else 0
    con.commit()
    con.close()
    print('IMAGES_INSERTED', n)

if __name__ == '__main__':
    main()
