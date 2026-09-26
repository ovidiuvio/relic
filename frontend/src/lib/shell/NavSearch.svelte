<script>
  // Scoped search in the navbar. The bar holds the whole query: free text plus filter tokens
  // (type: tag: by: in:, see search/query.js), coloured as you type. It always shows what the
  // list is filtered by (?search= ?type= ?tag= ?owner=), so clicking a facet, a tag or an owner
  // rewrites it, and Enter applies everything in it. The scope chip says where it searches:
  // pick another list or space there, or type in:. While it has focus, a panel under it lists the
  // filters you can type and completes the one you're typing.
  // On a list page the list follows the bar as you type (a token applies once you've finished
  // it). The first change adds a history entry and later ones replace it, so Back, or Esc,
  // returns to the list as it was. Meanwhile the panel shows what the query finds Everywhere
  // (everything you can see); on pages without a list it searches the scope, Everywhere unless
  // you pick another. Matches come with a preview: ↑↓ choose, Enter opens (Shift+Enter in a new
  // tab), Ctrl+Enter shows them all. Ctrl+K starts in Everywhere, and Backspace at the start of
  // the bar widens to it.
  // An empty bar lists your searches: pinned (on the server) and recent (this browser); typing
  // narrows them. Searches you commit (Enter, a match opened, a live-filtered list you leave)
  // go to Recent.
  //   / or Ctrl+K focus · ↑↓ choose · Tab complete · Enter applies · Esc closes the panel, then
  //   puts the field back and leaves
  import { tick, untrack } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import SearchPanel from "../search/SearchPanel.svelte";
  import { suggest, applySuggestion } from "../search/suggest";
  import { navigate } from "../../utils/navigation";
  import { searchScope, spaceScope, LIST_SCOPES, EVERYWHERE } from "./searchScope";
  import { segments, parseQuery, resolveFilters, formatQuery, sameFilters, builtinScope, FILTER_KEYS, QUERY_PARAMS, needsEverywhere } from "../search/query";
  import { session } from "../../stores/session";
  import { sidebarData, refreshSidebar } from "./sidebarData";
  import { spaces as spacesApi, searchTags } from "../../services/api";
  import { fetchScope } from "../search/scopeFetch";
  import { searchHistory, pathLabel } from "../search/history.svelte.js";
  import { showToast } from "../../stores/toastStore";

  let { section, routeProps = {} } = $props();


  const pageScope = $derived(searchScope(section, routeProps));
  let picked = $state(null); // a scope chosen in the menu, until the search runs or the page changes
  const scope = $derived(picked ?? pageScope);

  // The filters in the page's URL, re-read on every route change.
  const urlFilters = $derived.by(() => {
    routeProps;
    const p = new URLSearchParams(location.search);
    return Object.fromEntries(QUERY_PARAMS.map((k) => [k, p.get(k) || ""]));
  });

  let root = $state();
  let input = $state();
  let mirror = $state();
  let menuEl = $state();
  let query = $state("");
  let focused = $state(false);
  let within = $state(false); // focus is somewhere in the bar or its panel (a rename field)
  let caret = $state(0);
  let menuOpen = $state(false);
  let flagAll = $state(false); // after a failed Enter, underline problems even under the caret
  let applied = ""; // the text of the last search that ran, to show it back as you typed it
  let panelClosed = $state(false); // Esc closed the panel; typing opens it again
  let active = $state(-1); // the option chosen with ↑↓: a suggestion, a saved search or a match
  let tags = $state({}); // top tags per scope key, for tag: suggestions

  // What a query means, ignoring anything that doesn't resolve.
  function filtersOf(text) {
    const { search, tokens } = parseQuery(text);
    return { search, ...resolveFilters(tokens, { publicId: $session.publicId, filters: [...FILTER_KEYS, "from"] }).params };
  }

  // The text for the page's filters: what you typed if it means the same (keeping your order
  // and spelling), else the filters written out.
  function textFor(filters) {
    if (sameFilters(filtersOf(query), filters)) return query;
    if (applied && sameFilters(filtersOf(applied), filters)) return applied;
    return formatQuery(filters, { publicId: $session.publicId });
  }

  // Follow the page, so a facet, tag or owner click shows up in the bar.
  $effect(() => {
    const filters = urlFilters;
    untrack(() => {
      picked = null;
      // Someone else moved the page (a link, Back): live filtering starts over and the panel closes.
      const ours = live && location.pathname + location.search === live.url;
      if (!ours) {
        live = null;
        if (focused) input?.blur();
      }
      query = textFor(filters);
    });
  });

  // ---- live filtering on list pages ----
  let live = null; // { start: the URL before, text: the bar's text then, url: the last one set }
  let liveTimer;

  function scheduleLive() {
    clearTimeout(liveTimer);
    liveTimer = setTimeout(applyLive, 250);
  }

  function applyLive() {
    if (!focused || picked || location.pathname !== pageScope.path) return;
    // A token applies once you've finished it, so tag:w doesn't empty the list on the way to tag:work.
    if (segments(query).some((s) => s.kind === "token" && caret >= s.start && caret <= s.end)) return;
    const { search, tokens } = parseQuery(query);
    if ("in" in tokens || (needsEverywhere(tokens) && pageScope.key !== EVERYWHERE.key)) return; // another page: that waits for Enter
    const { params, problems } = resolveFilters(tokens, { publicId: $session.publicId, filters: pageScope.filters });
    if (problems.length) return;
    const url = urlFor(pageScope, search, params);
    const here = location.pathname + location.search;
    if (url === here) return;
    applied = query;
    if (!live) {
      live = { start: here, text: textFor(urlFilters), url };
      navigate(url);
    } else {
      live.url = url;
      navigate(url, { replace: true });
    }
  }

  /** Esc: put the list back as it was before you started typing. */
  function cancelLive() {
    clearTimeout(liveTimer);
    if (!live) return false;
    const { text } = live;
    live = null;
    applied = text;
    history.back();
    return true;
  }

  // Tokens that won't work here are underlined, once the caret has left them.
  const segs = $derived(
    segments(query).map((s) => {
      if (s.kind !== "token") return s;
      const problem =
        s.key === "in"
          ? s.value ? null : "in: needs a list or a space"
          : resolveFilters({ [s.key]: s.value }, { publicId: $session.publicId, filters: scope.filters }).problems[0] ?? null;
      return { ...s, problem };
    })
  );
  const editing = (s) => focused && !flagAll && caret >= s.start && caret <= s.end;
  const problem = $derived(segs.find((s) => s.problem && !editing(s))?.problem ?? null);

  const keys = $derived([...scope.filters, "in"]);

  // Completing tag: or type: counts what the rest of the query finds, so a suggestion says how
  // far it would narrow the results. (The whole list's top tags stand in until those arrive.)
  const completion = $derived.by(() => {
    const seg = segments(query).find((x) => x.kind === "token" && (x.key === "tag" || x.key === "type") && caret >= x.start && caret <= x.end);
    if (!seg) return null;
    const rest = parseQuery(query.slice(0, seg.start) + query.slice(seg.end));
    const { params } = resolveFilters(rest.tokens, { publicId: $session.publicId, filters: scope.filters });
    const filters = { search: rest.search.trim(), ...params };
    return { filters, key: `${scope.key}|${JSON.stringify(filters)}`, narrowed: Object.values(filters).some(Boolean) };
  });
  let facetData = $state(null); // { key, tags, types } for the completion
  let facetTimer;
  $effect(() => {
    const c = completion;
    const sc = scope;
    untrack(() => {
      clearTimeout(facetTimer);
      if (!c || facetData?.key === c.key) return;
      facetTimer = setTimeout(async () => {
        try {
          const data = await fetchScope(sc, c.filters, { limit: 1, facets: true });
          if (data) facetData = { key: c.key, tags: data.facets?.tags ?? [], types: data.facets?.types ?? {} };
        } catch {
          // Suggestions just go without counts.
        }
      }, 150);
    });
  });
  const counted = $derived(completion && facetData?.key === completion.key ? facetData : null);

  // Typing a tag: any tag you can see that matches, not only the top ones counted above.
  const tagTyped = $derived.by(() => {
    const seg = segments(query).find((x) => x.kind === "token" && x.key === "tag" && caret >= x.start && caret <= x.end);
    return seg?.value.trim().toLowerCase() || "";
  });
  let moreTags = $state({ q: "", tags: [] });
  const tagCache = new Map();
  let tagTimer;
  $effect(() => {
    const q = tagTyped;
    untrack(() => {
      clearTimeout(tagTimer);
      if (!q || moreTags.q === q) return;
      if (tagCache.has(q)) return void (moreTags = { q, tags: tagCache.get(q) });
      tagTimer = setTimeout(async () => {
        try {
          const { data } = await searchTags(q, 10);
          tagCache.set(q, data.tags);
          if (tagTyped === q) moreTags = { q, tags: data.tags };
        } catch {
          // Suggestions just stay with the counted ones.
        }
      }, 150);
    });
  });

  const suggestions = $derived(
    suggest(query, caret, {
      keys,
      tags: counted?.tags ?? tags[scope.key],
      typeCounts: counted?.types,
      moreTags: tagTyped && moreTags.q === tagTyped ? moreTags.tags : [],
      inResults: !!counted && completion.narrowed,
      spaces: $sidebarData.spaces,
      scopeLabel: scope.label,
    })
  );

  const panelOpen = $derived((focused || within) && !menuOpen && !panelClosed);

  // ---- your searches ----
  const here = $derived.by(() => {
    routeProps;
    return location.pathname + location.search;
  });
  const searches = $derived.by(() => {
    const spaces = $sidebarData.spaces;
    const pinned = (searchHistory.pinned ?? []).map((p) => ({ kind: "pinned", ...p, label: pathLabel(p.path, spaces) }));
    const pinnedPaths = new Set(pinned.map((p) => p.path));
    const recent = searchHistory.recent
      .filter((e) => !pinnedPaths.has(e.path))
      .map((e) => ({ kind: "recent", ...e, label: pathLabel(e.path, spaces) }));
    const q = query.trim().toLowerCase();
    // Until you change what the bar shows, you see them all; typing narrows them.
    if (!q || untouched) return [...pinned, ...recent.slice(0, 8)];
    // Typing narrows them; the search you're looking at isn't worth offering back.
    return [...pinned, ...recent]
      .filter((h) => h.path !== here && (h.query.toLowerCase().includes(q) || h.name?.toLowerCase().includes(q)))
      .slice(0, 4);
  });

  // The bar still shows the page's own filters (nothing typed since).
  const untouched = $derived(sameFilters(filtersOf(query), urlFilters));

  // On a filtered list, offer to pin what it shows.
  const pinCurrent = $derived.by(() => {
    if (!onListPage || picked || !QUERY_PARAMS.some((k) => urlFilters[k])) return null;
    if (!sameFilters(filtersOf(query), urlFilters)) return null;
    return { pinned: !!searchHistory.pinnedFor(here) };
  });

  // Everything ↑↓ moves through, in panel order.
  const options = $derived(
    suggestions.items.length
      ? suggestions.items.map((item) => ({ kind: "suggestion", item }))
      : [
          ...searches.map((item) => ({ kind: "history", item })),
          ...(showResults && results ? results.spaces.map((item) => ({ kind: "space", item })) : []),
          ...(showResults && results ? results.relics.map((item) => ({ kind: "relic", item })) : []),
        ]
  );
  $effect(() => {
    options;
    active = -1;
  });
  const suggestionIndex = $derived(options[active]?.kind === "suggestion" ? active : -1);
  const historyIndex = $derived(options[active]?.kind === "history" ? active : -1);
  const spaceCount = $derived(showResults && results ? results.spaces.length : 0);
  const spaceIndex = $derived(options[active]?.kind === "space" ? active - searches.length : -1);
  const resultIndex = $derived(options[active]?.kind === "relic" ? active - searches.length - spaceCount : -1);

  function runHistory(entry, newTab = false) {
    if (newTab) {
      window.open(entry.path, "_blank", "noopener");
      return;
    }
    searchHistory.record(entry);
    applied = entry.query;
    picked = null;
    live = null;
    input.blur();
    if (entry.path !== location.pathname + location.search) navigate(entry.path);
    else query = entry.query;
  }

  async function pinEntry(entry) {
    try {
      await searchHistory.pin({ query: entry.query, path: entry.path });
      showToast("Pinned", "success");
    } catch (e) {
      showToast(e.response?.data?.detail || "Couldn’t pin that search", "error");
    }
  }

  async function unpinEntry(entry) {
    try {
      await searchHistory.unpin(entry.id);
    } catch {
      showToast("Couldn’t unpin that search", "error");
    }
  }

  async function renameEntry(entry, name) {
    input.focus();
    if (name === null || (name ?? "") === (entry.name ?? "")) return;
    try {
      await searchHistory.rename(entry.id, name);
    } catch {
      showToast("Couldn’t rename that search", "error");
    }
  }

  function togglePinCurrent() {
    const pinned = searchHistory.pinnedFor(here);
    if (pinned) unpinEntry(pinned);
    else pinEntry({ query: query.trim(), path: here });
  }

  // Top tags for tag: suggestions, fetched once per scope when the bar gets focus.
  function loadTags(sc) {
    if (sc.key in tags) return;
    tags = { ...tags, [sc.key]: undefined };
    fetchScope(sc, {}, { limit: 1, facets: true })
      .then((data) => (tags = { ...tags, [sc.key]: data?.facets?.tags ?? [] }))
      .catch(() => (tags = { ...tags, [sc.key]: [] }));
  }

  // ---- matches: Everywhere on a list page, else the scope ----
  let results = $state(null); // { relics, total, spaces } for the query, or null
  let listHere = $state(null); // { label, total }: what the list under the panel shows for the query
  let resultsLoading = $state(false);
  let resultsTimer;
  let resultsSeq = 0;
  let panelWidth = $state(null); // px when there's room for the preview

  const onListPage = $derived.by(() => {
    routeProps;
    return location.pathname === pageScope.path;
  });
  // On a list the list shows its own matches, so the panel searches Everywhere (except on
  // Everywhere's own page, where the list already is that).
  const resultsScope = $derived(onListPage && !picked ? EVERYWHERE : scope);
  const showResults = $derived(!(onListPage && !picked && pageScope.key === EVERYWHERE.key));

  $effect(() => {
    query;
    resultsScope;
    caret;
    const on = focused && showResults;
    untrack(() => scheduleResults(on));
  });

  function scheduleResults(on) {
    clearTimeout(resultsTimer);
    if (!on) {
      results = null;
      listHere = null;
      return;
    }
    // Wait for a token to be finished, as the live list does.
    if (segments(query).some((seg) => seg.kind === "token" && caret >= seg.start && caret <= seg.end)) return;
    const { search, tokens } = parseQuery(query);
    const target = resultsScope;
    const { params, problems } = resolveFilters(tokens, { publicId: $session.publicId, filters: target.filters });
    if ("in" in tokens || problems.length || (!search.trim() && !Object.keys(params).length)) {
      results = null;
      listHere = null;
      return;
    }
    const filters = { search: search.trim(), ...params };
    const listToo = onListPage && !picked && pageScope.key !== target.key;
    resultsTimer = setTimeout(async () => {
      const seq = ++resultsSeq;
      resultsLoading = true;
      try {
        const [data, spaceData, listData] = await Promise.all([
          fetchScope(target, filters, { limit: 7, relevance: true }),
          // Everywhere also finds spaces by name.
          target.key === EVERYWHERE.key && search.trim() ? spacesApi.list({ search: search.trim(), limit: 3 }).catch(() => null) : null,
          listToo ? fetchScope(pageScope, { search: search.trim(), ...resolveFilters(tokens, { publicId: $session.publicId, filters: pageScope.filters }).params }, { limit: 1 }).catch(() => null) : null,
        ]);
        if (seq !== resultsSeq) return;
        results = data ? { ...data, spaces: spaceData?.spaces ?? [] } : null;
        listHere = listToo && listData ? { label: pageScope.label, total: listData.total } : null;
      } catch {
        if (seq === resultsSeq) results = null;
      } finally {
        if (seq === resultsSeq) resultsLoading = false;
      }
    }, 200);
  }

  /** Every match on its list: Everywhere's page, or the scope's. */
  function seeAll() {
    if (resultsScope.key === EVERYWHERE.key) picked = pageScope.key === EVERYWHERE.key ? null : EVERYWHERE;
    submit();
  }

  function openSpace(space) {
    picked = null;
    input.blur();
    navigate(`/spaces/${space.id}`);
  }

  function measure() {
    if (!root) return;
    const room = window.innerWidth - root.getBoundingClientRect().left - 12;
    panelWidth = room >= 820 ? Math.min(940, room) : null;
  }

  function openResult(relic, newTab = false) {
    if (newTab) {
      window.open(`/${relic.id}`, "_blank", "noopener");
      return;
    }
    // The search that found it goes to Recent, as the list it searched.
    const { search, tokens } = parseQuery(query);
    const { params } = resolveFilters(tokens, { publicId: $session.publicId, filters: resultsScope.filters });
    searchHistory.record({ query, path: urlFor(resultsScope, search, params), label: resultsScope.label });
    picked = null;
    input.blur();
    navigate(`/${relic.id}`);
  }

  async function setQuery(text, at) {
    query = text;
    panelClosed = false;
    await tick();
    input.focus();
    input.setSelectionRange(at, at);
    sync();
    scheduleLive();
  }

  function pickSuggestion(item) {
    const next = applySuggestion(query, item);
    setQuery(next.text, next.caret);
  }

  // A filter key or the example, clicked in the panel: the example replaces the query, a key is
  // added where the caret is (with a space before it when needed).
  function insertText(text) {
    if (text.includes(" ")) return setQuery(text, text.length);
    const before = query.slice(0, caret);
    const pad = before && !/\s$/.test(before) ? " " : "";
    setQuery(before + pad + text + query.slice(caret), caret + pad.length + text.length);
  }

  // The mirror draws the coloured text under the (transparent) input; keep them scrolled together.
  function sync() {
    if (!input || !mirror) return;
    mirror.scrollLeft = input.scrollLeft;
    caret = input.selectionStart ?? 0;
  }
  $effect(() => {
    query;
    tick().then(sync);
  });

  // Where an in: value points: a list, one of your spaces, or any space you can see by name or ID.
  async function scopeFor(value) {
    const builtin = builtinScope(value);
    if (builtin) return LIST_SCOPES.find((s) => s.key === builtin);
    const v = value.trim().toLowerCase();
    if (!v) return null;
    const match = (list) => list.find((s) => s.id === v || s.name?.toLowerCase() === v);
    const known = match($sidebarData.spaces);
    if (known) return spaceScope(known);
    try {
      const { spaces } = await spacesApi.list({ search: value.trim(), limit: 10 });
      const found = match(spaces) ?? (spaces.length === 1 ? spaces[0] : null);
      return found ? spaceScope(found) : null;
    } catch {
      return null;
    }
  }

  async function submit() {
    const { search, tokens } = parseQuery(query);
    let target = needsEverywhere(tokens) ? EVERYWHERE : scope;
    if ("in" in tokens) {
      target = await scopeFor(tokens.in);
      if (!target) {
        flagAll = true;
        showToast(`No list or space called “${tokens.in}”`, "error");
        return;
      }
    }
    const { params, problems } = resolveFilters(tokens, { publicId: $session.publicId, filters: target.filters });
    if (problems.length) {
      flagAll = true;
      showToast(target === pageScope || !("in" in tokens) ? problems[0] : `${problems[0]} (in ${target.label})`, "error");
      return;
    }
    clearTimeout(liveTimer);
    const url = urlFor(target, search, params);
    // in: has done its job once the chip shows the new scope.
    query = segments(query).filter((seg) => seg.key !== "in").map((seg) => seg.raw).join("").replace(/\s+/g, " ").trim();
    applied = query;
    searchHistory.record({ query, path: url, label: target.label });
    picked = null;
    // Live filtering already added this search's history entry; Enter just settles it.
    const replace = !!live && target.path === pageScope.path;
    live = null;
    input.blur();
    if (url !== location.pathname + location.search) navigate(url, { replace });
  }

  // The URL for a search: the same list keeps its sort and other options; another starts fresh.
  function urlFor(target, search, params) {
    const next = new URLSearchParams(location.pathname === target.path ? location.search : "");
    for (const key of QUERY_PARAMS) next.delete(key);
    if (search.trim()) next.set("search", search.trim());
    for (const [key, value] of Object.entries(params)) next.set(key, value);
    const qs = next.toString();
    return `${target.path}${qs ? `?${qs}` : ""}`;
  }

  function reset() {
    picked = null;
    query = applied && sameFilters(filtersOf(applied), urlFilters) ? applied : formatQuery(urlFilters, { publicId: $session.publicId });
  }

  function onkeydown(event) {
    const opts = panelOpen ? options : [];
    const chosen = opts[active];
    const newTab = event.shiftKey;
    if ((event.key === "ArrowDown" || event.key === "ArrowUp") && opts.length) {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      active = active + step < -1 ? opts.length - 1 : active + step >= opts.length ? -1 : active + step;
    } else if (event.key === "Tab" && !event.shiftKey && opts[0]?.kind === "suggestion") {
      event.preventDefault();
      pickSuggestion((chosen ?? opts[0]).item);
    } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      seeAll();
    } else if (event.key === "Backspace" && input.selectionStart === 0 && input.selectionEnd === 0 && scope.key !== EVERYWHERE.key) {
      // Backspace at the very start removes the list chip: search everything instead.
      event.preventDefault();
      picked = pageScope.key === EVERYWHERE.key ? null : EVERYWHERE;
      panelClosed = false;
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (chosen?.kind === "suggestion") pickSuggestion(chosen.item);
      else if (chosen?.kind === "space") openSpace(chosen.item);
      else if (chosen?.kind === "history") runHistory(chosen.item, newTab);
      else if (chosen?.kind === "relic") openResult(chosen.item, newTab);
      else submit();
    } else if (event.key === "Escape") {
      if (panelOpen) {
        panelClosed = true;
        active = -1;
        return;
      }
      if (!cancelLive()) reset();
      input.blur();
    } else {
      flagAll = false;
      panelClosed = false;
      tick().then(sync);
    }
  }

  function onBlur() {
    focused = false;
    // Leaving a list you filtered as you typed keeps that search: it goes to Recent.
    if (live && query.trim()) searchHistory.record({ query, path: live.url, label: pageScope.label });
    live = null;
    clearTimeout(liveTimer);
    tick().then(sync);
  }

  function onWindowKeydown(event) {
    const slash = event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey;
    const ctrlK = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";
    if (!slash && !ctrlK) return;
    if (event.target.closest?.('input, textarea, select, [contenteditable="true"], .monaco-editor')) return;
    event.preventDefault();
    if (ctrlK && pageScope.key !== EVERYWHERE.key) picked = EVERYWHERE;
    input.focus();
    input.select();
  }

  // A click on the bar's padding or icon goes to the field.
  function onBarMousedown(event) {
    if (event.target.closest("button, input, .scope-menu, .search-panel")) return;
    event.preventDefault();
    input.focus();
  }

  // ---- scope menu ----
  const menuItems = $derived.by(() => {
    const items = [...LIST_SCOPES, ...$sidebarData.spaces.map((s) => ({ ...spaceScope(s), space: true }))];
    // The page's own scope (a space you only visit, All relics…) stays pickable.
    if (!items.some((i) => i.key === pageScope.key)) items.unshift(pageScope);
    return items;
  });

  async function openMenu() {
    menuOpen = true;
    if (!$sidebarData.spaces.length) refreshSidebar();
    await tick();
    const items = [...(menuEl?.querySelectorAll("[role=menuitemradio]") ?? [])];
    (items.find((el) => el.getAttribute("aria-checked") === "true") ?? items[0])?.focus();
  }

  function closeMenu(refocus = true) {
    menuOpen = false;
    if (refocus) input.focus();
  }

  function pick(item) {
    picked = item.key === pageScope.key ? null : item;
    closeMenu();
    // With something to search for, search there now; otherwise wait for the query.
    if (query.trim()) submit();
  }

  function onChipKeydown(event) {
    if (["ArrowDown", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      openMenu();
    }
  }

  function onMenuKeydown(event) {
    const items = [...menuEl.querySelectorAll("[role=menuitemradio]")];
    const i = items.indexOf(document.activeElement);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = event.key === "ArrowDown" ? (i + 1) % items.length : (i - 1 + items.length) % items.length;
      items[next]?.focus();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeMenu();
    } else if (event.key === "Tab") {
      closeMenu(false);
    }
  }

  function onWindowClick(event) {
    if (menuOpen && !root.contains(event.target)) menuOpen = false;
  }
</script>

<svelte:window onkeydown={onWindowKeydown} onclick={onWindowClick} onresize={() => focused && measure()} />

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="r-nav-search nav-search"
  class:is-focus={focused || menuOpen}
  role="search"
  bind:this={root}
  onmousedown={onBarMousedown}
  onfocusin={() => (within = true)}
  onfocusout={(e) => (within = root.contains(e.relatedTarget))}
>
  <button
    type="button"
    class="r-nav-scope scope-btn"
    onclick={() => (menuOpen ? closeMenu() : openMenu())}
    onkeydown={onChipKeydown}
    aria-haspopup="menu"
    aria-expanded={menuOpen}
    title="Where to search"
  >
    {scope.label}<Icon name="chev" />
  </button>
  <Icon name="search" />
  <div class="q-field">
    <div class="q-mirror" bind:this={mirror} aria-hidden="true"><span>{#each segs as s (s.start)}{#if s.kind === "token"}<span class="q-tok" class:is-bad={s.problem && !editing(s)}>{s.raw}</span>{:else}{s.raw}{/if}{/each}</span></div>
    <input
      bind:this={input}
      bind:value={query}
      placeholder={scope.placeholder}
      aria-label={scope.placeholder}
      role="combobox"
      aria-expanded={panelOpen && suggestions.items.length > 0}
      aria-controls="search-suggestions"
      aria-activedescendant={suggestionIndex >= 0 ? `search-sugg-${suggestionIndex}` : historyIndex >= 0 ? `search-hist-${historyIndex}` : undefined}
      aria-invalid={problem ? "true" : undefined}
      title={problem ?? ""}
      autocomplete="off"
      spellcheck="false"
      {onkeydown}
      oninput={() => (sync(), scheduleLive())}
      onkeyup={sync}
      onclick={sync}
      onmousedown={() => (panelClosed = false)}
      onselect={sync}
      onscroll={sync}
      onfocus={() => ((focused = true), (panelClosed = false), measure(), loadTags(scope), searchHistory.load(), $sidebarData.spaces.length || refreshSidebar(), sync())}
      onblur={onBlur}
    />
  </div>
  <kbd class="r-kbd">{focused ? "Esc" : "/"}</kbd>

  {#if panelOpen}
    <SearchPanel
      {keys}
      scopeLabel={scope.label}
      heading={suggestions.heading}
      items={suggestions.items}
      note={suggestions.note}
      active={suggestionIndex}
      empty={!query.trim() || untouched}
      results={showResults ? results : null}
      resultsLabel={resultsScope.key === EVERYWHERE.key ? null : resultsScope.label}
      here={query.trim() ? listHere : null}
      {spaceIndex}
      onopenspace={openSpace}
      loading={resultsLoading}
      highlight={parseQuery(query).search}
      {resultIndex}
      width={panelWidth}
      onpick={pickSuggestion}
      oninsert={insertText}
      onopen={openResult}
      onseeall={seeAll}
      history={searches}
      {historyIndex}
      {pinCurrent}
      onrun={runHistory}
      onpin={pinEntry}
      onunpin={unpinEntry}
      onforget={(h) => searchHistory.forget(h.path)}
      onrename={renameEntry}
      onpincurrent={togglePinCurrent}
      onclearrecent={() => searchHistory.clear()}
    />
  {/if}

  {#if menuOpen}
    <!-- svelte-ignore a11y_interactive_supports_focus -->
    <div class="scope-menu" role="menu" aria-label="Search in" bind:this={menuEl} tabindex="-1" onkeydown={onMenuKeydown}>
      <div class="scope-menu-head">Search in</div>
      {#each menuItems as item, i (item.key)}
        {#if item.space && !menuItems[i - 1]?.space}<div class="scope-menu-head">Your spaces</div>{/if}
        <button type="button" role="menuitemradio" aria-checked={item.key === scope.key} onclick={() => pick(item)}>
          <Icon name={item.icon} />
          <span class="scope-menu-label">{item.label}</span>
          {#if item.key === scope.key}<Icon name="check" />{/if}
        </button>
      {/each}
      <div class="scope-menu-foot">or type <code>in:</code> followed by a list or space name</div>
    </div>
  {/if}
</div>

<style>
  .nav-search {
    position: relative;
    --q-caret: var(--on-accent);
  }
  .nav-search.is-focus {
    --q-caret: var(--ink);
  }
  .scope-btn {
    flex: none;
    border: 0;
    cursor: pointer;
  }
  .scope-btn :global(.r-icon) {
    margin-right: -2px;
  }

  /* The field: a transparent input over a mirror that draws the same text with tokens coloured. */
  .q-field {
    position: relative;
    flex: 1;
    min-width: 0;
    align-self: stretch;
  }
  .q-field input,
  .q-mirror {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    font: inherit;
    letter-spacing: normal;
  }
  .q-field input {
    background: transparent;
    color: transparent;
    caret-color: var(--q-caret);
    outline: 0;
  }
  .q-field input::selection {
    background: color-mix(in srgb, var(--accent) 24%, transparent);
    color: transparent;
  }
  .q-mirror {
    display: flex;
    align-items: center;
    overflow: hidden;
    color: inherit;
    pointer-events: none;
  }
  .q-mirror > span {
    white-space: pre;
  }
  .q-tok {
    border-radius: 3px;
    background: var(--nav-fill);
    color: var(--on-accent);
  }
  .is-focus .q-tok {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .q-tok.is-bad {
    text-decoration: underline wavy var(--danger);
    text-underline-offset: 3px;
  }

  /* Where to search: the lists, then your spaces. */
  .scope-menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 60;
    display: grid;
    min-width: 240px;
    max-height: min(70vh, 480px);
    overflow-y: auto;
    padding: 4px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-lg);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
    color: var(--ink);
    font-size: 13px;
  }
  .scope-menu-head {
    padding: 8px 10px 4px;
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .scope-menu button {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 30px;
    padding: 0 10px;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .scope-menu button :global(.r-icon) {
    flex: none;
    width: 14px;
    height: 14px;
    color: var(--ink-3);
  }
  .scope-menu button:hover,
  .scope-menu button:focus-visible {
    background: var(--subtle);
    outline: 0;
  }
  .scope-menu button[aria-checked="true"] {
    color: var(--accent);
    font-weight: 500;
  }
  .scope-menu button[aria-checked="true"] :global(.r-icon) {
    color: var(--accent);
  }
  .scope-menu-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .scope-menu-foot {
    margin-top: 4px;
    padding: 7px 10px 4px;
    border-top: 1px solid var(--line);
    color: var(--ink-3);
    font-size: 11.5px;
  }
  .scope-menu-foot code {
    color: var(--accent);
    font-family: var(--font-mono);
  }
</style>
