// Admin-wide state shared by the side navigation and the sections: the instance counts and
// the latest backup (refreshed after anything that changes them), and the owner a relic
// list is filtered to. The owner filter stays in memory: a user's ID is their secret key,
// so it never goes in the address bar.
import { writable } from "svelte/store";
import { getAdminStats, getAdminBackups } from "../../services/api";

export const adminStats = writable(null);
export const lastBackup = writable(undefined); // undefined while loading, null when there are none

export async function refreshAdminStats() {
  try {
    const { data } = await getAdminStats();
    adminStats.set(data);
  } catch (error) {
    console.error("[admin] Failed to load stats", error);
  }
}

export async function refreshLastBackup() {
  try {
    const { data } = await getAdminBackups(1, 0);
    lastBackup.set(data.backups?.[0] ?? null);
  } catch (error) {
    console.error("[admin] Failed to load backups", error);
    lastBackup.set(null);
  }
}

/** { id, publicId, label } of the user the Relics section shows, or null for everyone. */
export const relicOwner = writable(null);

/** When a backup was taken. Startup and shutdown backups have no time in their file name (the
 *  API reports noon for them), so the storage's last-modified time is the real one. */
export const backupTime = (backup) => backup?.last_modified || backup?.timestamp;
