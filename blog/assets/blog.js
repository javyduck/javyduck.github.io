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
  };

  function updateToggleIcon() {
    var btn = document.querySelector(".theme-toggle");
    if (!btn) return;
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    btn.textContent = dark ? "☀" : "☾";
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateToggleIcon();

    // ---------- category filter (index page) ----------
    var chips = document.querySelectorAll(".chip[data-category]");
    if (chips.length) {
      chips.forEach(function (chip) {
        chip.addEventListener("click", function () {
          chips.forEach(function (c) { c.classList.remove("active"); });
          chip.classList.add("active");
          var cat = chip.getAttribute("data-category");
          document.querySelectorAll(".post-item").forEach(function (item) {
            var show = cat === "all" || item.getAttribute("data-category") === cat;
            item.style.display = show ? "" : "none";
          });
          // Hide year headings with no visible posts.
          document.querySelectorAll(".year-group").forEach(function (group) {
            var any = Array.prototype.some.call(
              group.querySelectorAll(".post-item"),
              function (item) { return item.style.display !== "none"; }
            );
            group.style.display = any ? "" : "none";
          });
        });
      });
    }

    // ---------- date/topic view toggle (index page) ----------
    var viewBtns = document.querySelectorAll(".view-btn[data-view]");
    if (viewBtns.length) {
      viewBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          viewBtns.forEach(function (b) { b.classList.remove("active"); });
          btn.classList.add("active");
          var view = btn.getAttribute("data-view");
          document.getElementById("view-date").style.display = view === "date" ? "" : "none";
          document.getElementById("view-topic").style.display = view === "topic" ? "" : "none";
        });
      });
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
