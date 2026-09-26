// Files dropped on a list page, handed to the New relic page's upload mode (every drop lands
// there). Holds { files: [{ file, path }], spaceId } until the page takes it.
import { writable, get } from "svelte/store";
import { navigate } from "../../utils/navigation";

const pending = writable(null);

/** Send dropped files to the upload page, optionally into a space. */
export function uploadFiles(files, spaceId = null) {
  pending.set({ files, spaceId });
  navigate(spaceId ? `/?space=${spaceId}&upload=1` : "/?upload=1");
}

/** Take the waiting files (once). */
export function takePendingUpload() {
  const value = get(pending);
  pending.set(null);
  return value;
}
