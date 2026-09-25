<script>
  // The inspector for a space: its identity, actions and details, and the People section.
  // Settings (and New space) open as an inspector mode via SpaceForm.
  import Icon from "../ui/Icon.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import PeopleSection from "./PeopleSection.svelte";
  import SpaceForm from "./SpaceForm.svelte";
  import { copyToClipboard } from "../../services/relicActions";
  import { navigate } from "../../utils/navigation";
  import { canAddRelics, canManagePeople, canConfigure, canSeePeople, roleLabel } from "./roles";
  import { session } from "../../stores/session";
  import { fullDate, compactNumber } from "../relics/format";

  let {
    space = null, // null with mode "create" for a new space
    mode = $bindable("view"), // "view" | "settings" | "create"
    confirm = null, // { what: "delete", n } opens Settings with the delete confirmation
    showOpen = false, // an Open button (on the Spaces list)
    onsaved, // (space) after create, settings or a transfer
    ondeleted, // (space)
    onclose, // for drawers
  } = $props();

  const link = $derived(space ? `${location.origin}/spaces/${space.id}` : "");
  const configurable = $derived(canConfigure(space, $session.isAdmin));

  // The Spaces list's Delete row action.
  let confirmDelete = $state(false);
  $effect(() => {
    if (!confirm || !configurable) return;
    confirm.n;
    mode = "settings";
    confirmDelete = true;
  });
  $effect(() => {
    if (mode !== "settings") confirmDelete = false;
  });
</script>

<aside class="r-inspector" aria-label="Space details">
  {#if mode === "create" || (space && mode === "settings")}
    {#key space?.id ?? "new"}
      <SpaceForm
        space={mode === "create" ? null : space}
        transferable={configurable}
        startDelete={confirmDelete}
        oncancel={() => (mode = "view")}
        onsaved={(saved) => {
          mode = "view";
          onsaved?.(saved);
        }}
        {ondeleted}
      />
    {/key}
  {:else if !space}
    <div class="ins-empty">
      <Icon name="layers" size={22} />
      <p>Select a space to see who’s in it.</p>
    </div>
  {:else}
    <div class="r-ins-id">
      <div class="r-ins-name">
        <span class="r-badge r-t-doc" title="Space"><Icon name="layers" size={11} /></span>
        <h2><a href="/spaces/{space.id}">{space.name}</a></h2>
        {#if configurable}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => (mode = "settings")} title="Space settings" aria-label="Space settings"><Icon name="sliders" /></button>
        {/if}
        {#if onclose}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} title="Hide inspector ( ] )" aria-label="Hide inspector"><Icon name="x" /></button>
        {/if}
      </div>
      <button class="r-ins-fid" title="Copy space ID" onclick={() => copyToClipboard(space.id, "Space ID copied")}>
        {space.id.match(/.{1,8}/g).join(" ")}<Icon name="copy" />
      </button>

      <div class="r-ins-actions">
        {#if showOpen}
          <a class="r-btn r-btn-primary r-btn-md" href="/spaces/{space.id}"><Icon name="layers" />Open</a>
        {/if}
        <button class={showOpen ? "r-btn r-btn-secondary r-btn-md" : "r-btn r-btn-primary r-btn-md"} onclick={() => copyToClipboard(link, "Space link copied")}>
          <Icon name="link" />Copy link
        </button>
        {#if canAddRelics(space)}
          <button class="r-btn r-btn-secondary r-btn-md" onclick={() => navigate(`/?space=${space.id}`)}><Icon name="plus" />New relic here</button>
        {/if}
      </div>

      <div class="r-ins-meta">
        <span class="r-pill" class:r-pill-accent={space.visibility === "public"}>
          <Icon name={space.visibility === "public" ? "globe" : "lock"} />{space.visibility === "public" ? "Public" : "Private"}
        </span>
        {#if space.role}<span class="r-pill">{roleLabel(space.role)}</span>{/if}
        <span>{compactNumber(space.relic_count)} {space.relic_count === 1 ? "relic" : "relics"}</span>
      </div>
    </div>

    <div class="r-ins-body">
      <InsSection id="space-details" title="Details" defaultOpen>
        <dl class="r-kv">
          <dt>Visibility</dt><dd>{space.visibility === "public" ? "Public: anyone can view" : "Private: people you add"}</dd>
          <dt>Your role</dt><dd>{space.role ? roleLabel(space.role) : "None (public space)"}</dd>
          <dt>Relics</dt><dd>{(space.relic_count ?? 0).toLocaleString("en-US")}</dd>
          <dt>Created</dt><dd>{fullDate(space.created_at)}</dd>
        </dl>
      </InsSection>

      {#if canSeePeople(space)}
        {#key space.id}
          <InsSection id="space-people" title="People" aside={canManagePeople(space) ? "add · remove" : "view"} defaultOpen>
            <PeopleSection spaceId={space.id} manage={canManagePeople(space)} />
          </InsSection>
        {/key}
      {/if}
    </div>
  {/if}
</aside>

<style>
  .r-inspector {
    height: 100%;
  }
  .r-ins-name h2 a {
    color: inherit;
    text-decoration: none;
    overflow-wrap: anywhere;
  }
  .r-ins-name h2 a:hover {
    text-decoration: underline;
    text-decoration-color: var(--line-2);
  }
  .r-ins-name .r-badge {
    min-width: 24px;
  }
  .r-ins-fid {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .ins-empty {
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    margin: auto;
    padding: var(--space-5);
    color: var(--ink-3);
    text-align: center;
  }
  .ins-empty p {
    margin: 0;
  }
</style>
