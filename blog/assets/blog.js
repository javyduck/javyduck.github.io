/* Theme toggle, category filtering, and TOC scroll-spy. */

(function () {
  // ---------- theme ----------
  var stored = localStorage.getItem("blog-theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);

  // ---------- TOC collapse (post page) ----------
  if (localStorage.getItem("blog-toc") === "collapsed") {
    document.documentElement.classList.add("toc-collapsed");
  }

  window.toggleToc = function () {
    var collapsed = document.documentElement.classList.toggle("toc-collapsed");
    localStorage.setItem("blog-toc", collapsed ? "collapsed" : "open");
  };

  window.toggleTheme = function () {
    var cur = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    var next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("blog-theme", next);
    updateToggleIcon();
    // Keep the giscus comment iframe in sync with the page theme.
    var frame = document.querySelector("iframe.giscus-frame");
    if (frame) {
      frame.contentWindow.postMessage(
        { giscus: { setConfig: { theme: next === "dark" ? "dark" : "light" } } },
        "https://giscus.app"
      );
    }
  };

  var MOON_SVG = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
  var SUN_SVG = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="12" cy="12" r="5"></circle>' +
    '<line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line>' +
    '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>' +
    '<line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line>' +
    '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>';

  function updateToggleIcon() {
    var btn = document.querySelector(".theme-toggle");
    if (!btn) return;
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    btn.innerHTML = dark ? SUN_SVG : MOON_SVG;
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateToggleIcon();

    // ---------- index page: search + pager ----------
    var postList = document.getElementById("post-list");
    if (postList) {
      var searchBox = document.getElementById("post-search");
      var pager = document.getElementById("pager");
      var noResults = document.getElementById("no-results");
      var pageSize = parseInt(postList.getAttribute("data-page-size") || "10", 10);
      var state = { query: "", page: 1 };

      function matches(item) {
        return !state.query ||
          (item.getAttribute("data-search") || "").indexOf(state.query) !== -1;
      }

      function renderPager(pageCount) {
        pager.innerHTML = "";
        if (pageCount <= 1) return;
        function btn(label, page, opts) {
          var b = document.createElement("button");
          b.textContent = label;
          if (opts && opts.current) b.classList.add("current");
          if (opts && opts.disabled) b.disabled = true;
          b.addEventListener("click", function () { state.page = page; apply(); });
          return b;
        }
        pager.appendChild(btn("←", state.page - 1, { disabled: state.page === 1 }));
        for (var i = 1; i <= pageCount; i++) {
          pager.appendChild(btn(String(i), i, { current: i === state.page }));
        }
        pager.appendChild(btn("→", state.page + 1, { disabled: state.page === pageCount }));
      }

      function apply() {
        var items = Array.prototype.slice.call(postList.querySelectorAll(".post-item"));
        var visible = items.filter(matches);
        var pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
        if (state.page > pageCount) state.page = pageCount;
        var start = (state.page - 1) * pageSize;
        var pageItems = visible.slice(start, start + pageSize);
        items.forEach(function (item) {
          item.style.display = pageItems.indexOf(item) !== -1 ? "" : "none";
        });

        postList.querySelectorAll(".year-group").forEach(function (group) {
          var any = Array.prototype.some.call(
            group.querySelectorAll(".post-item"),
            function (item) { return item.style.display !== "none"; }
          );
          group.style.display = any ? "" : "none";
        });

        // While searching, collapse the series/topics sections so results
        // are the focus.
        var searching = !!state.query;
        ["series-section", "topics-section"].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.style.display = searching ? "none" : "";
        });

        noResults.style.display = visible.length ? "none" : "block";
        renderPager(pageCount);
      }

      if (searchBox) {
        searchBox.addEventListener("input", function () {
          state.query = searchBox.value.trim().toLowerCase();
          state.page = 1;
          apply();
        });
      }

      apply();
    }

    // ---------- giscus comments (post page) ----------
    var giscusEl = document.getElementById("giscus-container");
    if (giscusEl) {
      var dark = document.documentElement.getAttribute("data-theme") === "dark";
      var s = document.createElement("script");
      s.src = "https://giscus.app/client.js";
      s.async = true;
      s.crossOrigin = "anonymous";
      s.setAttribute("data-repo", giscusEl.getAttribute("data-giscus-repo"));
      s.setAttribute("data-repo-id", giscusEl.getAttribute("data-giscus-repo-id"));
      s.setAttribute("data-category", giscusEl.getAttribute("data-giscus-category"));
      s.setAttribute("data-category-id", giscusEl.getAttribute("data-giscus-category-id"));
      s.setAttribute("data-mapping", "pathname");
      s.setAttribute("data-strict", "0");
      s.setAttribute("data-reactions-enabled", "1");
      s.setAttribute("data-emit-metadata", "0");
      s.setAttribute("data-input-position", "top");
      s.setAttribute("data-theme", dark ? "dark" : "light");
      s.setAttribute("data-lang", "en");
      giscusEl.appendChild(s);
    }

    // ---------- TOC scroll-spy (post page) ----------
    var tocLinks = document.querySelectorAll(".toc-sidebar a");
    if (tocLinks.length) {
      var map = new Map();
      tocLinks.forEach(function (link) {
        var id = decodeURIComponent(link.getAttribute("href").slice(1));
        var el = document.getElementById(id);
        if (el) map.set(el, link);
      });
      var current = null;
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              if (current) current.classList.remove("toc-active");
              current = map.get(entry.target);
              if (current) {
                current.classList.add("toc-active");
                current.scrollIntoView({ block: "nearest" });
              }
            }
          });
        },
        { rootMargin: "0px 0px -75% 0px" }
      );
      map.forEach(function (_link, el) { observer.observe(el); });
    }
  });
})();
