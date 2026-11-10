# -*- coding: utf-8 -*-
"""save_article.py — 三报快照抽取：把一篇已抓到的正文写入 md 并更新 harvest.db
用法: python save_article.py payload.json
payload 字段: paper, url, pub_date, title, author, snapshot_url, content,
              slug(可选), note(可选: 存档页标题不同时说明), published_line(可选)
"""
import json, re, sys, sqlite3, datetime
from pathlib import Path
from urllib.parse import unquote

BASE = Path(r"D:\three-papers-harvest")
DB = BASE / "harvest.db"
MD = BASE / "md"
PAPER_DIR = {"纽约时报 NYT": "NYT", "华盛顿邮报 WaPo": "WaPo", "华尔街日报 WSJ": "WSJ"}

def slugify(s, fallback):
    s = unquote(s or "").strip()
    s = re.sub(r"\.html?$", "", s)          # 去掉 .html/.htm
    s = s.split("/")[-1] if "/" in s else s  # 取 URL 末段
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "", s)  # wapo uuid
    s = re.sub(r"[^0-9A-Za-z._-]+", "-", s).strip("-.")
    if len(s) < 3:                           # 用标题兜底
        t = re.sub(r"[^0-9A-Za-z]+", "-", fallback).strip("-").lower()
        s = t[:60].strip("-")
    return s[:80].strip("-.")

def main():
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if payload.get("content_file"):
        payload["content"] = Path(payload["content_file"]).read_text(encoding="utf-8")
    paper = payload["paper"]
    url = payload["url"]
    pub = payload["pub_date"]
    title = payload["title"]
    author = payload.get("author") or ""
    snap = payload["snapshot_url"]
    note = payload.get("note") or ""
    content = payload["content"].strip() + "\n"

    slug = slugify(payload.get("slug") or url, title)
    out = MD / PAPER_DIR[paper] / f"{pub}_{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    m = re.search(r"/(\d{14})/", snap)
    cap = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]} {m.group(1)[8:10]}:{m.group(1)[10:12]}:{m.group(1)[12:]}" if m else ""
    today = datetime.date.today().isoformat()

    fm = ["---",
          f"paper: {paper}",
          f'title: "{title.replace(chr(34), chr(39))}"',
          f'author: "{author.replace(chr(34), chr(39))}"',
          f"published: {pub}",
          f"original_url: {url}",
          f"snapshot_url: {snap}",
          f'snapshot_captures: "{cap}"',
          f"harvested: {today}",
          'batch: "auto"',
          "---", "", f"# {title}", ""]
    if note:
        fm += [f"*({note})*", ""]
    body = "\n".join(fm) + content
    out.write_text(body, encoding="utf-8", newline="\n")
    size = out.stat().st_size

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("UPDATE articles2026 SET md_path=?, content_chars=? WHERE url=?", (str(out), size, url))
    updated = cur.rowcount
    cur.execute("INSERT OR REPLACE INTO contents(url,paper,md_path,chars,extracted_at) VALUES(?,?,?,?,?)",
                (url, paper, str(out), size, today))
    con.commit(); con.close()
    print(json.dumps({"ok": True, "file": str(out), "bytes": size, "updated": updated}, ensure_ascii=False))

if __name__ == "__main__":
    main()
