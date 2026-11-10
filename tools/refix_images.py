# -*- coding: utf-8 -*-
"""图片层完整重建：重抓存档页 → 只取正文配图 → 按文章内唯一序号落盘 → 更新 images 表

用法:
  python refix_images.py [--limit N] [--only url]
  python refix_images.py --dry          只统计不下载
"""
import sqlite3, os, sys, re, subprocess, time, json, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, r'D:\three-papers-harvest\tools')
from bodyimg import body_images

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\three-papers-harvest'
DB = os.path.join(BASE, 'harvest.db')
PROXY = 'http://127.0.0.1:7890'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'
PAPER_DIR = {'纽约时报 NYT': 'NYT', '华盛顿邮报 WaPo': 'WaPo', '华尔街日报 WSJ': 'WSJ'}
CAP = 12
DRY = '--dry' in sys.argv
T0 = time.time()


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def fetch(url, timeout=60):
    r = subprocess.run(['curl', '-sL', '-x', PROXY, '-m', str(timeout), '--connect-timeout', '10',
                        '-A', UA, url], capture_output=True, timeout=timeout + 20)
    body = r.stdout.decode('utf-8', 'ignore')
    return body if len(body) > 5000 else None


def ext_of(url):
    m = re.search(r'\.(jpe?g|png|webp|avif|gif)(?:\?|$)', url, re.I)
    return '.' + m.group(1).lower() if m else '.jpg'


def download(url, out, timeout=60):
    r = subprocess.run(['curl', '-sL', '-x', PROXY, '-m', str(timeout), '--connect-timeout', '10',
                        '-A', UA, '-o', out, '-w', '%{http_code}', url],
                       capture_output=True, timeout=timeout + 20)
    code = r.stdout.decode().strip()
    if code == '200' and os.path.exists(out) and os.path.getsize(out) > 3072:
        with open(out, 'rb') as f:
            m = f.read(12)
        if (m[:3] == b'\xff\xd8\xff' or m[:8] == b'\x89PNG\r\n\x1a\n' or m[:3] == b'GIF'
                or m[4:8] == b'ftyp' or (m[:4] == b'RIFF' and m[8:12] == b'WEBP')):
            return True
    if os.path.exists(out):
        os.remove(out)
    return False



CUT_RE = re.compile(r'^#{1,4}\s*(Most Read|Most Popular|More stories|Related|More on|Read more|'
                    r'Trending|Recommended|More from|Sign up)', re.I | re.M)
JUNK_JINA = ('privacyoptions', 'pixel.png', 'cookielaw', 'author-service-images', '/logo', '.svg',
             'newsletter', 'avatar', 'sprite')


def jina_body_images(url, cap=CAP):
    """从 r.jina.ai 的 markdown 取正文图：在第一个推荐位标题前截断，并跳过列表项里的缩略图"""
    r = subprocess.run(['curl', '-sL', '-x', PROXY, '-m', '90', '-A', UA, 'https://r.jina.ai/' + url],
                       capture_output=True, timeout=110)
    t = r.stdout.decode('utf-8', 'ignore')
    if len(t) < 800 or 'tn_404page' in t or 'One more step' in t:
        return []
    m = CUT_RE.search(t)
    if m:
        t = t[:m.start()]
    out = []
    for line in t.splitlines():
        s = line.strip()
        if not s or s[0] in '*-+>':
            continue
        for u in re.findall(r'!\[[^\]]*\]\((https?://[^)]+)\)', s):
            if 'imrs.php' in u and 'src=' in u:
                mm = re.search(r'src=([^&]+)', u)
                if mm:
                    o = urllib.parse.unquote(mm.group(1))
                    if o.startswith('http'):
                        out.append(o)
                continue
            out.append(u)
    seen, ded = set(), []
    for u in out:
        low = u.lower()
        if any(j in low for j in JUNK_JINA):
            continue
        if u in seen:
            continue
        seen.add(u)
        ded.append(u)
    return ded[:cap]

def process_one(r, cap=CAP):
    """单篇：抓页 → 取正文图 → 落盘。返回 (url, paper, [(img_url, path, ok)], 状态)"""
    url, paper, md_path = r['url'], r['paper'], r['md_path']
    sub = PAPER_DIR.get(paper, 'NYT')
    stem = os.path.splitext(os.path.basename(md_path))[0]
    outdir = os.path.join(BASE, 'md', sub, 'img', stem)
    prefer_jina = ('WaPo' in paper) or ('WSJ' in paper)
    imgs = []
    html = fetch('https://archive.ph/newest/' + url) if not prefer_jina else None
    if html:
        imgs = body_images(html, cap=cap)
    if prefer_jina or len(imgs) < 2:
        j = jina_body_images(url, cap=cap)
        if len(j) > len(imgs):
            imgs = j
    if not imgs and not html:
        html = fetch('https://archive.ph/newest/' + url)
        if html:
            imgs = body_images(html, cap=cap)
    if not imgs:
        return url, paper, [], ('noimg' if (html or prefer_jina) else 'fetchfail')
    if DRY:
        return url, paper, [(u, None, True) for u in imgs], 'dry'
    os.makedirs(outdir, exist_ok=True)
    for old in os.listdir(outdir):
        try:
            os.remove(os.path.join(outdir, old))
        except OSError:
            pass
    targets = []
    for k, iu in enumerate(imgs, 1):
        if iu.startswith('//'):
            iu = 'https:' + iu
        elif iu.startswith('/'):
            iu = 'https://archive.ph' + iu
        targets.append((iu, os.path.join(outdir, f'{k:02d}{ext_of(iu)}')))
    res = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(download, iu, p): (iu, p) for iu, p in targets}
        for fut, (iu, p) in list(futs.items()):
            try:
                ok = fut.result()
            except Exception:
                ok = False
            res.append((iu, p, ok))
    res.sort(key=lambda x: x[1])
    return url, paper, res, 'ok'


def main():
    limit = None
    only = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1]

    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    q = "SELECT url, paper, md_path, title, ph_id FROM articles2026 WHERE md_path IS NOT NULL"
    if only:
        rows = cur.execute(q + " AND url = ?", (only,)).fetchall()
    else:
        rows = cur.execute(q + " ORDER BY pub_date DESC, url").fetchall()
    if '--paper' in sys.argv:
        want = sys.argv[sys.argv.index('--paper') + 1]
        rows = [r for r in rows if want in r['paper']]
    if limit:
        rows = rows[:limit]
    log(f'待处理文章 {len(rows)} 篇（4 篇并行）' + ('（DRY）' if DRY else ''))

    stat = {'ok': 0, 'noimg': 0, 'fetchfail': 0, 'imgs': 0, 'dlfail': 0}
    report = []
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(process_one, r): r for r in rows}
        for fut in as_completed(futs):
            r = futs[fut]
            url, paper = r['url'], r['paper']
            try:
                url, paper, res, status = fut.result()
            except Exception as e:
                log('EXC', url[:50], e); stat['fetchfail'] += 1; continue
            done += 1
            if status in ('fetchfail', 'noimg'):
                stat[status] += 1
                report.append({'url': url, 'res': status})
                if not DRY:
                    cur.execute("DELETE FROM images WHERE article_url=?", (url,))
                    if status == 'noimg':
                        cur.execute("INSERT INTO images(paper,article_url,img_url,status,added_at) VALUES(?,?,?,'no_images',datetime('now'))",
                                    (paper, url, 'NONE'))
                    con.commit()
                log(f'[{done}/{len(rows)}] {status.upper()} {url[:58]}')
                continue
            if DRY:
                stat['ok'] += 1; stat['imgs'] += len(res)
                log(f'[{done}/{len(rows)}] {len(res)} 张 {url[:58]}')
                continue
            cur.execute("DELETE FROM images WHERE article_url=?", (url,))
            good = 0
            for iu, p, ok in res:
                cur.execute("INSERT INTO images(paper,article_url,img_url,local_path,status,added_at) VALUES(?,?,?,?,?,datetime('now'))",
                            (paper, url, iu, p if ok else None, 'downloaded' if ok else 'failed'))
                good += 1 if ok else 0
            con.commit()
            stat['ok'] += 1
            stat['imgs'] += good
            stat['dlfail'] += len(res) - good
            report.append({'url': url, 'res': 'ok', 'n': len(res), 'good': good})
            log(f'[{done}/{len(rows)}] OK {good}/{len(res)} 图 {url[:55]}')

    con.close()
    log('统计:', json.dumps(stat, ensure_ascii=False), f'耗时 {time.time()-T0:.0f}s')
    json.dump(report, open(os.path.join(BASE, 'tmp', 'refix_report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
