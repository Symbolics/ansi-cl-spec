/* Web edition scripts: symbol search (and, later, the contents sidebar).
 * Plain DOM methods only: book pages are XHTML (application/xhtml+xml), where innerHTML needs well-formed XML.
 * Features degrade to nothing without JavaScript. */
(function () {
  "use strict";

  var MAX_RESULTS = 20;
  var TYPE_SYMBOL = 0, TYPE_SECTION = 1, TYPE_GLOSSARY = 2;

  /* ---------- ranking (pure; also loaded by node for tests) ---------- */

  var variantCache = typeof WeakMap === "function" ? new WeakMap() : null;

  function stripNumber(s) {
    return s.replace(/^\S*\d\S*\s+/, "");
  }

  /* Lower-cased texts of an item that a query is matched against. */
  function variants(item) {
    var cached = variantCache && variantCache.get(item);
    if (cached) return cached;
    var label = String(item[0]).toLowerCase();
    var v = [label];
    var type = item[3];
    if (type === TYPE_SYMBOL) {
      var bare = label.replace(/^[*&(]+/, "");
      if (bare && bare !== label) v.push(bare);
    } else if (type === TYPE_SECTION) {
      var title = stripNumber(label);
      if (title !== label) v.push(title);
      if (item[4]) {
        var full = String(item[4]).toLowerCase();
        v.push(full);
        var fullTitle = stripNumber(full);
        if (fullTitle !== full) v.push(fullTitle);
      }
    }
    if (variantCache) variantCache.set(item, v);
    return v;
  }

  /* 0 exact, 1 prefix, 2 substring, 3 no match. */
  function tier(item, q) {
    var v = variants(item), best = 3;
    for (var i = 0; i < v.length; i++) {
      var t = v[i] === q ? 0 : v[i].indexOf(q) === 0 ? 1 : v[i].indexOf(q) > 0 ? 2 : 3;
      if (t < best) best = t;
    }
    return best;
  }

  /* Best matches of `query` among `items` (search.json items), at most `limit`.
   * Order: tier (exact, prefix, substring); symbols before sections before glossary; shorter label; index. */
  function rank(items, query, limit) {
    var q = String(query || "").trim().toLowerCase().replace(/\s+/g, " ");
    if (!q) return [];
    var hits = [];
    for (var i = 0; i < items.length; i++) {
      var t = tier(items[i], q);
      if (t < 3) hits.push({ item: items[i], tier: t, type: items[i][3], len: String(items[i][0]).length, idx: i });
    }
    hits.sort(function (a, b) {
      return a.tier - b.tier || a.type - b.type || a.len - b.len || a.idx - b.idx;
    });
    return hits.slice(0, limit || MAX_RESULTS).map(function (h) { return h.item; });
  }

  /* ---------- contents tree (pure; also loaded by node for tests) ---------- */

  /* Index path (e.g. [3, 0, 2]) of the first node, in document order, whose href file (without the
   * fragment) equals `file`, in toc.json nodes [title, href, children?]; null if none. */
  function findPath(nodes, file) {
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (String(n[1]).split("#")[0] === file) return [i];
      if (n[2]) {
        var sub = findPath(n[2], file);
        if (sub) return [i].concat(sub);
      }
    }
    return null;
  }

  if (typeof module === "object" && module && module.exports) {
    module.exports = { rank: rank, findPath: findPath };
    return; /* node: no DOM code below runs */
  }

  /* ---------- helpers ---------- */

  function siteRoot() {
    var s = document.currentScript;
    if (!s || !s.getAttribute("src")) {
      var all = document.getElementsByTagName("script");
      s = null;
      for (var i = 0; i < all.length; i++) {
        var src = all[i].getAttribute("src") || "";
        if (/(^|\/)assets\/site\.js$/.test(src)) { s = all[i]; break; }
      }
    }
    if (!s) return new URL("./", document.baseURI);
    return new URL("../", new URL(s.getAttribute("src"), document.baseURI));
  }

  function el(name, className, text) {
    var e = document.createElement(name);
    if (className) e.setAttribute("class", className);
    if (text) e.textContent = text;
    return e;
  }

  /* ---------- search ---------- */

  function initSearch(root) {
    var boxes = document.querySelectorAll(".site-search");
    if (!boxes.length) return;
    var index = null, loading = null, nextId = 0, inputs = [];

    function load() {
      if (index) return Promise.resolve(index);
      if (!loading) {
        loading = fetch(new URL("search.json", root).href)
          .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json();
          })
          .then(function (d) { index = d.items || []; return index; })
          .catch(function (e) { loading = null; throw e; });
      }
      return loading;
    }

    function go(item) {
      window.location.assign(new URL(item[2], root).href);
    }

    function build(box) {
      var uid = "site-search-" + (nextId++);
      var input = el("input", "site-search-input");
      input.setAttribute("type", "search");
      input.setAttribute("role", "combobox");
      input.setAttribute("autocomplete", "off");
      input.setAttribute("autocapitalize", "off");
      input.setAttribute("spellcheck", "false");
      input.setAttribute("enterkeyhint", "go");
      input.setAttribute("aria-label", "Search symbols, sections, glossary");
      input.setAttribute("aria-autocomplete", "list");
      input.setAttribute("aria-expanded", "false");
      input.setAttribute("aria-controls", uid + "-list");
      input.setAttribute("placeholder", "Search symbols and sections (/)");
      var status = el("span", "site-search-status");
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      var list = el("ul", "site-search-results");
      list.id = uid + "-list";
      list.setAttribute("role", "listbox");
      list.setAttribute("aria-label", "Search results");
      list.hidden = true;
      box.appendChild(input);
      box.appendChild(status);
      /* The list lives in <body>, not in the header: the header's clip-path would cut it off. */
      document.body.appendChild(list);
      box.hidden = false;
      box.removeAttribute("hidden");

      var results = [], active = -1, pendingEnter = false, current = "";

      function place() {
        var r = input.getBoundingClientRect();
        var doc = document.documentElement;
        var vw = doc.clientWidth;
        var width = Math.min(Math.max(r.width, 280), vw - 16);
        var left = Math.max(8, Math.min(r.left, vw - width - 8));
        list.style.left = (left + (window.pageXOffset || 0)) + "px";
        list.style.top = (r.bottom + (window.pageYOffset || 0) + 2) + "px";
        list.style.width = width + "px";
      }

      function close() {
        list.hidden = true;
        input.setAttribute("aria-expanded", "false");
        input.removeAttribute("aria-activedescendant");
        active = -1;
      }

      function setActive(i, scroll) {
        var opts = list.querySelectorAll('[role="option"]');
        if (active >= 0 && opts[active]) {
          opts[active].setAttribute("aria-selected", "false");
          opts[active].setAttribute("class", "site-search-option");
        }
        active = i;
        if (i >= 0 && opts[i]) {
          opts[i].setAttribute("aria-selected", "true");
          opts[i].setAttribute("class", "site-search-option site-search-active");
          input.setAttribute("aria-activedescendant", opts[i].id);
          if (scroll !== false && opts[i].scrollIntoView) opts[i].scrollIntoView({ block: "nearest" });
        } else {
          input.removeAttribute("aria-activedescendant");
        }
      }

      function note(text) {
        var li = el("li", "site-search-note", text);
        li.setAttribute("role", "presentation");
        list.appendChild(li);
      }

      function render() {
        while (list.firstChild) list.removeChild(list.firstChild);
        active = -1;
        input.removeAttribute("aria-activedescendant");
        var q = input.value;
        if (!q.trim()) { results = []; close(); status.textContent = ""; return; }
        results = index ? rank(index, q, MAX_RESULTS) : [];
        if (!index) note("Loading…");
        else if (!results.length) note("No matches");
        results.forEach(function (item, i) {
          var li = el("li", "site-search-option");
          li.id = uid + "-opt-" + i;
          li.setAttribute("role", "option");
          li.setAttribute("aria-selected", "false");
          li.appendChild(el("span", "site-search-label", item[0]));
          li.appendChild(el("span", "site-search-kind", " — " + item[1]));
          li.addEventListener("click", function () { go(item); });
          li.addEventListener("mousemove", function () { if (active !== i) setActive(i, false); });
          list.appendChild(li);
        });
        status.textContent = index ? (results.length ? results.length + " results" : "No matches") : "";
        place();
        list.hidden = false;
        input.setAttribute("aria-expanded", "true");
      }

      function ensure() {
        if (index) return;
        load().then(function () {
          if (document.activeElement === input || pendingEnter) render();
          if (pendingEnter) {
            pendingEnter = false;
            if (results.length) go(results[0]);
          }
        }, function () {
          pendingEnter = false;
          while (list.firstChild) list.removeChild(list.firstChild);
          note("Search index unavailable");
          place();
          list.hidden = false;
        });
      }

      input.addEventListener("focus", function () { ensure(); if (input.value.trim()) render(); });
      input.addEventListener("input", function () { ensure(); render(); });
      input.addEventListener("blur", function () { close(); });
      /* keep focus in the input while the pointer is on the list */
      list.addEventListener("mousedown", function (e) { e.preventDefault(); });
      window.addEventListener("resize", function () { if (!list.hidden) place(); });
      input.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          if (!results.length) return;
          e.preventDefault();
          if (list.hidden) { render(); }
          var n = results.length;
          var next = e.key === "ArrowDown" ? (active + 1) % n : (active <= 0 ? n - 1 : active - 1);
          setActive(next);
        } else if (e.key === "Enter") {
          e.preventDefault();
          if (!input.value.trim()) return;
          if (!index) { pendingEnter = true; ensure(); return; }
          var item = results[active >= 0 ? active : 0];
          if (item) go(item);
        } else if (e.key === "Escape") {
          if (input.value || !list.hidden) {
            e.preventDefault();
            input.value = "";
            results = [];
            render();
          } else {
            input.blur();
          }
        }
      });
      inputs.push(input);
    }

    for (var i = 0; i < boxes.length; i++) build(boxes[i]);

    document.addEventListener("keydown", function (e) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return;
      var t = e.target, name = t && t.nodeName ? t.nodeName.toLowerCase() : "";
      if (name === "input" || name === "textarea" || name === "select" || (t && t.isContentEditable)) return;
      var first = null;
      for (var j = 0; j < inputs.length; j++) {
        if (inputs[j].offsetParent !== null || inputs[j].getClientRects().length) { first = inputs[j]; break; }
      }
      if (!first) return;
      e.preventDefault();
      first.focus();
      first.select();
    });
  }

  /* ---------- sidebar ---------- */

  var STORE_OPEN = "site-toc-open", STORE_HIDDEN = "site-sidebar-hidden";

  function load(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function save(key, value) {
    try {
      if (value === null) window.localStorage.removeItem(key); else window.localStorage.setItem(key, value);
    } catch (e) { /* storage unavailable: state just isn't remembered */ }
  }

  function initSidebar(root) {
    var sb = document.getElementById("site-sidebar");
    if (!sb || !document.body) return;
    var page = sb.getAttribute("data-site-page") || "";
    var html = document.documentElement;
    var wide = window.matchMedia ? window.matchMedia("(min-width: 64em)") : { matches: false };
    var header = document.querySelector(".site-header");
    var contentsLink = header && header.querySelector(".site-contents");
    var tocData = null, loading = null, rendered = false, current = null, drawerOpen = false;
    var opened = {}; /* "3/0/2" -> true: branches the user left open */
    try { opened = JSON.parse(load(STORE_OPEN) || "{}") || {}; } catch (e) { opened = {}; }
    if (typeof opened !== "object") opened = {};

    /* skeleton */
    var head = el("div", "site-sidebar-head");
    var title = el("a", "site-sidebar-title", "Contents");
    title.setAttribute("href", new URL("nav.xhtml", root).href);
    var hideBtn = el("button", "site-sidebar-hide", "Hide");
    hideBtn.setAttribute("type", "button");
    hideBtn.setAttribute("title", "Hide the contents sidebar");
    var closeBtn = el("button", "site-sidebar-close", "×");
    closeBtn.setAttribute("type", "button");
    closeBtn.setAttribute("aria-label", "Close contents");
    head.appendChild(title);
    head.appendChild(hideBtn);
    head.appendChild(closeBtn);
    var body = el("div", "site-sidebar-body", "Loading contents…");
    sb.appendChild(head);
    sb.appendChild(body);
    var backdrop = el("div", "site-backdrop");
    document.body.appendChild(backdrop);

    var menuBtn = null;
    if (header) {
      menuBtn = el("button", "site-menu-button", "☰ Contents");
      menuBtn.setAttribute("type", "button");
      menuBtn.setAttribute("aria-controls", "site-sidebar");
      menuBtn.setAttribute("aria-expanded", "false");
      header.insertBefore(menuBtn, contentsLink || null);
      html.classList.add("site-has-menu"); /* hides the plain Contents link; it stays for no-JS */
    }

    function visible() {
      return wide.matches ? !html.classList.contains("site-sidebar-collapsed") : drawerOpen;
    }
    function syncState() {
      if (menuBtn) menuBtn.setAttribute("aria-expanded", visible() ? "true" : "false");
      if (visible()) ensureRendered();
    }

    /* ---- tree ---- */

    function key(path) { return path.join("/"); }

    function makeList(nodes, prefix, depth) {
      var ul = el("ul", "site-toc");
      for (var i = 0; i < nodes.length; i++) ul.appendChild(makeItem(nodes[i], prefix.concat([i]), depth));
      return ul;
    }

    function setOpen(li, open) {
      var btn = li.firstChild.firstChild;
      var node = li._node;
      if (open && !li._list) {
        li._list = makeList(node[2], li._path, li._depth + 1);
        li.appendChild(li._list);
      }
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (li._list) li._list.hidden = !open;
    }

    function makeItem(node, path, depth) {
      var li = el("li", "site-toc-item");
      li._node = node; li._path = path; li._depth = depth;
      var row = el("div", "site-toc-row");
      var hasKids = node[2] && node[2].length;
      if (hasKids) {
        var btn = el("button", "site-toc-toggle");
        btn.setAttribute("type", "button");
        btn.setAttribute("aria-expanded", "false");
        btn.setAttribute("aria-label", "Subsections of " + node[0]);
        btn.addEventListener("click", function () {
          var open = btn.getAttribute("aria-expanded") !== "true";
          setOpen(li, open);
          if (open) opened[key(path)] = true; else delete opened[key(path)];
          save(STORE_OPEN, JSON.stringify(opened));
        });
        row.appendChild(btn);
      } else {
        row.appendChild(el("span", "site-toc-spacer"));
      }
      var a = el("a", "site-toc-link", node[0]);
      a.setAttribute("href", new URL(node[1], root).href);
      a.setAttribute("title", node[0]);
      row.appendChild(a);
      li.appendChild(row);
      if (hasKids && (opened[key(path)] || (current && isPrefix(path, current)))) setOpen(li, true);
      if (current && key(path) === key(current)) a.setAttribute("aria-current", "page");
      return li;
    }

    function isPrefix(p, full) {
      if (p.length >= full.length) return false;
      for (var i = 0; i < p.length; i++) if (p[i] !== full[i]) return false;
      return true;
    }

    function reveal() {
      var a = body.querySelector('[aria-current="page"]');
      if (!a || !visible()) return;
      var r = a.getBoundingClientRect(), b = sb.getBoundingClientRect();
      sb.scrollTop += (r.top - b.top) - sb.clientHeight / 3;
    }

    function fetchToc() {
      if (tocData) return Promise.resolve(tocData);
      if (!loading) {
        loading = fetch(new URL("toc.json", root).href)
          .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json();
          })
          .then(function (d) { tocData = d.toc || []; return tocData; })
          .catch(function (e) { loading = null; throw e; });
      }
      return loading;
    }

    function ensureRendered() {
      if (rendered) return;
      rendered = true;
      fetchToc().then(function (nodes) {
        current = findPath(nodes, page);
        while (body.firstChild) body.removeChild(body.firstChild);
        var nav = el("nav", "site-toc-nav");
        nav.setAttribute("aria-label", "Table of contents");
        nav.appendChild(makeList(nodes, [], 0));
        body.appendChild(nav);
        reveal();
      }, function () {
        rendered = false;
        body.textContent = "Contents unavailable. ";
        var a = el("a", null, "Open the contents page");
        a.setAttribute("href", new URL("nav.xhtml", root).href);
        body.appendChild(a);
      });
    }

    /* ---- wide: collapsible column ---- */

    function applyWide() {
      html.classList.toggle("site-sidebar-collapsed", load(STORE_HIDDEN) === "1");
    }
    sb.hidden = false;
    sb.removeAttribute("hidden"); /* CSS decides when it shows */
    html.classList.add("site-sidebar-on");
    applyWide();

    function setCollapsed(c) {
      html.classList.toggle("site-sidebar-collapsed", c);
      save(STORE_HIDDEN, c ? "1" : null);
      syncState();
      if (c && menuBtn) menuBtn.focus();
      else if (!c) { reveal(); hideBtn.focus(); }
    }
    hideBtn.addEventListener("click", function () { setCollapsed(true); });

    /* ---- narrow: drawer ---- */

    function focusables() {
      var all = sb.querySelectorAll("a[href], button");
      var out = [];
      for (var i = 0; i < all.length; i++) if (all[i].offsetParent !== null) out.push(all[i]);
      return out;
    }
    function openDrawer() {
      drawerOpen = true;
      html.classList.add("site-drawer-open");
      syncState();
      reveal();
      closeBtn.focus();
    }
    function closeDrawer(refocus) {
      if (!drawerOpen) return;
      drawerOpen = false;
      html.classList.remove("site-drawer-open");
      syncState();
      if (refocus && menuBtn) menuBtn.focus();
    }
    closeBtn.addEventListener("click", function () { closeDrawer(true); });
    backdrop.addEventListener("click", function () { closeDrawer(true); });
    sb.addEventListener("click", function (e) {
      var t = e.target;
      if (t && t.closest && t.closest("a") && drawerOpen) closeDrawer(false);
    });
    document.addEventListener("keydown", function (e) {
      if (!drawerOpen || wide.matches) return;
      if (e.key === "Escape") { e.preventDefault(); closeDrawer(true); }
      else if (e.key === "Tab") {
        var f = focusables();
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (!sb.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
        else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });

    if (menuBtn) {
      menuBtn.addEventListener("click", function () {
        if (wide.matches) setCollapsed(!html.classList.contains("site-sidebar-collapsed"));
        else if (drawerOpen) closeDrawer(true); else openDrawer();
      });
    }

    function onResize() {
      if (wide.matches && drawerOpen) { drawerOpen = false; html.classList.remove("site-drawer-open"); }
      syncState();
    }
    if (wide.addEventListener) wide.addEventListener("change", onResize);
    else if (wide.addListener) wide.addListener(onResize);

    syncState();
  }

  /* ---------- start ---------- */

  function start() {
    var root = siteRoot();
    initSearch(root);
    initSidebar(root);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
