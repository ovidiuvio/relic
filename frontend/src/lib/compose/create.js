// Creating relics from the New relic page: from the editor, or from files (one relic each, or
// zipped into one). Same rules as the old form: types come from the chosen language or from
// each file's extension, and multi-file zips keep folder paths.
import { createRelic } from "../../services/api";
import { getContentType, getFileExtension, getSyntaxFromExtension, getFileTypeDefinition } from "../../services/typeUtils";

const expires = (expiry) => (expiry && expiry !== "never" ? expiry : undefined);
const tagList = (tags) => (tags?.length ? tags : undefined);

/** Create one relic from editor text. Returns the created relic. */
export async function createFromText({ content, title, syntax, visibility, expiry, tags, spaceId }) {
  const contentType = syntax !== "auto" ? getContentType(syntax) : "text/plain";
  const extension = syntax !== "auto" ? getFileExtension(syntax) : "txt";
  const file = new File([content], title || `relic.${extension}`, { type: contentType });
  const { data } = await createRelic({
    file,
    name: title || undefined,
    content_type: contentType,
    language_hint: syntax !== "auto" ? syntax : undefined,
    access_level: visibility,
    expires_in: expires(expiry),
    tags: tagList(tags),
    space_id: spaceId || undefined,
  });
  return data;
}

// Text-like files get the canonical type for their extension; binaries keep the browser's.
const TEXTLIKE = ["code", "text", "markdown", "html", "csv", "json", "xml"];
function typeFor(file) {
  const ext = file.name.split(".").pop()?.toLowerCase();
  const syntax = ext ? getSyntaxFromExtension(ext) : null;
  if (!syntax) return { contentType: file.type || undefined, hint: undefined };
  const canonical = getContentType(syntax);
  const category = getFileTypeDefinition(canonical).category;
  return {
    contentType: TEXTLIKE.includes(category) || !file.type ? canonical : file.type,
    hint: syntax,
  };
}

/** Upload one file as its own relic. */
export async function createFromFile(file, { name, visibility, expiry, tags, spaceId }) {
  const { contentType, hint } = typeFor(file);
  const { data } = await createRelic({
    file,
    name: name || file.name,
    content_type: contentType,
    language_hint: hint,
    access_level: visibility,
    expires_in: expires(expiry),
    tags: tagList(tags),
    space_id: spaceId || undefined,
  });
  return data;
}

/** Zip several files (keeping their folder paths) into one archive relic. */
export async function createZip(entries, { title, visibility, expiry, tags, spaceId }) {
  const { default: JSZip } = await import("jszip");
  const zip = new JSZip();
  for (const { file, path } of entries) zip.file(path || file.name, file);
  const blob = await zip.generateAsync({ type: "blob", compression: "DEFLATE" });
  const zipName = title ? `${title}.zip` : `${entries[0].file.name.split(".")[0]}_archive.zip`;
  const { data } = await createRelic({
    file: new File([blob], zipName, { type: "application/zip" }),
    name: title || zipName,
    content_type: "application/zip",
    language_hint: "archive",
    access_level: visibility,
    expires_in: expires(expiry),
    tags: tagList(tags),
    space_id: spaceId || undefined,
  });
  return data;
}
