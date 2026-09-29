<script>
  // What Relic is, what it does, how to reach it from a terminal, and which build this is.
  import Icon from "../lib/ui/Icon.svelte";
  import RelicMark from "../lib/ui/RelicMark.svelte";
  import { copyToClipboard } from "../services/relicActions";
  import { appVersion, loadVersion, REPO_URL } from "../lib/shell/appVersion";

  loadVersion();

  const FEATURES = [
    { icon: "code", title: "Preview anything", text: "Code with syntax highlighting, JSON, YAML, TOML and XML as trees, archives you can browse, PDFs, spreadsheets, Markdown, images and Excalidraw diagrams." },
    { icon: "fork", title: "Forks and diffs", text: "Build on someone else’s relic as your own copy, trace where it came from, and compare it with the original." },
    { icon: "layers", title: "Spaces", text: "Collections with their own people and access, for a team, a project or a topic." },
    { icon: "bookmark", title: "Tags and bookmarks", text: "Label what you share, bookmark what you need, and search across all of it." },
    { icon: "lock", title: "Sharing on your terms", text: "Public, private or restricted, an optional password, and an expiry from ten minutes to never." },
    { icon: "msg", title: "Comments", text: "Discuss a relic where it lives, down to a single line of code." },
  ];

  const origin = typeof location === "undefined" ? "" : location.origin;
  const install = `curl -sSL ${origin}/install.sh | bash`;

  // "1.4.0" links to its release, a commit hash to its commit.
  const versionUrl = $derived.by(() => {
    const v = $appVersion ?? "";
    if (/^\d+\.\d+/.test(v)) return `${REPO_URL}/releases/tag/v${v}`;
    if (/^[0-9a-f]{7,40}$/.test(v)) return `${REPO_URL}/commit/${v}`;
    return null;
  });
</script>

<div class="about">
  <section class="hero">
    <span class="mark"><RelicMark size={40} /></span>
    <h1>Relic</h1>
    <p class="lead">Self-hosted artifact storage for developers.</p>
    <p class="sub">Paste it, share it, preview it: code, images, archives, PDFs, diagrams, anything.</p>
    <div class="hero-actions">
      <a class="r-btn r-btn-primary r-btn-md" href={REPO_URL} target="_blank" rel="noopener"><Icon name="github" />Source on GitHub</a>
      <a class="r-btn r-btn-secondary r-btn-md" href="{REPO_URL}/releases" target="_blank" rel="noopener"><Icon name="download" />Releases</a>
      <a class="r-btn r-btn-secondary r-btn-md" href="/docs" target="_blank" rel="noopener"><Icon name="braces" />API docs</a>
    </div>
  </section>

  <section class="features" aria-label="What Relic does">
    {#each FEATURES as f (f.title)}
      <article class="feature">
        <span class="feature-icon"><Icon name={f.icon} size={18} /></span>
        <h2>{f.title}</h2>
        <p>{f.text}</p>
      </article>
    {/each}
  </section>

  <section class="cli" aria-label="Command line">
    <div>
      <h2><Icon name="terminal" />From your terminal</h2>
      <p>Pipe output straight in, upload files, fork and manage spaces with the Relic CLI, installed from this server.</p>
    </div>
    <div class="cli-line">
      <code>{install}</code>
      <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => copyToClipboard(install, "Install command copied")} title="Copy" aria-label="Copy the install command"><Icon name="copy" /></button>
    </div>
  </section>

  <footer class="facts">
    <div>
      <span>Version</span>
      {#if versionUrl}
        <a class="r-link r-mono" href={versionUrl} target="_blank" rel="noopener">{$appVersion}</a>
      {:else}
        <b class="r-mono">{$appVersion ?? "…"}</b>
      {/if}
    </div>
    <div>
      <span>Author</span>
      <a class="r-link" href="https://github.com/ovidiuvio" target="_blank" rel="noopener">Ovidiu Ionescu</a>
    </div>
    <div>
      <span>License</span>
      <b>MIT</b>
    </div>
  </footer>
</div>

<style>
  .about {
    display: grid;
    gap: 28px;
    width: 100%;
    max-width: 960px;
    margin: 0 auto;
    padding: 28px var(--space-4) 40px;
  }

  .hero {
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    padding: 28px 0 var(--space-2);
    text-align: center;
  }
  .mark {
    display: grid;
    place-items: center;
    width: 72px;
    height: 72px;
    margin-bottom: var(--space-2);
    border-radius: var(--radius-lg);
    background: var(--accent-soft);
    color: var(--accent);
  }
  .hero h1 {
    margin: 0;
    font-size: 34px;
    font-weight: 500;
    letter-spacing: -0.02em;
  }
  .lead {
    margin: 0;
    color: var(--ink);
    font-size: 16px;
  }
  .sub {
    max-width: 480px;
    margin: 0;
    color: var(--ink-3);
    line-height: 1.5;
  }
  .hero-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-2);
    margin-top: var(--space-3);
  }

  .features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: var(--space-3);
  }
  .feature {
    padding: var(--space-4);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    background: var(--surface);
  }
  .feature-icon {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    margin-bottom: var(--space-3);
    border-radius: var(--radius-md);
    background: var(--accent-soft);
    color: var(--accent);
  }
  .feature h2,
  .cli h2 {
    margin: 0 0 var(--space-1);
    font-size: 14px;
    font-weight: 600;
  }
  .feature p,
  .cli p {
    margin: 0;
    color: var(--ink-2);
    font-size: 13px;
    line-height: 1.5;
  }

  .cli {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    background: var(--inset);
  }
  .cli h2 {
    display: flex;
    align-items: center;
    gap: var(--space-1\.5);
  }
  .cli-line {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-2) var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--night);
    color: var(--night-ink);
  }
  .cli-line code {
    flex: 1;
    min-width: 0;
    overflow-x: auto;
    font: 12.5px var(--font-mono);
    white-space: nowrap;
  }
  .cli-line .r-btn {
    flex: none;
    color: var(--night-ink);
  }
  .cli-line .r-btn:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .facts {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-2) 28px;
    padding-top: var(--space-4);
    border-top: 1px solid var(--line);
    font-size: 12.5px;
  }
  .facts div {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .facts span {
    color: var(--ink-3);
  }
  .facts b {
    font-weight: 500;
  }
</style>
