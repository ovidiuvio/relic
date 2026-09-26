export const IGNORED_NAMES = [
  ".git",
  "node_modules",
  ".DS_Store",
  "__pycache__",
  ".idea",
  ".vscode",
  "dist",
  "build",
  "coverage",
  "venv",
  ".env",
];

/**
 * Recursive function to traverse file system entries from a DataTransferItem or FileSystemEntry
 * @param {FileSystemEntry} item 
 * @param {string} path 
 * @returns {Promise<Array<{file: File, path: string}>>}
 */
export async function traverseFileTree(item, path = "") {
  if (IGNORED_NAMES.includes(item.name)) {
    return [];
  }

  if (item.isFile) {
    return new Promise((resolve) => {
      item.file((file) => {
        // Double check file name for ignore list (though item.name caught dirs)
        if (IGNORED_NAMES.includes(file.name)) {
          resolve([]);
        } else {
          resolve([{ file, path: path + file.name }]);
        }
      });
    });
  } else if (item.isDirectory) {
    const dirReader = item.createReader();
    const entries = await new Promise((resolve) => {
      dirReader.readEntries((entries) => resolve(entries));
    });

    let files = [];
    for (const entry of entries) {
      const children = await traverseFileTree(entry, path + item.name + "/");
      files = [...files, ...children];
    }
    return files;
  }
  return [];
}

/**
 * Normalizes DataTransfer items into a list of file objects with paths
 * @param {DataTransfer} dt 
 * @returns {Promise<Array<{file: File, path: string}>>}
 */
export async function getFilesFromDrop(dt) {
  if (!dt) return [];

  if (dt.items && dt.items.length > 0) {
    const entriesToProcess = [];
    for (let i = 0; i < dt.items.length; i++) {
      const item = dt.items[i];
      // Entries let folders be walked; when the browser gives none for a file (some drag
      // sources), fall back to the plain file.
      const entry = item.webkitGetAsEntry?.();
      if (entry) {
        entriesToProcess.push({ entry });
      } else if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) entriesToProcess.push({ file });
      }
    }

    let allFiles = [];
    for (const { entry, file } of entriesToProcess) {
      if (entry) {
        const files = await traverseFileTree(entry);
        allFiles = [...allFiles, ...files];
      } else if (file) {
        allFiles.push({ file, path: file.name });
      }
    }
    return allFiles;
  } else {
    // Fallback for older browsers
    const files = dt.files;
    if (files && files.length > 0) {
      return Array.from(files).map(file => ({ file, path: file.name }));
    }
  }
  return [];
}
