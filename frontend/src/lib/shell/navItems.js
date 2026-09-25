// The app's sections, shared by the navbar and the phone tab bar.
export const NAV_ITEMS = [
  { section: "recent", label: "Recent", icon: "clock", path: "/recent" },
  { section: "spaces", label: "Spaces", icon: "layers", path: "/spaces", alsoActive: ["space-view"] },
  { section: "my-relics", label: "My relics", icon: "user", path: "/my-relics" },
  { section: "my-bookmarks", label: "Bookmarks", icon: "bookmark", path: "/my-bookmarks" },
];

export const ADMIN_ITEM = { section: "admin", label: "Admin", icon: "shield", path: "/admin" };

export const isActive = (item, section) =>
  item.section === section || (item.alsoActive?.includes(section) ?? false);
