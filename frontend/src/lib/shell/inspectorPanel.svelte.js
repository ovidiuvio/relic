// Whether the inspector is showing. From 1280px it docks beside the list and the choice is
// remembered (] toggles it); below that it opens as a drawer over the list when needed.
const KEY = "relic_inspector_open";

function remembered() {
  try {
    return localStorage.getItem(KEY) !== "false";
  } catch {
    return true;
  }
}

export class InspectorPanel {
  docked = $state(remembered());
  drawer = $state(false);

  /** Is the inspector on screen? `dock` is the layout's dock tier; drawers need something to show. */
  isOpen(dock, hasContent = true) {
    return dock ? this.docked : this.drawer && hasContent;
  }

  toggle(dock) {
    if (!dock) {
      this.drawer = !this.drawer;
      return;
    }
    this.docked = !this.docked;
    try {
      localStorage.setItem(KEY, String(this.docked));
    } catch {
      // Not remembered without storage; the toggle still works.
    }
  }

  /** Make sure it's showing (a row was selected, or a row action needs it). */
  show(dock) {
    if (dock) this.docked = true;
    else this.drawer = true;
  }

  hide() {
    this.drawer = false;
  }
}
