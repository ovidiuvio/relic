// What your role in a space lets you do, matching the API's checks. Relic (system) admins come
// back from the API with the role "admin", like space admins, but can do more: pass `sysAdmin`.
export const ROLES = {
  owner: { label: "Owner", hint: "Full control, including ownership" },
  admin: { label: "Admin", hint: "Manage people and settings" },
  editor: { label: "Editor", hint: "Add and remove relics" },
  viewer: { label: "Viewer", hint: "See the space and its relics" },
};

/** Roles you can give someone when adding them. */
export const GRANTABLE = ["viewer", "editor", "admin"];

/** Add and remove relics; see who's in the space. */
export const canAddRelics = (space) => ["owner", "admin", "editor"].includes(space?.role);
export const canSeePeople = canAddRelics;
/** Add and remove people. */
export const canManagePeople = (space) => ["owner", "admin"].includes(space?.role);
/** Rename, change visibility, transfer ownership, delete: the owner or a Relic admin only. */
export const canConfigure = (space, sysAdmin = false) => space?.role === "owner" || (sysAdmin && !!space);
export const roleLabel = (role) => ROLES[role]?.label ?? "Public";
