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


def build_post(pandoc, post):
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

    # Drop the TOC sidebar when a post has almost no headings.
    aside = re.search(r'<aside class="toc-sidebar">.*?</aside>', page, flags=re.S)
    if aside and aside.group(0).count("<li>") < 2:
        page = page.replace(aside.group(0), "")

    out_file.write_text(page)
    print("built posts/%s/index.html" % slug)


def build_index(config):
    posts = sorted(config["posts"], key=lambda p: p["date"], reverse=True)
    cats = config["categories"]

    counts = {}
    for p in posts:
        counts[p["category"]] = counts.get(p["category"], 0) + 1

    chips = ['<button class="chip active" data-category="all">All'
             '<span class="count">%d</span></button>' % len(posts)]
    for key, label in cats.items():
        if key in counts:
            chips.append(
                '<button class="chip" data-category="%s">%s'
                '<span class="count">%d</span></button>'
                % (key, html.escape(label), counts[key]))

    def item_html(p, show_tag=True):
        label = cats.get(p["category"], p["category"])
        tag = ('<span class="tag">%s</span>' % html.escape(label)) if show_tag else ""
        return (
            '<div class="post-item" data-category="%s">\n'
            '  <span class="post-date">%s</span>\n'
            '  <div>\n'
            '    <a class="post-link" href="posts/%s/">%s</a>%s\n'
            '    <p class="post-desc">%s</p>\n'
            '  </div>\n'
            '</div>'
            % (p["category"], display_date(p["date"]), p["slug"],
               html.escape(p["title"]), tag,
               html.escape(p.get("description", ""))))

    # ----- view 1: grouped by year -----
    by_date = []
    current_year = None
    for p in posts:
        year = p["date"][:4]
        if year != current_year:
            if current_year is not None:
                by_date.append("</div>")
            by_date.append('<div class="year-group">\n'
                           '<div class="year-heading">%s</div>' % year)
            current_year = year
        by_date.append(item_html(p))
    if current_year is not None:
        by_date.append("</div>")

    # ----- view 2: grouped by topic -----
    by_topic = []
    for key, label in cats.items():
        cat_posts = [p for p in posts if p["category"] == key]
        if not cat_posts:
            continue
        by_topic.append('<div class="year-group" data-category-group="%s">\n'
                        '<div class="year-heading">%s</div>' % (key, html.escape(label)))
        by_topic.extend(item_html(p, show_tag=False) for p in cat_posts)
        by_topic.append("</div>")

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blog | Jiawei Zhang</title>
<meta name="description" content="%(intro)s">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%%22http://www.w3.org/2000/svg%%22 viewBox=%%220 0 100 100%%22><text y=%%22.9em%%22 font-size=%%2290%%22>🍪</text></svg>">
<link rel="stylesheet" href="assets/blog.css">
<script src="assets/blog.js"></script>
<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
</head>
<body>

<header class="site-header">
  <div class="site-header-inner">
    <a class="site-title" href="./">Jiawei Zhang<span style="color:var(--accent)">&nbsp;· Blog</span></a>
    <nav class="site-nav">
      <a href="./" class="active">Posts</a>
      <a href="https://javyduck.github.io/">About</a>
      <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark mode">☾</button>
    </nav>
  </div>
</header>

<main class="index-wrap">
  <p class="index-intro">%(intro)s</p>

  <div class="index-controls">
    <div class="category-chips">
      %(chips)s
    </div>
    <div class="view-toggle">
      <button class="view-btn active" data-view="date">By date</button>
      <button class="view-btn" data-view="topic">By topic</button>
    </div>
  </div>

  <div id="view-date">
  %(by_date)s
  </div>

  <div id="view-topic" style="display:none">
  %(by_topic)s
  </div>
</main>

<footer class="site-footer">
  © 2026 Jiawei Zhang · <a href="https://javyduck.github.io/">javyduck.github.io</a>
  <span id="busuanzi_container_site_pv" style="display:none">·
    <span id="busuanzi_value_site_pv"></span> visits</span>
</footer>

</body>
</html>
""" % {"intro": html.escape(config["intro"]),
       "chips": "\n    ".join(chips),
       "by_date": "\n\n  ".join(by_date),
       "by_topic": "\n\n  ".join(by_topic)}

    (BLOG_DIR / "index.html").write_text(page)
    print("built index.html")


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
        build_post(pandoc, post)

    build_index(config)


if __name__ == "__main__":
    main()
