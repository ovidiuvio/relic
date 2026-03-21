package upload

import (
	"mime"
	"net/http"
	"path/filepath"
	"strings"
)

// FileType represents a file type definition matching the frontend
type FileType struct {
	Syntax     string   // Language/syntax identifier (e.g., "python", "javascript")
	Label      string   // Human-readable label (e.g., "Python", "JavaScript")
	MIME       string   // MIME type (e.g., "text/x-python")
	Extensions []string // File extensions without leading dot (e.g., "py", "pyw")
	Category   string   // Category (e.g., "code", "text", "image")
}

// fileTypes is the comprehensive list of file types matching the frontend
var fileTypes = []FileType{
	// ============================================
	// GENERAL PURPOSE PROGRAMMING LANGUAGES
	// ============================================
	{Syntax: "javascript", Label: "JavaScript", MIME: "application/javascript", Extensions: []string{"js", "jsx", "mjs", "cjs"}, Category: "code"},
	{Syntax: "typescript", Label: "TypeScript", MIME: "application/x-typescript", Extensions: []string{"ts", "tsx"}, Category: "code"},
	{Syntax: "python", Label: "Python", MIME: "text/x-python", Extensions: []string{"py", "pyw", "pyx", "pyi", "pyd", "pyc"}, Category: "code"},
	{Syntax: "java", Label: "Java", MIME: "text/x-java-source", Extensions: []string{"java", "class", "jar"}, Category: "code"},
	{Syntax: "csharp", Label: "C#", MIME: "text/x-csharp", Extensions: []string{"cs", "csx"}, Category: "code"},
	{Syntax: "cpp", Label: "C++", MIME: "text/x-c++", Extensions: []string{"cpp", "cc", "cxx", "c++", "hpp", "hh", "hxx", "h++"}, Category: "code"},
	{Syntax: "c", Label: "C", MIME: "text/x-c", Extensions: []string{"c", "h"}, Category: "code"},
	{Syntax: "objective-c", Label: "Objective-C", MIME: "text/x-objectivec", Extensions: []string{"m", "mm"}, Category: "code"},
	{Syntax: "swift", Label: "Swift", MIME: "text/x-swift", Extensions: []string{"swift"}, Category: "code"},
	{Syntax: "kotlin", Label: "Kotlin", MIME: "text/x-kotlin", Extensions: []string{"kt", "kts", "ktm"}, Category: "code"},

	// ============================================
	// SYSTEMS PROGRAMMING LANGUAGES
	// ============================================
	{Syntax: "rust", Label: "Rust", MIME: "text/x-rust", Extensions: []string{"rs"}, Category: "code"},
	{Syntax: "go", Label: "Go", MIME: "text/x-go", Extensions: []string{"go"}, Category: "code"},
	{Syntax: "zig", Label: "Zig", MIME: "text/x-zig", Extensions: []string{"zig"}, Category: "code"},
	{Syntax: "d", Label: "D", MIME: "text/x-d", Extensions: []string{"d", "di"}, Category: "code"},
	{Syntax: "nim", Label: "Nim", MIME: "text/x-nim", Extensions: []string{"nim", "nims", "nimble"}, Category: "code"},
	{Syntax: "v", Label: "V", MIME: "text/x-v", Extensions: []string{"v", "vsh"}, Category: "code"},

	// ============================================
	// FUNCTIONAL PROGRAMMING LANGUAGES
	// ============================================
	{Syntax: "haskell", Label: "Haskell", MIME: "text/x-haskell", Extensions: []string{"hs", "lhs"}, Category: "code"},
	{Syntax: "ocaml", Label: "OCaml", MIME: "text/x-ocaml", Extensions: []string{"ml", "mli", "mll", "mly"}, Category: "code"},
	{Syntax: "fsharp", Label: "F#", MIME: "text/x-fsharp", Extensions: []string{"fs", "fsi", "fsx", "fsscript"}, Category: "code"},
	{Syntax: "scala", Label: "Scala", MIME: "text/x-scala", Extensions: []string{"scala", "sc"}, Category: "code"},
	{Syntax: "clojure", Label: "Clojure", MIME: "text/x-clojure", Extensions: []string{"clj", "cljs", "cljc", "edn"}, Category: "code"},
	{Syntax: "elixir", Label: "Elixir", MIME: "text/x-elixir", Extensions: []string{"ex", "exs"}, Category: "code"},
	{Syntax: "erlang", Label: "Erlang", MIME: "text/x-erlang", Extensions: []string{"erl", "hrl"}, Category: "code"},
	{Syntax: "scheme", Label: "Scheme", MIME: "text/x-scheme", Extensions: []string{"scm", "ss", "sld"}, Category: "code"},
	{Syntax: "racket", Label: "Racket", MIME: "text/x-racket", Extensions: []string{"rkt", "rktl", "rktd"}, Category: "code"},
	{Syntax: "lisp", Label: "Lisp", MIME: "text/x-lisp", Extensions: []string{"lisp", "lsp", "l", "cl", "fasl"}, Category: "code"},

	// ============================================
	// WEB DEVELOPMENT
	// ============================================
	{Syntax: "html", Label: "HTML", MIME: "text/html", Extensions: []string{"html", "htm", "xhtml"}, Category: "html"},
	{Syntax: "css", Label: "CSS", MIME: "text/css", Extensions: []string{"css"}, Category: "code"},
	{Syntax: "scss", Label: "SCSS", MIME: "text/x-scss", Extensions: []string{"scss"}, Category: "code"},
	{Syntax: "sass", Label: "Sass", MIME: "text/x-sass", Extensions: []string{"sass"}, Category: "code"},
	{Syntax: "less", Label: "Less", MIME: "text/x-less", Extensions: []string{"less"}, Category: "code"},
	{Syntax: "php", Label: "PHP", MIME: "application/x-php", Extensions: []string{"php", "phtml", "php3", "php4", "php5", "phps"}, Category: "code"},
	{Syntax: "ruby", Label: "Ruby", MIME: "application/x-ruby", Extensions: []string{"rb", "rbw", "rake", "gemspec"}, Category: "code"},
	{Syntax: "vue", Label: "Vue", MIME: "text/x-vue", Extensions: []string{"vue"}, Category: "code"},
	{Syntax: "svelte", Label: "Svelte", MIME: "text/x-svelte", Extensions: []string{"svelte"}, Category: "code"},
	{Syntax: "jsx", Label: "JSX", MIME: "text/jsx", Extensions: []string{"jsx"}, Category: "code"},

	// ============================================
	// SCRIPTING LANGUAGES
	// ============================================
	{Syntax: "bash", Label: "Bash", MIME: "text/x-shellscript", Extensions: []string{"sh", "bash"}, Category: "code"},
	{Syntax: "shell", Label: "Shell", MIME: "application/x-sh", Extensions: []string{"zsh", "fish", "ksh", "csh", "tcsh"}, Category: "code"},
	{Syntax: "powershell", Label: "PowerShell", MIME: "application/x-powershell", Extensions: []string{"ps1", "psm1", "psd1"}, Category: "code"},
	{Syntax: "perl", Label: "Perl", MIME: "text/x-perl", Extensions: []string{"pl", "pm", "perl"}, Category: "code"},
	{Syntax: "lua", Label: "Lua", MIME: "text/x-lua", Extensions: []string{"lua"}, Category: "code"},
	{Syntax: "tcl", Label: "Tcl", MIME: "text/x-tcl", Extensions: []string{"tcl"}, Category: "code"},
	{Syntax: "awk", Label: "AWK", MIME: "text/x-awk", Extensions: []string{"awk"}, Category: "code"},
	{Syntax: "sed", Label: "Sed", MIME: "text/x-sed", Extensions: []string{"sed"}, Category: "code"},

	// ============================================
	// DATA & CONFIGURATION
	// ============================================
	{Syntax: "json", Label: "JSON", MIME: "application/json", Extensions: []string{"json", "jsonc", "json5"}, Category: "code"},
	{Syntax: "relic-index", Label: "Relic Index", MIME: "application/x-relic-index", Extensions: []string{"rix"}, Category: "relicindex"},
	{Syntax: "yaml", Label: "YAML", MIME: "application/x-yaml", Extensions: []string{"yaml", "yml"}, Category: "code"},
	{Syntax: "xml", Label: "XML", MIME: "application/xml", Extensions: []string{"xml", "xsl", "xslt", "xsd", "dtd"}, Category: "code"},
	{Syntax: "toml", Label: "TOML", MIME: "application/toml", Extensions: []string{"toml"}, Category: "code"},
	{Syntax: "ini", Label: "INI", MIME: "text/x-ini", Extensions: []string{"ini", "cfg", "conf", "config"}, Category: "code"},
	{Syntax: "properties", Label: "Properties", MIME: "text/x-properties", Extensions: []string{"properties"}, Category: "code"},
	{Syntax: "csv", Label: "CSV", MIME: "text/csv", Extensions: []string{"csv"}, Category: "csv"},
	{Syntax: "tsv", Label: "TSV", MIME: "text/tab-separated-values", Extensions: []string{"tsv"}, Category: "csv"},
	{Syntax: "env", Label: "Environment", MIME: "application/x-env", Extensions: []string{"env"}, Category: "code"},

	// ============================================
	// MARKUP & DOCUMENTATION
	// ============================================
	{Syntax: "markdown", Label: "Markdown", MIME: "text/markdown", Extensions: []string{"md", "markdown", "mdown", "mkd"}, Category: "markdown"},
	{Syntax: "restructuredtext", Label: "reStructuredText", MIME: "text/x-rst", Extensions: []string{"rst", "rest"}, Category: "markdown"},
	{Syntax: "asciidoc", Label: "AsciiDoc", MIME: "text/x-asciidoc", Extensions: []string{"adoc", "asciidoc", "asc"}, Category: "markdown"},
	{Syntax: "org", Label: "Org Mode", MIME: "text/x-org", Extensions: []string{"org"}, Category: "markdown"},
	{Syntax: "latex", Label: "LaTeX", MIME: "text/x-latex", Extensions: []string{"tex", "latex", "sty", "cls"}, Category: "code"},
	{Syntax: "bibtex", Label: "BibTeX", MIME: "text/x-bibtex", Extensions: []string{"bib", "bibtex"}, Category: "code"},

	// ============================================
	// QUERY LANGUAGES
	// ============================================
	{Syntax: "sql", Label: "SQL", MIME: "application/sql", Extensions: []string{"sql", "ddl", "dml"}, Category: "code"},
	{Syntax: "mysql", Label: "MySQL", MIME: "text/x-mysql", Extensions: []string{"mysql"}, Category: "code"},
	{Syntax: "pgsql", Label: "PostgreSQL", MIME: "text/x-pgsql", Extensions: []string{"pgsql", "postgres"}, Category: "code"},
	{Syntax: "plsql", Label: "PL/SQL", MIME: "text/x-plsql", Extensions: []string{"plsql", "pls"}, Category: "code"},
	{Syntax: "graphql", Label: "GraphQL", MIME: "application/graphql", Extensions: []string{"graphql", "gql"}, Category: "code"},
	{Syntax: "sparql", Label: "SPARQL", MIME: "application/sparql-query", Extensions: []string{"sparql", "rq"}, Category: "code"},

	// ============================================
	// TEMPLATE LANGUAGES
	// ============================================
	{Syntax: "handlebars", Label: "Handlebars", MIME: "text/x-handlebars-template", Extensions: []string{"hbs", "handlebars"}, Category: "code"},
	{Syntax: "mustache", Label: "Mustache", MIME: "text/x-mustache", Extensions: []string{"mustache"}, Category: "code"},
	{Syntax: "jinja", Label: "Jinja", MIME: "text/x-jinja", Extensions: []string{"jinja", "jinja2", "j2"}, Category: "code"},
	{Syntax: "ejs", Label: "EJS", MIME: "text/x-ejs", Extensions: []string{"ejs"}, Category: "code"},
	{Syntax: "pug", Label: "Pug", MIME: "text/x-pug", Extensions: []string{"pug", "jade"}, Category: "code"},
	{Syntax: "twig", Label: "Twig", MIME: "text/x-twig", Extensions: []string{"twig"}, Category: "code"},
	{Syntax: "liquid", Label: "Liquid", MIME: "text/x-liquid", Extensions: []string{"liquid"}, Category: "code"},
	{Syntax: "razor", Label: "Razor", MIME: "text/x-cshtml", Extensions: []string{"cshtml", "razor"}, Category: "code"},

	// ============================================
	// DOMAIN-SPECIFIC LANGUAGES
	// ============================================
	{Syntax: "dockerfile", Label: "Dockerfile", MIME: "text/x-dockerfile", Extensions: []string{"dockerfile"}, Category: "code"},
	{Syntax: "makefile", Label: "Makefile", MIME: "text/x-makefile", Extensions: []string{"makefile", "mk", "mak"}, Category: "code"},
	{Syntax: "cmake", Label: "CMake", MIME: "text/x-cmake", Extensions: []string{"cmake", "cmake.in"}, Category: "code"},
	{Syntax: "gradle", Label: "Gradle", MIME: "text/x-gradle", Extensions: []string{"gradle"}, Category: "code"},
	{Syntax: "groovy", Label: "Groovy", MIME: "text/x-groovy", Extensions: []string{"groovy", "gvy", "gy", "gsh"}, Category: "code"},
	{Syntax: "terraform", Label: "Terraform", MIME: "text/x-terraform", Extensions: []string{"tf", "tfvars", "hcl"}, Category: "code"},
	{Syntax: "nginx", Label: "Nginx", MIME: "text/x-nginx-conf", Extensions: []string{"nginx", "nginxconf"}, Category: "code"},
	{Syntax: "apache", Label: "Apache", MIME: "text/x-apache-conf", Extensions: []string{"htaccess", "apache", "apacheconf"}, Category: "code"},
	{Syntax: "protobuf", Label: "Protocol Buffers", MIME: "text/x-protobuf", Extensions: []string{"proto"}, Category: "code"},
	{Syntax: "thrift", Label: "Thrift", MIME: "text/x-thrift", Extensions: []string{"thrift"}, Category: "code"},

	// ============================================
	// SCIENTIFIC & MATHEMATICAL
	// ============================================
	{Syntax: "r", Label: "R", MIME: "text/x-r", Extensions: []string{"r", "R"}, Category: "code"},
	{Syntax: "julia", Label: "Julia", MIME: "text/x-julia", Extensions: []string{"jl"}, Category: "code"},
	{Syntax: "matlab", Label: "MATLAB", MIME: "text/x-matlab", Extensions: []string{"mat"}, Category: "code"},
	{Syntax: "octave", Label: "Octave", MIME: "text/x-octave", Extensions: []string{}, Category: "code"},
	{Syntax: "mathematica", Label: "Mathematica", MIME: "text/x-mathematica", Extensions: []string{"nb", "wl", "wls"}, Category: "code"},
	{Syntax: "sage", Label: "Sage", MIME: "text/x-sage", Extensions: []string{"sage"}, Category: "code"},
	{Syntax: "fortran", Label: "Fortran", MIME: "text/x-fortran", Extensions: []string{"f", "for", "f90", "f95", "f03", "f08"}, Category: "code"},

	// ============================================
	// ASSEMBLY & LOW-LEVEL
	// ============================================
	{Syntax: "asm", Label: "Assembly", MIME: "text/x-asm", Extensions: []string{"asm", "s", "nasm"}, Category: "code"},
	{Syntax: "llvm", Label: "LLVM IR", MIME: "text/x-llvm", Extensions: []string{"ll"}, Category: "code"},
	{Syntax: "wasm", Label: "WebAssembly", MIME: "application/wasm", Extensions: []string{"wasm", "wat"}, Category: "code"},

	// ============================================
	// MOBILE DEVELOPMENT
	// ============================================
	{Syntax: "dart", Label: "Dart", MIME: "text/x-dart", Extensions: []string{"dart"}, Category: "code"},

	// ============================================
	// GAME DEVELOPMENT
	// ============================================
	{Syntax: "gdscript", Label: "GDScript", MIME: "text/x-gdscript", Extensions: []string{"gd"}, Category: "code"},
	{Syntax: "hlsl", Label: "HLSL", MIME: "text/x-hlsl", Extensions: []string{"hlsl", "fx", "fxh"}, Category: "code"},
	{Syntax: "glsl", Label: "GLSL", MIME: "text/x-glsl", Extensions: []string{"glsl", "vert", "frag", "geom", "comp", "tesc", "tese"}, Category: "code"},
	{Syntax: "wgsl", Label: "WGSL", MIME: "text/x-wgsl", Extensions: []string{"wgsl"}, Category: "code"},

	// ============================================
	// HARDWARE DESCRIPTION LANGUAGES
	// ============================================
	{Syntax: "verilog", Label: "Verilog", MIME: "text/x-verilog", Extensions: []string{"sv", "svh"}, Category: "code"},
	{Syntax: "vhdl", Label: "VHDL", MIME: "text/x-vhdl", Extensions: []string{"vhd", "vhdl"}, Category: "code"},

	// ============================================
	// LEGACY & SPECIALIZED LANGUAGES
	// ============================================
	{Syntax: "cobol", Label: "COBOL", MIME: "text/x-cobol", Extensions: []string{"cob", "cbl", "cobol"}, Category: "code"},
	{Syntax: "pascal", Label: "Pascal", MIME: "text/x-pascal", Extensions: []string{"pas", "p", "pp"}, Category: "code"},
	{Syntax: "delphi", Label: "Delphi", MIME: "text/x-delphi", Extensions: []string{"dpr", "dfm"}, Category: "code"},
	{Syntax: "basic", Label: "BASIC", MIME: "text/x-basic", Extensions: []string{"bas"}, Category: "code"},
	{Syntax: "vb", Label: "Visual Basic", MIME: "text/x-vb", Extensions: []string{"vb", "vbs"}, Category: "code"},

	// ============================================
	// BLOCKCHAIN & SMART CONTRACTS
	// ============================================
	{Syntax: "solidity", Label: "Solidity", MIME: "text/x-solidity", Extensions: []string{"sol"}, Category: "code"},
	{Syntax: "cairo", Label: "Cairo", MIME: "text/x-cairo", Extensions: []string{"cairo"}, Category: "code"},
	{Syntax: "move", Label: "Move", MIME: "text/x-move", Extensions: []string{"move"}, Category: "code"},

	// ============================================
	// SPECIAL FILE TYPES
	// ============================================
	{Syntax: "diff", Label: "Diff", MIME: "text/x-diff", Extensions: []string{"diff", "patch"}, Category: "code"},
	{Syntax: "git", Label: "Git Config", MIME: "text/x-git", Extensions: []string{"gitignore", "gitattributes", "gitmodules"}, Category: "code"},
	{Syntax: "svg", Label: "SVG", MIME: "image/svg+xml", Extensions: []string{"svg"}, Category: "image"},

	// ============================================
	// BINARY & ARCHIVE FORMATS
	// ============================================
	{Syntax: "pdf", Label: "PDF", MIME: "application/pdf", Extensions: []string{"pdf"}, Category: "pdf"},
	{Syntax: "image", Label: "Image", MIME: "image/", Extensions: []string{"jpg", "jpeg", "png", "gif", "webp", "bmp", "ico", "tiff", "tif"}, Category: "image"},
	{Syntax: "archive", Label: "Archive", MIME: "application/zip", Extensions: []string{"zip", "tar", "gz", "bz2", "xz", "7z", "rar", "tgz", "tbz2", "txz"}, Category: "archive"},

	// ============================================
	// DRAWING & DIAGRAM TOOLS
	// ============================================
	{Syntax: "excalidraw", Label: "Excalidraw", MIME: "application/vnd.excalidraw+json", Extensions: []string{"excalidraw", "excalidraw.json"}, Category: "excalidraw"},

	// ============================================
	// PLAIN TEXT (FALLBACK)
	// ============================================
	{Syntax: "text", Label: "Text", MIME: "text/plain", Extensions: []string{"txt", "text", "log"}, Category: "text"},
}

// unknownType is the fallback for unrecognized types
var unknownType = FileType{
	Syntax:     "auto",
	Label:      "Unknown",
	MIME:       "application/octet-stream",
	Extensions: []string{},
	Category:   "unknown",
}

// extensionToFileType maps extensions to their FileType (built at init)
var extensionToFileType map[string]*FileType

// mimeToFileType maps MIME types to their FileType (built at init)
var mimeToFileType map[string]*FileType

func init() {
	extensionToFileType = make(map[string]*FileType)
	mimeToFileType = make(map[string]*FileType)

	for i := range fileTypes {
		ft := &fileTypes[i]
		// Map extensions
		for _, ext := range ft.Extensions {
			extensionToFileType[strings.ToLower(ext)] = ft
		}
		// Map MIME type
		mimeToFileType[strings.ToLower(ft.MIME)] = ft
	}
}

// GetFileTypeByExtension returns the FileType for a given extension (without dot)
func GetFileTypeByExtension(ext string) *FileType {
	ext = strings.ToLower(strings.TrimPrefix(ext, "."))
	if ft, ok := extensionToFileType[ext]; ok {
		return ft
	}
	return &unknownType
}

// GetFileTypeByMIME returns the FileType for a given MIME type
func GetFileTypeByMIME(mimeType string) *FileType {
	lowerMime := strings.ToLower(mimeType)

	// Try exact match first
	if ft, ok := mimeToFileType[lowerMime]; ok {
		return ft
	}

	// Try prefix match (for MIME types with parameters like "text/html; charset=utf-8")
	for mime, ft := range mimeToFileType {
		if strings.HasPrefix(lowerMime, mime) {
			return ft
		}
	}

	// Special cases for generic matches
	if strings.Contains(lowerMime, "pdf") {
		return GetFileTypeByExtension("pdf")
	}
	if strings.Contains(lowerMime, "image") {
		return GetFileTypeByExtension("jpg")
	}
	if strings.Contains(lowerMime, "zip") || strings.Contains(lowerMime, "archive") || strings.Contains(lowerMime, "tar") || strings.Contains(lowerMime, "gzip") {
		return GetFileTypeByExtension("zip")
	}
	if strings.Contains(lowerMime, "text") {
		return GetFileTypeByExtension("txt")
	}

	return &unknownType
}

// DetectContentType detects the MIME type from filename and content
func DetectContentType(filename string, content []byte) string {
	// Try extension-based detection first using our comprehensive mapping
	if filename != "" {
		ext := strings.ToLower(filepath.Ext(filename))
		ext = strings.TrimPrefix(ext, ".")
		if ft, ok := extensionToFileType[ext]; ok {
			return ft.MIME
		}

		// Fallback to Go's built-in mime detection
		if mimeType := mime.TypeByExtension("." + ext); mimeType != "" {
			return mimeType
		}
	}

	// Fall back to content sniffing
	if len(content) > 0 {
		return http.DetectContentType(content)
	}

	// Default
	return "text/plain"
}

// DetectLanguageHint detects the language/syntax hint from filename
func DetectLanguageHint(filename string) string {
	if filename == "" {
		return ""
	}

	ext := strings.ToLower(filepath.Ext(filename))
	ext = strings.TrimPrefix(ext, ".")
	if ft, ok := extensionToFileType[ext]; ok {
		return ft.Syntax
	}

	return ""
}

// IsBinaryType checks if the content type is a binary/non-editable type
func IsBinaryType(contentType string) bool {
	ft := GetFileTypeByMIME(contentType)
	switch ft.Category {
	case "image", "pdf", "archive", "unknown":
		return true
	}
	return false
}
