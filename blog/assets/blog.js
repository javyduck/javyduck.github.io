/* Theme toggle, category filtering, and TOC scroll-spy. */

(function () {
  // ---------- theme ----------
  var stored = localStorage.getItem("blog-theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);

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

  function updateToggleIcon() {
    var btn = document.querySelector(".theme-toggle");
    if (!btn) return;
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    btn.textContent = dark ? "☀" : "☾";
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateToggleIcon();

    // ---------- index page: filter + search + view toggle + pager ----------
    var viewDate = document.getElementById("view-date");
    if (viewDate) {
      var chips = document.querySelectorAll(".chip[data-category]");
      var viewBtns = document.querySelectorAll(".view-btn[data-view]");
      var searchBox = document.getElementById("post-search");
      var pager = document.getElementById("pager");
      var noResults = document.getElementById("no-results");
      var pageSize = parseInt(viewDate.getAttribute("data-page-size") || "10", 10);
      var state = { category: "all", query: "", view: "date", page: 1 };

      function matches(item) {
        if (state.category !== "all" &&
            item.getAttribute("data-category") !== state.category) return false;
        if (state.query &&
            (item.getAttribute("data-search") || "").indexOf(state.query) === -1) return false;
        return true;
      }

      function renderPager(pageCount) {
        pager.innerHTML = "";
        if (state.view !== "date" || pageCount <= 1) return;
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
        var container = state.view === "date" ? viewDate
                                              : document.getElementById("view-topic");
        var items = Array.prototype.slice.call(container.querySelectorAll(".post-item"));
        var visible = items.filter(matches);
        var pageCount = 1;

        if (state.view === "date") {
          pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
          if (state.page > pageCount) state.page = pageCount;
          var start = (state.page - 1) * pageSize;
          var pageItems = visible.slice(start, start + pageSize);
          items.forEach(function (item) {
            item.style.display = pageItems.indexOf(item) !== -1 ? "" : "none";
          });
        } else {
          items.forEach(function (item) {
            item.style.display = visible.indexOf(item) !== -1 ? "" : "none";
          });
        }

        container.querySelectorAll(".year-group").forEach(function (group) {
          var any = Array.prototype.some.call(
            group.querySelectorAll(".post-item"),
            function (item) { return item.style.display !== "none"; }
          );
          group.style.display = any ? "" : "none";
        });

        noResults.style.display = visible.length ? "none" : "block";
        renderPager(pageCount);
      }

      chips.forEach(function (chip) {
        chip.addEventListener("click", function () {
          chips.forEach(function (c) { c.classList.remove("active"); });
          chip.classList.add("active");
          state.category = chip.getAttribute("data-category");
          state.page = 1;
          apply();
        });
      });

      viewBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          viewBtns.forEach(function (b) { b.classList.remove("active"); });
          btn.classList.add("active");
          state.view = btn.getAttribute("data-view");
          state.page = 1;
          viewDate.style.display = state.view === "date" ? "" : "none";
          document.getElementById("view-topic").style.display =
            state.view === "topic" ? "" : "none";
          apply();
        });
      });

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
