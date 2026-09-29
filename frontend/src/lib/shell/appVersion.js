// The server's version, fetched once and shared by the navbar and the About page, and where
// the project lives.
import { writable } from "svelte/store";
import { getVersion } from "../../services/api";

export const REPO_URL = "https://github.com/ovidiuvio/relic";

export const appVersion = writable(null);

let requested = false;

export function loadVersion() {
  if (requested) return;
  requested = true;
  getVersion()
    .then((r) => appVersion.set(r.data?.version ?? null))
    .catch(() => (requested = false));
}
