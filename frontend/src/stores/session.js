// Who is using Relic: display name, public ID, admin status and the running version.
// Loaded once at start-up by App.svelte; the navbar and profile read it from here.
import { writable } from "svelte/store";
import { registerUser, checkAdminStatus, getVersion, updateUserName } from "../services/api";
import { userPublicId } from "./userStore";

export const session = writable({
  name: "",
  publicId: "",
  isAdmin: false,
  version: "",
});

export async function loadSession() {
  const [user, admin, version] = await Promise.allSettled([
    registerUser(),
    checkAdminStatus(),
    getVersion(),
  ]);

  const next = { name: "", publicId: "", isAdmin: false, version: "unknown" };
  if (user.status === "fulfilled" && user.value) {
    next.name = user.value.name || "";
    next.publicId = user.value.public_id || "";
  } else if (user.status === "rejected") {
    console.error("[session] Failed to fetch user info", user.reason);
  }
  if (admin.status === "fulfilled") next.isAdmin = !!admin.value.data.is_admin;
  if (version.status === "fulfilled") next.version = version.value.data.version;

  if (next.publicId) userPublicId.set(next.publicId);
  session.set(next);
}

export async function saveDisplayName(name) {
  await updateUserName(name);
  session.update((s) => ({ ...s, name }));
}

/** Two-letter initials for the avatar; "?" for someone without a display name. */
export function initials(name) {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  return (parts[0][0] + (parts[1]?.[0] ?? parts[0][1] ?? "")).toUpperCase();
}
