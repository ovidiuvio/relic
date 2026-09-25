// Layout tiers for the Workbench frame. Widths match the media queries in app.css,
// which set --rail-w and --inspector-width; components read the same tiers from here.
import { readable } from "svelte/store";

export const TIERS = {
  desktop: 768, // tabs in the navbar, bottom tab bar gone
  dock: 1280, // the inspector docks beside the list instead of opening over it
  rail: 1600, // sections move from the navbar into the sidebar
};

function measure() {
  const w = window.innerWidth;
  return {
    phone: w < TIERS.desktop,
    dock: w >= TIERS.dock,
    rail: w >= TIERS.rail,
  };
}

export const layout = readable(measure(), (set) => {
  const queries = Object.values(TIERS).map((w) => window.matchMedia(`(min-width: ${w}px)`));
  const update = () => set(measure());
  queries.forEach((q) => q.addEventListener("change", update));
  return () => queries.forEach((q) => q.removeEventListener("change", update));
});
