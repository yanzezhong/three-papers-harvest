# -*- coding: utf-8 -*-
"""从存档页 HTML 中定位正文容器并按顺序取出正文配图（轻量 DOM，无第三方依赖）

判定规则（按优先级）：
1. 取文本量最大的 <article> 子树内的 <figure>/<img>；
2. 若该容器内无图，退化为全文档 <figure> 扫描（archive.today 会剥离 class，WaPo 首图常在 article 之外）；
3. 过滤站点素材/推荐位缩略图（cookie 横幅、作者头像、像素、scr.png、square640 缩略图等）。
"""
import re
from html.parser import HTMLParser

VOID = {'img', 'source', 'br', 'hr', 'meta', 'link', 'input', 'area', 'base',
        'col', 'embed', 'param', 'track', 'wbr'}
SKIP_TAGS = {'script', 'style', 'noscript', 'svg', 'iframe'}

JUNK_URL = ('cookielaw', 'author-service-images', 'px.washingtonpost', 'histats',
            '/scr.png', 'doubleclick', 'googletag', '/logo', 'sstats', 'ad-delivery',
            'square640', '-thumb', 'thumbnail', 'avatar', 'icon-', 'favicon',
            'newsletter', '1x1.', 'spacer')

BAD_ANCESTOR = re.compile(
    r'(relat|recirc|most-read|more-in|read-next|also-read|newsletter|promo|'
    r'sign[_-]?up|sidebar|ad[_-]|advert|recommend|trending|popular|'
    r'comment|footer|\bnav\b|banner|subscri|share|social|paywall|onboarding)', re.I)


class Node:
    __slots__ = ('tag', 'attrs', 'kids', 'parent', 'textlen', 'img')

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.kids = []
        self.parent = parent
        self.textlen = 0
        self.img = None


class Dom(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root', {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        node = Node(tag, a, self.cur)
        self.cur.kids.append(node)
        if tag in ('img', 'source'):
            src = a.get('currentsourceurl') or a.get('src') or a.get('data-src') or ''
            if src and not src.startswith('data:'):
                node.img = src
        if tag not in VOID:
            self.cur = node

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if self.cur.tag in SKIP_TAGS:
            return
        t = data.strip()
        if t:
            self.cur.textlen += len(t)


def subtree_text(n):
    tot = n.textlen
    for k in n.kids:
        tot += subtree_text(k)
    return tot


def find_articles(root):
    out = []

    def walk(n):
        if n.tag == 'article':
            out.append(n)
        for k in n.kids:
            walk(k)

    walk(root)
    return out


def _cls(n):
    return ' '.join((n.attrs.get('class', ''), n.attrs.get('id', ''),
                     n.attrs.get('data-qa', ''), n.attrs.get('data-testid', ''))).strip()


def _bad_chain(n, stop):
    while n is not None and n is not stop:
        c = _cls(n)
        if c and BAD_ANCESTOR.search(c):
            return True
        n = n.parent
    return False


def collect(node, cap=20, check_ancestors=True):
    """收集 node 子树内 <figure> 中的图片，按文档顺序"""
    out = []

    def rec(n, in_fig, depth):
        if len(out) >= cap or depth > 80:
            return
        if n.tag in SKIP_TAGS:
            return
        fig = in_fig or n.tag == 'figure'
        if n.img and fig:
            low = n.img.lower()
            if not any(j in low for j in JUNK_URL):
                if not check_ancestors or not _bad_chain(n, node):
                    out.append(n.img)
        for k in n.kids:
            rec(k, fig, depth + 1)

    rec(node, False, 0)
    return out


def body_images(html, cap=14):
    """返回正文配图 URL 列表（文档顺序、已去重）"""
    d = Dom()
    d.feed(html)
    imgs = []
    arts = find_articles(d.root)
    if arts:
        main = max(arts, key=subtree_text)
        if subtree_text(main) > 300:
            imgs = collect(main, cap=cap * 2)
    if not imgs:
        imgs = collect(d.root, cap=cap * 2, check_ancestors=True)
    seen, uniq = set(), []
    for u in imgs:
        k = re.sub(r'[?#].*$', '', u)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(u)
    return uniq[:cap]
