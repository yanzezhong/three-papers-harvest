# 三报快照抽取（three-papers-harvest）

从 **archive.today / archive.ph** 的快照里，把《纽约时报》《华盛顿邮报》《华尔街日报》2026 年的文章
**正文 + 配图**抽成 Markdown 与结构化数据库，并生成可浏览的"内容广场"页面。

本仓库只收录**代码与文档**；正文、图片、数据库属于数据产物，不进 Git（见 `.gitignore`）。

---

## 1. 数据在哪

| 内容 | 位置 |
|---|---|
| 数据库 | `D:\three-papers-harvest\harvest.db`（SQLite） |
| 正文 Markdown | `md\NYT\`、`md\WaPo\`、`md\WSJ\` |
| 文章配图 | `md\<报纸>\img\<与 md 同名的目录>\01.jpg…` |
| 内容广场页面 | `内容广场.html`（自包含，需从项目根目录提供服务） |

### 数据表

```
articles2026(paper, url, pub_date, title, ph_hit, ph_id, md_path, content_chars, src)
contents(url, paper, md_path, chars)
listings_scanned(listing_url, scanned_at, note)
images(paper, article_url, img_url, proxied_url, local_path, status, note)
```

`images.status`：`downloaded`（已落盘）/ `pending`（待下载）/ `failed`（取不到）/
`no_images`（原文确认无配图）。

---

## 2. 处理流水线

```
archive.ph 列表页  ──►  articles2026（待抽取清单）
                          │
                    ┌─────┴─────┐
                    │  正文抽取  │  archive.ph/<快照ID> 或 /newest/<原文URL>
                    └─────┬─────┘
                          ▼
                 md/<报纸>/<日期>_<标题slug>.md
                          │
                    ┌─────┴─────┐
                    │  图片采集  │  正文容器内 <figure> 图（NYT）/ jina 通道（WaPo、WSJ）
                    └─────┬─────┘
                          ▼
                images 表 ──► 下载 ──► md/<报纸>/img/<文章目录>/01.jpg
                          │
                    ┌─────┴─────┐
                    │  图片内联  │  inline_images.py 按段落均匀插入
                    └─────┬─────┘
                          ▼
                内容广场.html（筛选/搜索/阅读）
```

### 2.1 正文抽取

- 有快照 ID → `https://archive.ph/<ph_id>`；没有 → `https://archive.ph/newest/<原文URL>`
- 用浏览器插件（`my-browser`）读取 `mode=content, maxChars≈14000`，长文用 30000 重取
- 落盘格式：YAML front matter（paper / title / author / published / original_url /
  snapshot_url / harvested / batch）+ 完整正文
- 成功后写回 `md_path`、`content_chars`，并插入 `contents`
- 遇到 "One more step" / CAPTCHA / 403 → 通知人工过验证，本轮停止

### 2.2 图片采集与下载

**采集（取 URL）**

- NYT：`tools/bodyimg.py` 解析存档页，取 `<article>` 内 `<figure>` 的图
- WaPo / WSJ：存档页往往只剩首图，改用 `r.jina.ai` 的 markdown，在第一个
  "Most Read / Related" 标题前截断，并跳过列表项里的推荐位缩略图
- 过滤规则：cookie 横幅 logo、作者头像、追踪像素、`scr.png`、`square640` 缩略图、`data:` 内联图

**下载**

- `tools/img_downloader.py`：4 线程 + 代理，校验 HTTP 200 与文件头（JPEG/PNG/GIF/WebP/AVIF），
  小于 3KB 视为图标丢弃；每轮限额下载 400 张
- 零 token：全部走 curl，不占浏览器额度

### 2.3 内联与展示

- `tools/inline_images.py`：剥离旧图引用后按 v2 规则重排（跳过标题/署名，剩余段落均匀分布），幂等
- `tools/gen_plaza_data.py` + `gen_plaza_html.py`：生成自包含的 `内容广场.html`（深色模式、筛选、搜索、全文阅读）
- `tools/gen_nyt_preview.py`：纯静态的 NYT 单报核对页（无 JS，`<details>` 折叠）

---

## 3. 踩过的坑（都已修复，改代码时别再踩）

### 3.1 图片文件名冲突（最严重）

下载器按 `COUNT(已有文件)+1` 给同篇文章的图编号，而这个值在批量开始时就固定了。
结果同批 `.jpg` 全部写成 `01.jpg`，互相覆盖 —— 3519 条记录只落到 1168 个文件，
正文里同一张图被引用多次，用户看到的就是"图片和文章对不上"。

**现状**：`refix_images.py` 每篇单独建目录（与 md 同名），按正文出现顺序 `01、02…` 编号，
冲突率从 67% 降到 0.4%。

### 3.2 采集范围过宽

早期脚本抓存档页**整页**所有 `<img>`，把侧栏推荐、作者头像、Cookie 同意横幅 logo 一并收进来。
**现状**：只取正文容器的 `<figure>`，并按 URL 特征过滤站点素材。

### 3.3 archive 快照缺图

WaPo 的存档页只保留首图（其余为懒加载，未被存档）；WSJ 多数根本没有可用快照。
**现状**：WaPo/WSJ 走 jina 通道，NYT 仍用存档页（更精确）。

### 3.4 jina 的 404 陷阱

`r.jina.ai` 对失效 URL 会返回 **404 页面**，而该页面带一整套 "Most Read" 缩略图。
不过滤的话会把这些无关图当成正文配图 —— 这是错图的另一个来源。
**现状**：检测 `tn_404page` 直接丢弃；正文图在第一个推荐位标题处截断。

### 3.5 预览页图片路径重复

`img/<目录>/01.jpg` 被替换成 `md/NYT/img/<目录>/<目录>/01.jpg`，正文图全部 404。
**现状**：只加 `md/<报纸>/img/` 前缀。

### 3.6 前端渲染失败

早期预览页用 JS 注入数据渲染列表，脚本一报错整页只剩一个标题。
**现状**：改为服务端静态渲染，不依赖 JS。

### 3.7 URL 变体重复

同一篇文章因 `?itid=` 跟踪参数或尾斜杠，在库里存成两行，图片互相覆盖。
**现状**：URL 归一化（去查询参数），重复行合并。

---

## 4. 脚本清单

| 脚本 | 作用 |
|---|---|
| `tools/save_one.py` | 从 JSON 落盘一篇正文并更新库 |
| `save_article.py` | 写 md + 更新 `articles2026` / `contents`（底层实现） |
| `tools/bodyimg.py` | 轻量 DOM 解析：从存档页定位正文容器并取图（无第三方依赖） |
| `tools/refix_images.py` | 图片层重建：抓页 → 取正文图 → 按篇编号落盘 → 更新 images |
| `tools/img_downloader.py` | pending 图片下载 + 内联 + 刷新广场（可独立定时运行） |
| `tools/inline_images.py` | 图片内联重排（`--reall` 全量） |
| `tools/insert_images.py` | 把图片 URL 列表写入 images 表（去重、`/o/` 还原原始 URL） |
| `tools/backfill_img_urls.py` | 零 token 回填：curl 抓存档页解析 img 入表（早期批量补齐用） |
| `tools/import_listing.py` | 列表页条目导入 `articles2026` |
| `tools/gen_plaza_data.py` / `gen_plaza_html.py` | 生成内容广场数据与页面 |
| `tools/gen_nyt_preview.py` | 生成 NYT 单报静态核对页 |
| `tools/check_one.py` / `final_stats.py` | 单篇检查 / 统计 |

---

## 5. 本地预览

```bash
cd D:\three-papers-harvest
python -m http.server 8765 --bind 127.0.0.1
# 内容广场
#   http://127.0.0.1:8765/内容广场.html
# NYT 图文核对页
#   http://127.0.0.1:8765/nyt_preview.html
```

页面用相对路径引用 `md/...`，必须从项目根目录起服务，直接双击打开会丢图。

---

## 6. 常用查询

```sql
-- 待抽取
SELECT paper, pub_date, title FROM articles2026
 WHERE ph_hit=1 AND md_path IS NULL ORDER BY pub_date DESC;

-- 有正文但缺图片记录
SELECT a.url FROM articles2026 a WHERE a.md_path IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM images i WHERE i.article_url=a.url);

-- 图片状态分布
SELECT status, COUNT(*) FROM images GROUP BY status;
```

---

## 7. 已知限制

- **覆盖范围**：目前只回溯到 2026-10-19（列表页扫描 40 个，目标 2026-01-01），1 月至 10 月中旬仍是空白
- **抽取方式**：正文靠浏览器插件读取，受每轮调用额度限制；图片与列表页走脚本，零 token
- **存档质量**：archive.ph 上的快照本身可能缺图、缺评论、缺交互图表或视频封面，这些拿不到
- **付费墙**：WSJ 多数文章无可用快照
- **时效**：`/newest/` 取的是最新快照，同一 URL 不同时间的快照内容可能有差异
