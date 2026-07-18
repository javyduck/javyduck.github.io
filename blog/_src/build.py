#!/usr/bin/env python3
"""Static builder for the blog.

Reads posts.json, converts each post source (LaTeX chapter or Markdown)
to HTML with pandoc, wraps it in templates/post.html, and regenerates
blog/index.html.

Usage:  python3 build.py [--pandoc /path/to/pandoc]

Add a post: drop an entry into posts.json (source paths are relative to
this directory), put any figures into
blog/posts/<slug>/figures/<figure-id>.svg, then re-run this script.
"""

import argparse
import datetime
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
BLOG_DIR = SRC_DIR.parent


def find_pandoc(cli_arg):
    candidates = [cli_arg, shutil.which("pandoc"),
                  str(Path.home() / ".local/pandoc/pandoc-3.6.4-arm64/bin/pandoc")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    sys.exit("pandoc not found; pass --pandoc /path/to/pandoc")


def display_date(iso):
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%b %-d, %Y")


def extract_chapter_body(tex, chapter_number):
    """Keep everything from \\chapter{...} to \\end{document}."""
    start = tex.find("\\chapter{")
    end = tex.find("\\end{document}")
    body = tex[start:end if end != -1 else None]
    setcounter = "\\setcounter{chapter}{%d}\n" % (chapter_number - 1)
    return setcounter + body


def reading_time(body_html):
    text = re.sub(r"<[^>]+>", " ", body_html)
    words = len(text.split())
    return max(1, round(words / 230))


def strip_chapter_heading(body):
    """Remove the chapter <h1> (the template renders the title itself)."""
    return re.sub(r"<h1[^>]*>.*?</h1>", "", body, count=1, flags=re.S)


def unwrap_toc(page):
    """The pandoc TOC nests all sections under the single chapter entry;
    lift the inner <ul> up one level."""
    m = re.search(r'(<aside class="toc-sidebar">.*?</aside>)', page, flags=re.S)
    if not m:
        return page
    aside = m.group(1)
    inner = re.search(r"<li>.*?(<ul>.*</ul>)\s*</li>\s*</ul>", aside, flags=re.S)
    if not inner:
        return page
    outer_ul = re.search(r"<ul>.*</ul>", aside, flags=re.S)
    new_aside = aside.replace(outer_ul.group(0), inner.group(1))
    return page.replace(aside, new_aside)


def inject_figures(body, post_dir):
    """Pandoc drops tikzpicture bodies; slot in pre-rendered SVGs by id."""
    def repl(m):
        fig_id = m.group(1)
        name = fig_id.split(":", 1)[-1]
        svg = post_dir / "figures" / (name + ".svg")
        if svg.exists():
            img = ('\n<img class="figure-light" src="figures/%s.svg" '
                   'alt="%s">' % (name, name.replace("-", " ")))
            return m.group(0) + img
        print("  warning: no SVG for figure id %s" % fig_id)
        return m.group(0)
    return re.sub(r'<figure id="(fig:[^"]+)">', repl, body)


def label_references(body):
    if '<div id="refs"' in body:
        body = body.replace(
            '<div id="refs"',
            '<h1 class="refs-heading">References</h1>\n<div id="refs"', 1)
    return body


def series_neighbors(config, post):
    """Return (series_id, series_def, prev_post, next_post) for a series
    member, ordered by part number."""
    sid = post.get("series")
    if not sid:
        return None, None, None, None
    sdef = config.get("series", {}).get(sid, {})
    members = sorted(
        [p for p in config["posts"] if p.get("series") == sid],
        key=lambda p: p.get("part", 0))
    idx = next(i for i, p in enumerate(members) if p["slug"] == post["slug"])
    prev_p = members[idx - 1] if idx > 0 else None
    next_p = members[idx + 1] if idx + 1 < len(members) else None
    return sid, sdef, prev_p, next_p


def build_post(pandoc, post, config):
    slug = post["slug"]
    out_dir = BLOG_DIR / "posts" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    src = (SRC_DIR / post["source"]).resolve()
    if not src.exists():
        sys.exit("source not found: %s" % src)

    fmt = post.get("format", "markdown")
    cmd = [pandoc, "-t", "html5", "--mathjax", "--toc", "--toc-depth=3",
           "--template", str(SRC_DIR / "templates" / "post.html"),
           "-V", "title=%s" % post["title"],
           "-V", "displaydate=%s" % display_date(post["date"]),
           "-V", "category=%s" % post["category"],
           "-V", "description=%s" % post.get("description", ""),
           "-V", "readingtime=PLACEHOLDER"]

    sid, sdef, prev_p, next_p = series_neighbors(config, post)
    if sid:
        crumb = ('<nav class="post-breadcrumb"><a href="../../series/%s/">%s</a>'
                 '<span class="crumb-sep">/</span>'
                 '<span>Chapter %d</span></nav>'
                 % (sid, html.escape(sdef.get("title", sid)), post.get("part", 0)))
        cmd += ["-V", "breadcrumbhtml=%s" % crumb]

        nav_cells = []
        if prev_p:
            nav_cells.append(
                '<a class="series-nav-card" href="../%s/">'
                '<span class="series-nav-label">← Previous · Chapter %d</span>'
                '<span class="series-nav-title">%s</span></a>'
                % (prev_p["slug"], prev_p.get("part", 0), html.escape(prev_p["title"])))
        else:
            nav_cells.append('<span class="series-nav-card empty"></span>')
        if next_p:
            nav_cells.append(
                '<a class="series-nav-card next" href="../%s/">'
                '<span class="series-nav-label">Next · Chapter %d →</span>'
                '<span class="series-nav-title">%s</span></a>'
                % (next_p["slug"], next_p.get("part", 0), html.escape(next_p["title"])))
        else:
            nav_cells.append(
                '<span class="series-nav-card next empty">'
                '<span class="series-nav-label">Next chapter</span>'
                '<span class="series-nav-title">Coming soon</span></span>')
        cmd += ["-V", "seriesnavhtml=<nav class=\"series-nav\">%s</nav>"
                % "".join(nav_cells)]

    giscus = config.get("giscus", {})
    if giscus.get("categoryId"):
        cmd += ["-V", "giscusrepo=%s" % giscus["repo"],
                "-V", "giscusrepoid=%s" % giscus["repoId"],
                "-V", "giscuscategory=%s" % giscus["category"],
                "-V", "giscuscategoryid=%s" % giscus["categoryId"]]

    if post.get("bibliography"):
        bib = (SRC_DIR / post["bibliography"]).resolve()
        cmd += ["--citeproc", "--bibliography", str(bib)]

    if fmt == "latex":
        tex = src.read_text()
        body = extract_chapter_body(tex, post.get("chapter", 1))
        preamble = (SRC_DIR / "tex-preamble.tex").read_text()
        full = preamble + body + "\n\\end{document}\n"
        with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False) as f:
            f.write(full)
            tmp = f.name
        cmd += ["-f", "latex", "--number-sections", tmp]
    else:
        cmd += ["-f", "markdown+smart", str(src)]
        # Copy images sitting next to the markdown source so relative
        # paths keep working in the published post.
        for f in src.parent.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif",
                                    ".svg", ".webp", ".mp4", ".pdf"):
                shutil.copy2(f, out_dir / f.name)

    page = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout

    # Post-processing.
    art = re.search(r'<article class="post-content">(.*?)</article>', page, flags=re.S)
    body_html = art.group(1)
    new_body = body_html
    if fmt == "latex":
        new_body = strip_chapter_heading(new_body)
    new_body = inject_figures(new_body, out_dir)
    new_body = label_references(new_body)
    page = page.replace(body_html, new_body)
    page = page.replace("PLACEHOLDER", str(reading_time(new_body)))
    page = unwrap_toc(page)

    # Drop the TOC sidebar (and its reopen button) when a post has almost
    # no headings.
    aside = re.search(
        r'<aside class="toc-sidebar">.*?</aside>\s*'
        r'(?:<button class="toc-reopen".*?</button>)?',
        page, flags=re.S)
    if aside and aside.group(0).count("<li>") < 2:
        page = page.replace(aside.group(0), "")

    out_file.write_text(page)
    print("built posts/%s/index.html" % slug)


def page_chrome(rel, title, description, content):
    """Shared page shell for index / topic / series pages. `rel` is the
    relative path prefix back to the blog root ("" or "../../")."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(description)s">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%%22http://www.w3.org/2000/svg%%22 viewBox=%%220 0 100 100%%22><text y=%%22.9em%%22 font-size=%%2290%%22>🍪</text></svg>">
<link rel="stylesheet" href="%(rel)sassets/blog.css">
<script src="%(rel)sassets/blog.js"></script>
<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
</head>
<body>

<header class="site-header">
  <div class="site-header-inner">
    <a class="site-title" href="%(rel)s./">Jiawei Zhang<span class="site-title-accent">&nbsp;· Blog</span></a>
    <nav class="site-nav">
      <a href="%(rel)s./">Posts</a>
      <a href="https://javyduck.github.io/">About</a>
      <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark mode">☾</button>
    </nav>
  </div>
</header>

<main class="index-wrap">
%(content)s
</main>

<footer class="site-footer">
  © 2026 Jiawei Zhang · <a href="https://javyduck.github.io/">javyduck.github.io</a>
  <span id="busuanzi_container_site_pv" style="display:none">·
    <span id="busuanzi_value_site_pv"></span> visits</span>
</footer>

</body>
</html>
""" % {"title": html.escape(title), "description": html.escape(description),
       "rel": rel, "content": content}


def item_html(p, cats, rel, show_tag=True):
    label = cats.get(p["category"], p["category"])
    tag = ('<a class="tag" href="%stopics/%s/">%s</a>'
           % (rel, p["category"], html.escape(label))) if show_tag else ""
    search_blob = html.escape(" ".join(
        [p["title"], p.get("description", ""), p["category"], label]).lower())
    return (
        '<div class="post-item" data-category="{cat}" data-search="{search}">\n'
        '  <span class="post-date">{date}</span>\n'
        '  <div>\n'
        '    <a class="post-link" href="{rel}posts/{slug}/">{title}</a>{tag}\n'
        '    <p class="post-desc">{desc}</p>\n'
        '  </div>\n'
        '</div>'
    ).format(cat=p["category"], search=search_blob,
             date=display_date(p["date"]), rel=rel, slug=p["slug"],
             title=html.escape(p["title"]), tag=tag,
             desc=html.escape(p.get("description", "")))


def year_grouped(posts, cats, rel, show_tag=True):
    out = []
    current_year = None
    for p in posts:
        year = p["date"][:4]
        if year != current_year:
            if current_year is not None:
                out.append("</div>")
            out.append('<div class="year-group">\n'
                       '<div class="year-heading">%s</div>' % year)
            current_year = year
        out.append(item_html(p, cats, rel, show_tag))
    if current_year is not None:
        out.append("</div>")
    return "\n\n".join(out)


def series_meta(members):
    latest = max(members, key=lambda p: p["date"]) if members else None
    meta = "%d chapter%s" % (len(members), "" if len(members) == 1 else "s")
    if latest:
        meta += " · updated %s" % display_date(latest["date"])
    return meta


def series_card(sid, sdef, members, rel):
    return (
        '<a class="series-card" href="%(rel)sseries/%(sid)s/">\n'
        '  <span class="section-label">Series</span>\n'
        '  <span class="series-card-title">%(title)s</span>\n'
        '  <span class="series-card-desc">%(desc)s</span>\n'
        '  <span class="series-card-meta">%(meta)s</span>\n'
        '</a>'
    ) % {"rel": rel, "sid": sid, "title": html.escape(sdef.get("title", sid)),
         "desc": html.escape(sdef.get("description", "")),
         "meta": series_meta(members)}


def series_accordion(sid, sdef, members, rel):
    """Collapsed overview row that expands inline to the chapter list."""
    members = sorted(members, key=lambda p: p.get("part", 0))
    rows = "\n".join(
        '<a class="series-acc-row" href="%sposts/%s/">'
        '<span class="series-acc-num">%02d</span>'
        '<span class="series-acc-name">%s</span>'
        '<span class="series-acc-date">%s</span></a>'
        % (rel, p["slug"], p.get("part", 0), html.escape(p["title"]),
           display_date(p["date"]))
        for p in members)
    return (
        '<details class="series-acc">\n'
        '  <summary>\n'
        '    <span class="series-acc-head">\n'
        '      <span class="series-card-title">%(title)s</span>\n'
        '      <span class="series-card-meta">%(meta)s</span>\n'
        '    </span>\n'
        '    <span class="series-acc-chevron">⌄</span>\n'
        '  </summary>\n'
        '  <div class="series-acc-body">\n'
        '    <p class="series-card-desc">%(desc)s</p>\n'
        '    %(rows)s\n'
        '    <a class="series-acc-more" href="%(rel)sseries/%(sid)s/">View series page →</a>\n'
        '  </div>\n'
        '</details>'
    ) % {"title": html.escape(sdef.get("title", sid)),
         "meta": series_meta(members),
         "desc": html.escape(sdef.get("description", "")),
         "rows": rows, "rel": rel, "sid": sid}


def build_index(config):
    posts = sorted(config["posts"], key=lambda p: p["date"], reverse=True)
    cats = config["categories"]
    series = config.get("series", {})

    accordions = []
    for sid, sdef in series.items():
        members = [p for p in posts if p.get("series") == sid]
        if members:
            accordions.append(series_accordion(sid, sdef, members, ""))

    topic_links = []
    for key, label in cats.items():
        n = sum(1 for p in posts if p["category"] == key)
        if n:
            topic_links.append(
                '<a class="topic-link" href="topics/%s/">%s'
                '<span class="count">%d</span></a>'
                % (key, html.escape(label), n))

    content = """
  <p class="index-intro">%(intro)s</p>

  <input class="search-box" type="search" id="post-search"
         placeholder="Search posts…" autocomplete="off">

  <section class="home-section">
    <div class="section-label">Recent posts</div>
    <div id="post-list" data-page-size="%(page_size)d">
    %(recent)s
    </div>
    <p class="no-results" id="no-results">No posts match your search.</p>
    <nav class="pager" id="pager"></nav>
  </section>

  %(series_section)s

  <section class="home-section" id="topics-section">
    <div class="section-label">Browse by topic</div>
    <div class="topic-links">
      %(topics)s
    </div>
  </section>
""" % {"intro": html.escape(config["intro"]),
       "series_section": (
           '<section class="home-section" id="series-section">\n'
           '<div class="section-label">Series</div>\n%s\n</section>'
           % "\n".join(accordions) if accordions else ""),
       "recent": year_grouped(posts, cats, ""),
       "topics": "\n      ".join(topic_links),
       "page_size": int(config.get("page_size", 10))}

    (BLOG_DIR / "index.html").write_text(
        page_chrome("", "Blog | Jiawei Zhang", config["intro"], content))
    print("built index.html")


def build_topic_pages(config):
    posts = sorted(config["posts"], key=lambda p: p["date"], reverse=True)
    cats = config["categories"]
    series = config.get("series", {})

    for key, label in cats.items():
        cat_posts = [p for p in posts if p["category"] == key]
        if not cat_posts:
            continue
        out_dir = BLOG_DIR / "topics" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        cards = []
        for sid, sdef in series.items():
            if sdef.get("topic") == key:
                members = [p for p in posts if p.get("series") == sid]
                if members:
                    cards.append(series_card(sid, sdef, members, "../../"))

        content = """
  <nav class="page-crumb"><a href="../../">Blog</a><span class="crumb-sep">/</span><span>%(label)s</span></nav>
  <h1 class="page-title">%(label)s</h1>
  <p class="index-intro">%(count)d post%(plural)s</p>

  %(series_section)s

  <section class="home-section">
  %(items)s
  </section>
""" % {"label": html.escape(label), "count": len(cat_posts),
       "plural": "" if len(cat_posts) == 1 else "s",
       "series_section": (
           '<section class="home-section">\n<div class="series-grid">\n'
           '%s\n</div>\n</section>' % "\n".join(cards) if cards else ""),
       "items": year_grouped(cat_posts, cats, "../../", show_tag=False)}

        (out_dir / "index.html").write_text(page_chrome(
            "../../", "%s | Jiawei Zhang" % label,
            "Posts about %s" % label, content))
        print("built topics/%s/index.html" % key)


def build_series_pages(config):
    posts = config["posts"]
    series = config.get("series", {})

    for sid, sdef in series.items():
        members = sorted([p for p in posts if p.get("series") == sid],
                         key=lambda p: p.get("part", 0))
        if not members:
            continue
        out_dir = BLOG_DIR / "series" / sid
        out_dir.mkdir(parents=True, exist_ok=True)

        rows = []
        for p in members:
            rows.append(
                '<a class="chapter-row" href="../../posts/%(slug)s/">\n'
                '  <span class="chapter-num">%(part)02d</span>\n'
                '  <span class="chapter-body">\n'
                '    <span class="chapter-title">%(title)s</span>\n'
                '    <span class="chapter-desc">%(desc)s</span>\n'
                '    <span class="chapter-meta">%(date)s</span>\n'
                '  </span>\n'
                '</a>'
                % {"slug": p["slug"], "part": p.get("part", 0),
                   "title": html.escape(p["title"]),
                   "desc": html.escape(p.get("description", "")),
                   "date": display_date(p["date"])})

        content = """
  <nav class="page-crumb"><a href="../../">Blog</a><span class="crumb-sep">/</span><span>Series</span></nav>
  <h1 class="page-title serif">%(title)s</h1>
  <p class="series-lede">%(desc)s</p>
  <p class="index-intro">%(count)d chapter%(plural)s so far · more on the way</p>

  <div class="chapter-list">
  %(rows)s
  </div>
""" % {"title": html.escape(sdef.get("title", sid)),
       "desc": html.escape(sdef.get("description", "")),
       "count": len(members), "plural": "" if len(members) == 1 else "s",
       "rows": "\n\n  ".join(rows)}

        (out_dir / "index.html").write_text(page_chrome(
            "../../", "%s | Jiawei Zhang" % sdef.get("title", sid),
            sdef.get("description", ""), content))
        print("built series/%s/index.html" % sid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pandoc", default=None)
    ap.add_argument("--only", default=None, help="build a single slug")
    args = ap.parse_args()

    pandoc = find_pandoc(args.pandoc)
    config = json.loads((SRC_DIR / "posts.json").read_text())

    for post in config["posts"]:
        if args.only and post["slug"] != args.only:
            continue
        build_post(pandoc, post, config)

    build_index(config)
    build_topic_pages(config)
    build_series_pages(config)


if __name__ == "__main__":
    main()
