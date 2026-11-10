"""把已下载的图片内联插入到对应文章的 markdown 正文里。
用法：
  python inline_images.py                处理所有已下载图片但未内联的文章
  python inline_images.py <url>          只处理指定文章（下载器每张下载后调用，做全篇重排）
  python inline_images.py --reall        全量重排（剥离旧图行，按 v2 规则重新分布）
规则 v2：
  - 跳过标题与署名段（前 2 段），图片从第 3 段开始按文档顺序均匀分布
  - 幂等：非 --reall 模式下，正文已含 ](img/ 引用的文章自动跳过
"""
import sqlite3, os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
BASE = r"D:\three-papers-harvest"
RELALL = "--reall" in sys.argv
db = sqlite3.connect(os.path.join(BASE, "harvest.db"))
db.row_factory = sqlite3.Row
FM = re.compile(r'\A(---\n.*?\n---\n)(.*)\Z', re.S)

def rel(img_path, md_path):
    return os.path.relpath(img_path, os.path.dirname(md_path)).replace(os.sep, '/')

def strip_refs(pp):
    out = pp
    while True:
        i = out.find("![](")
        if i == -1:
            return out
        j = out.find(")", i)
        if j == -1:
            return out
        out = out[:i] + out[j+1:]

def relayout(url):
    a = db.execute("SELECT paper, url, md_path, title FROM articles2026 WHERE url=?", (url,)).fetchone()
    if not a or not a["md_path"] or not os.path.exists(a["md_path"]):
        return "skip:no_md"
    seen, imgs = set(), []
    for r in db.execute(
        "SELECT local_path FROM images WHERE article_url=? AND status='downloaded' AND local_path IS NOT NULL ORDER BY id", (url,)):
        if r["local_path"] not in seen:
            seen.add(r["local_path"]); imgs.append(r["local_path"])
    if not imgs:
        return "skip:no_imgs"
    md_abs = a["md_path"]
    text = open(md_abs, encoding="utf-8").read()
    m = FM.match(text)
    fm = m.group(1) if m else ""
    body = text[len(fm):]
    # 每次都全量重排（幂等）：先剥离旧图行再按最新下载集合重新插入
    # 剥离所有已插入的图片引用（含嵌在段落内的），再按 v2 规则插入
    paras = body.split("\n\n")
    paras = [strip_refs(pp) for pp in paras]
    paras = [pp for pp in paras if pp]
    N, P = len(imgs), len(paras)
    if P == 0:
        return "skip:empty"
    new_paras = list(paras)
    start = 2 if P > 3 else 0   # 跳过标题与署名
    span = max(1, P - start)
    for k, img in enumerate(imgs):
        rel_ref = rel(img, md_abs)
        pos = start + (span * k) // N
        new_paras.insert(pos + k, f"![]({rel_ref})")
    new_body = "\n\n".join(new_paras)
    open(md_abs, "w", encoding="utf-8").write(fm + new_body)
    return f"inlined {N}"

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        print(relayout(sys.argv[1]))
    else:
        done = 0
        rows = db.execute("""SELECT DISTINCT i.article_url FROM images i
          JOIN articles2026 a ON a.url = i.article_url
          WHERE i.status='downloaded' AND i.local_path IS NOT NULL""").fetchall()
        for (u,) in rows:
            res = relayout(u)
            done += 1
            print(f"{res:16} {u[:70]}")
        print(f"处理完成: {done} 篇")
