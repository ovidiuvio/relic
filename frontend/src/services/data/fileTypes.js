// Centralized file type definitions
// Extracted from typeUtils.js
export const FILE_TYPES = [
    // ============================================
    // GENERAL PURPOSE PROGRAMMING LANGUAGES
    // ============================================
    {
        syntax: 'javascript',
        label: 'JavaScript',
        icon: 'fa-brands fa-js',
        mime: 'application/javascript',
        extensions: ['js', 'jsx', 'mjs', 'cjs'],
        category: 'code'
    },
    {
        syntax: 'typescript',
        label: 'TypeScript',
        icon: 'fa-brands fa-js',
        mime: 'application/x-typescript',
        extensions: ['ts', 'tsx'],
        category: 'code'
    },
    {
        syntax: 'python',
        label: 'Python',
        icon: 'fa-brands fa-python',
        mime: 'text/x-python',
        extensions: ['py', 'pyw', 'pyx', 'pyi', 'pyd', 'pyc'],
        category: 'code'
    },
    {
        syntax: 'java',
        label: 'Java',
        icon: 'fa-brands fa-java',
        mime: 'text/x-java-source',
        extensions: ['java', 'class', 'jar'],
        category: 'code'
    },
    {
        syntax: 'csharp',
        label: 'C#',
        icon: 'fa-code',
        mime: 'text/x-csharp',
        extensions: ['cs', 'csx'],
        category: 'code'
    },
    {
        syntax: 'cpp',
        label: 'C++',
        icon: 'fa-code',
        mime: 'text/x-c++',
        extensions: ['cpp', 'cc', 'cxx', 'c++', 'hpp', 'hh', 'hxx', 'h++'],
        category: 'code'
    },
    {
        syntax: 'c',
        label: 'C',
        icon: 'fa-code',
        mime: 'text/x-c',
        extensions: ['c', 'h'],
        category: 'code'
    },
    {
        syntax: 'objective-c',
        label: 'Objective-C',
        icon: 'fa-code',
        mime: 'text/x-objectivec',
        extensions: ['m', 'mm'],
        category: 'code'
    },
    {
        syntax: 'swift',
        label: 'Swift',
        icon: 'fa-brands fa-swift',
        mime: 'text/x-swift',
        extensions: ['swift'],
        category: 'code'
    },
    {
        syntax: 'kotlin',
        label: 'Kotlin',
        icon: 'fa-code',
        mime: 'text/x-kotlin',
        extensions: ['kt', 'kts', 'ktm'],
        category: 'code'
    },

    // ============================================
    // SYSTEMS PROGRAMMING LANGUAGES
    // ============================================
    {
        syntax: 'rust',
        label: 'Rust',
        icon: 'fa-brands fa-rust',
        mime: 'text/x-rust',
        extensions: ['rs'],
        category: 'code'
    },
    {
        syntax: 'go',
        label: 'Go',
        icon: 'fa-brands fa-golang',
        mime: 'text/x-go',
        extensions: ['go'],
        category: 'code'
    },
    {
        syntax: 'zig',
        label: 'Zig',
        icon: 'fa-code',
        mime: 'text/x-zig',
        extensions: ['zig'],
        category: 'code'
    },
    {
        syntax: 'd',
        label: 'D',
        icon: 'fa-code',
        mime: 'text/x-d',
        extensions: ['d', 'di'],
        category: 'code'
    },
    {
        syntax: 'nim',
        label: 'Nim',
        icon: 'fa-code',
        mime: 'text/x-nim',
        extensions: ['nim', 'nims', 'nimble'],
        category: 'code'
    },
    {
        syntax: 'v',
        label: 'V',
        icon: 'fa-code',
        mime: 'text/x-v',
        extensions: ['v', 'vsh'],
        category: 'code'
    },

    // ============================================
    // FUNCTIONAL PROGRAMMING LANGUAGES
    // ============================================
    {
        syntax: 'haskell',
        label: 'Haskell',
        icon: 'fa-code',
        mime: 'text/x-haskell',
        extensions: ['hs', 'lhs'],
        category: 'code'
    },
    {
        syntax: 'ocaml',
        label: 'OCaml',
        icon: 'fa-code',
        mime: 'text/x-ocaml',
        extensions: ['ml', 'mli', 'mll', 'mly'],
        category: 'code'
    },
    {
        syntax: 'fsharp',
        label: 'F#',
        icon: 'fa-code',
        mime: 'text/x-fsharp',
        extensions: ['fs', 'fsi', 'fsx', 'fsscript'],
        category: 'code'
    },
    {
        syntax: 'scala',
        label: 'Scala',
        icon: 'fa-code',
        mime: 'text/x-scala',
        extensions: ['scala', 'sc'],
        category: 'code'
    },
    {
        syntax: 'clojure',
        label: 'Clojure',
        icon: 'fa-code',
        mime: 'text/x-clojure',
        extensions: ['clj', 'cljs', 'cljc', 'edn'],
        category: 'code'
    },
    {
        syntax: 'elixir',
        label: 'Elixir',
        icon: 'fa-code',
        mime: 'text/x-elixir',
        extensions: ['ex', 'exs'],
        category: 'code'
    },
    {
        syntax: 'erlang',
        label: 'Erlang',
        icon: 'fa-code',
        mime: 'text/x-erlang',
        extensions: ['erl', 'hrl'],
        category: 'code'
    },
    {
        syntax: 'scheme',
        label: 'Scheme',
        icon: 'fa-code',
        mime: 'text/x-scheme',
        extensions: ['scm', 'ss', 'sld'],
        category: 'code'
    },
    {
        syntax: 'racket',
        label: 'Racket',
        icon: 'fa-code',
        mime: 'text/x-racket',
        extensions: ['rkt', 'rktl', 'rktd'],
        category: 'code'
    },
    {
        syntax: 'lisp',
        label: 'Lisp',
        icon: 'fa-code',
        mime: 'text/x-lisp',
        extensions: ['lisp', 'lsp', 'l', 'cl', 'fasl'],
        category: 'code'
    },

    // ============================================
    // WEB DEVELOPMENT
    // ============================================
    {
        syntax: 'html',
        label: 'HTML',
        icon: 'fa-brands fa-html5',
        mime: 'text/html',
        extensions: ['html', 'htm', 'xhtml'],
        category: 'html'
    },
    {
        syntax: 'css',
        label: 'CSS',
        icon: 'fa-brands fa-css3-alt',
        mime: 'text/css',
        extensions: ['css'],
        category: 'code'
    },
    {
        syntax: 'scss',
        label: 'SCSS',
        icon: 'fa-brands fa-sass',
        mime: 'text/x-scss',
        extensions: ['scss'],
        category: 'code'
    },
    {
        syntax: 'sass',
        label: 'Sass',
        icon: 'fa-brands fa-sass',
        mime: 'text/x-sass',
        extensions: ['sass'],
        category: 'code'
    },
    {
        syntax: 'less',
        label: 'Less',
        icon: 'fa-brands fa-less',
        mime: 'text/x-less',
        extensions: ['less'],
        category: 'code'
    },
    {
        syntax: 'php',
        label: 'PHP',
        icon: 'fa-brands fa-php',
        mime: 'application/x-php',
        extensions: ['php', 'phtml', 'php3', 'php4', 'php5', 'phps'],
        category: 'code'
    },
    {
        syntax: 'ruby',
        label: 'Ruby',
        icon: 'fa-gem',
        mime: 'application/x-ruby',
        extensions: ['rb', 'rbw', 'rake', 'gemspec'],
        category: 'code'
    },
    {
        syntax: 'vue',
        label: 'Vue',
        icon: 'fa-brands fa-vuejs',
        mime: 'text/x-vue',
        extensions: ['vue'],
        category: 'code'
    },
    {
        syntax: 'svelte',
        label: 'Svelte',
        icon: 'fa-code',
        mime: 'text/x-svelte',
        extensions: ['svelte'],
        category: 'code'
    },
    {
        syntax: 'jsx',
        label: 'JSX',
        icon: 'fa-brands fa-react',
        mime: 'text/jsx',
        extensions: ['jsx'],
        category: 'code'
    },

    // ============================================
    // SCRIPTING LANGUAGES
    // ============================================
    {
        syntax: 'bash',
        label: 'Bash',
        icon: 'fa-terminal',
        mime: 'text/x-shellscript',
        extensions: ['sh', 'bash'],
        category: 'code'
    },
    {
        syntax: 'shell',
        label: 'Shell',
        icon: 'fa-terminal',
        mime: 'application/x-sh',
        extensions: ['zsh', 'fish', 'ksh', 'csh', 'tcsh'],
        category: 'code'
    },
    {
        syntax: 'powershell',
        label: 'PowerShell',
        icon: 'fa-terminal',
        mime: 'application/x-powershell',
        extensions: ['ps1', 'psm1', 'psd1'],
        category: 'code'
    },
    {
        syntax: 'perl',
        label: 'Perl',
        icon: 'fa-code',
        mime: 'text/x-perl',
        extensions: ['pl', 'pm', 'perl'],
        category: 'code'
    },
    {
        syntax: 'lua',
        label: 'Lua',
        icon: 'fa-code',
        mime: 'text/x-lua',
        extensions: ['lua'],
        category: 'code'
    },
    {
        syntax: 'tcl',
        label: 'Tcl',
        icon: 'fa-code',
        mime: 'text/x-tcl',
        extensions: ['tcl'],
        category: 'code'
    },
    {
        syntax: 'awk',
        label: 'AWK',
        icon: 'fa-code',
        mime: 'text/x-awk',
        extensions: ['awk'],
        category: 'code'
    },
    {
        syntax: 'sed',
        label: 'Sed',
        icon: 'fa-code',
        mime: 'text/x-sed',
        extensions: ['sed'],
        category: 'code'
    },

    // ============================================
    // DATA & CONFIGURATION
    // ============================================
    {
        syntax: 'json',
        label: 'JSON',
        icon: 'fa-code',
        mime: 'application/json',
        extensions: ['json', 'jsonc', 'json5'],
        category: 'code'
    },
    {
        syntax: 'notebook',
        label: 'Jupyter Notebook',
        icon: 'fa-book-open',
        mime: 'application/x-ipynb+json',
        extensions: ['ipynb'],
        category: 'notebook'
    },
    {
        syntax: 'relic-index',
        label: 'Relic Index',
        icon: 'fa-solid fa-list-ul',
        mime: 'application/x-relic-index',
        extensions: ['rix'],
        category: 'relicindex'
    },
    {
        syntax: 'yaml',
        label: 'YAML',
        icon: 'fa-code',
        mime: 'application/x-yaml',
        extensions: ['yaml', 'yml'],
        category: 'code'
    },
    {
        syntax: 'xml',
        label: 'XML',
        icon: 'fa-code',
        mime: 'application/xml',
        extensions: ['xml', 'xsl', 'xslt', 'xsd', 'dtd'],
        category: 'code'
    },
    {
        syntax: 'toml',
        label: 'TOML',
        icon: 'fa-code',
        mime: 'application/toml',
        extensions: ['toml'],
        category: 'code'
    },
    {
        syntax: 'ini',
        label: 'INI',
        icon: 'fa-code',
        mime: 'text/x-ini',
        extensions: ['ini', 'cfg', 'conf', 'config'],
        category: 'code'
    },
    {
        syntax: 'properties',
        label: 'Properties',
        icon: 'fa-code',
        mime: 'text/x-properties',
        extensions: ['properties'],
        category: 'code'
    },
    {
        syntax: 'csv',
        label: 'CSV',
        icon: 'fa-file-csv',
        mime: 'text/csv',
        extensions: ['csv'],
        category: 'csv'
    },
    {
        syntax: 'tsv',
        label: 'TSV',
        icon: 'fa-file-csv',
        mime: 'text/tab-separated-values',
        extensions: ['tsv'],
        category: 'csv'
    },
    {
        syntax: 'env',
        label: 'Environment',
        icon: 'fa-code',
        mime: 'application/x-env',
        extensions: ['env'],
        category: 'code'
    },

    // ============================================
    // MARKUP & DOCUMENTATION
    // ============================================
    {
        syntax: 'markdown',
        label: 'Markdown',
        icon: 'fa-file-lines',
        mime: 'text/markdown',
        extensions: ['md', 'markdown', 'mdown', 'mkd'],
        category: 'markdown'
    },
    {
        syntax: 'restructuredtext',
        label: 'reStructuredText',
        icon: 'fa-file-lines',
        mime: 'text/x-rst',
        extensions: ['rst', 'rest'],
        category: 'markdown'
    },
    {
        syntax: 'asciidoc',
        label: 'AsciiDoc',
        icon: 'fa-file-lines',
        mime: 'text/x-asciidoc',
        extensions: ['adoc', 'asciidoc', 'asc'],
        category: 'markdown'
    },
    {
        syntax: 'org',
        label: 'Org Mode',
        icon: 'fa-file-lines',
        mime: 'text/x-org',
        extensions: ['org'],
        category: 'markdown'
    },
    {
        syntax: 'latex',
        label: 'LaTeX',
        icon: 'fa-code',
        mime: 'text/x-latex',
        extensions: ['tex', 'latex', 'sty', 'cls'],
        category: 'code'
    },
    {
        syntax: 'bibtex',
        label: 'BibTeX',
        icon: 'fa-code',
        mime: 'text/x-bibtex',
        extensions: ['bib', 'bibtex'],
        category: 'code'
    },

    // ============================================
    // QUERY LANGUAGES
    // ============================================
    {
        syntax: 'sql',
        label: 'SQL',
        icon: 'fa-database',
        mime: 'application/sql',
        extensions: ['sql', 'ddl', 'dml'],
        category: 'code'
    },
    {
        syntax: 'mysql',
        label: 'MySQL',
        icon: 'fa-database',
        mime: 'text/x-mysql',
        extensions: ['mysql'],
        category: 'code'
    },
    {
        syntax: 'pgsql',
        label: 'PostgreSQL',
        icon: 'fa-database',
        mime: 'text/x-pgsql',
        extensions: ['pgsql', 'postgres'],
        category: 'code'
    },
    {
        syntax: 'plsql',
        label: 'PL/SQL',
        icon: 'fa-database',
        mime: 'text/x-plsql',
        extensions: ['plsql', 'pls'],
        category: 'code'
    },
    {
        syntax: 'graphql',
        label: 'GraphQL',
        icon: 'fa-code',
        mime: 'application/graphql',
        extensions: ['graphql', 'gql'],
        category: 'code'
    },
    {
        syntax: 'sparql',
        label: 'SPARQL',
        icon: 'fa-database',
        mime: 'application/sparql-query',
        extensions: ['sparql', 'rq'],
        category: 'code'
    },

    // ============================================
    // TEMPLATE LANGUAGES
    // ============================================
    {
        syntax: 'handlebars',
        label: 'Handlebars',
        icon: 'fa-code',
        mime: 'text/x-handlebars-template',
        extensions: ['hbs', 'handlebars'],
        category: 'code'
    },
    {
        syntax: 'mustache',
        label: 'Mustache',
        icon: 'fa-code',
        mime: 'text/x-mustache',
        extensions: ['mustache'],
        category: 'code'
    },
    {
        syntax: 'jinja',
        label: 'Jinja',
        icon: 'fa-code',
        mime: 'text/x-jinja',
        extensions: ['jinja', 'jinja2', 'j2'],
        category: 'code'
    },
    {
        syntax: 'ejs',
        label: 'EJS',
        icon: 'fa-code',
        mime: 'text/x-ejs',
        extensions: ['ejs'],
        category: 'code'
    },
    {
        syntax: 'pug',
        label: 'Pug',
        icon: 'fa-code',
        mime: 'text/x-pug',
        extensions: ['pug', 'jade'],
        category: 'code'
    },
    {
        syntax: 'twig',
        label: 'Twig',
        icon: 'fa-code',
        mime: 'text/x-twig',
        extensions: ['twig'],
        category: 'code'
    },
    {
        syntax: 'liquid',
        label: 'Liquid',
        icon: 'fa-code',
        mime: 'text/x-liquid',
        extensions: ['liquid'],
        category: 'code'
    },
    {
        syntax: 'razor',
        label: 'Razor',
        icon: 'fa-code',
        mime: 'text/x-cshtml',
        extensions: ['cshtml', 'razor'],
        category: 'code'
    },

    // ============================================
    // DOMAIN-SPECIFIC LANGUAGES
    // ============================================
    {
        syntax: 'dockerfile',
        label: 'Dockerfile',
        icon: 'fa-brands fa-docker',
        mime: 'text/x-dockerfile',
        extensions: ['dockerfile'],
        category: 'code'
    },
    {
        syntax: 'makefile',
        label: 'Makefile',
        icon: 'fa-file-code',
        mime: 'text/x-makefile',
        extensions: ['makefile', 'mk', 'mak'],
        category: 'code'
    },
    {
        syntax: 'cmake',
        label: 'CMake',
        icon: 'fa-file-code',
        mime: 'text/x-cmake',
        extensions: ['cmake', 'cmake.in'],
        category: 'code'
    },
    {
        syntax: 'gradle',
        label: 'Gradle',
        icon: 'fa-code',
        mime: 'text/x-gradle',
        extensions: ['gradle'],
        category: 'code'
    },
    {
        syntax: 'groovy',
        label: 'Groovy',
        icon: 'fa-code',
        mime: 'text/x-groovy',
        extensions: ['groovy', 'gvy', 'gy', 'gsh'],
        category: 'code'
    },
    {
        syntax: 'terraform',
        label: 'Terraform',
        icon: 'fa-code',
        mime: 'text/x-terraform',
        extensions: ['tf', 'tfvars', 'hcl'],
        category: 'code'
    },
    {
        syntax: 'nginx',
        label: 'Nginx',
        icon: 'fa-server',
        mime: 'text/x-nginx-conf',
        extensions: ['nginx', 'nginxconf'],
        category: 'code'
    },
    {
        syntax: 'apache',
        label: 'Apache',
        icon: 'fa-server',
        mime: 'text/x-apache-conf',
        extensions: ['htaccess', 'apache', 'apacheconf'],
        category: 'code'
    },
    {
        syntax: 'protobuf',
        label: 'Protocol Buffers',
        icon: 'fa-code',
        mime: 'text/x-protobuf',
        extensions: ['proto'],
        category: 'code'
    },
    {
        syntax: 'thrift',
        label: 'Thrift',
        icon: 'fa-code',
        mime: 'text/x-thrift',
        extensions: ['thrift'],
        category: 'code'
    },

    // ============================================
    // SCIENTIFIC & MATHEMATICAL
    // ============================================
    {
        syntax: 'r',
        label: 'R',
        icon: 'fa-code',
        mime: 'text/x-r',
        extensions: ['r', 'R'],
        category: 'code'
    },
    {
        syntax: 'julia',
        label: 'Julia',
        icon: 'fa-code',
        mime: 'text/x-julia',
        extensions: ['jl'],
        category: 'code'
    },
    {
        syntax: 'matlab',
        label: 'MATLAB',
        icon: 'fa-code',
        mime: 'text/x-matlab',
        extensions: ['m', 'mat'],
        category: 'code'
    },
    {
        syntax: 'octave',
        label: 'Octave',
        icon: 'fa-code',
        mime: 'text/x-octave',
        extensions: ['m'],
        category: 'code'
    },
    {
        syntax: 'mathematica',
        label: 'Mathematica',
        icon: 'fa-code',
        mime: 'text/x-mathematica',
        extensions: ['nb', 'wl', 'wls', 'm'],
        category: 'code'
    },
    {
        syntax: 'sage',
        label: 'Sage',
        icon: 'fa-code',
        mime: 'text/x-sage',
        extensions: ['sage'],
        category: 'code'
    },
    {
        syntax: 'fortran',
        label: 'Fortran',
        icon: 'fa-code',
        mime: 'text/x-fortran',
        extensions: ['f', 'for', 'f90', 'f95', 'f03', 'f08'],
        category: 'code'
    },

    // ============================================
    // ASSEMBLY & LOW-LEVEL
    // ============================================
    {
        syntax: 'asm',
        label: 'Assembly',
        icon: 'fa-microchip',
        mime: 'text/x-asm',
        extensions: ['asm', 's', 'nasm'],
        category: 'code'
    },
    {
        syntax: 'llvm',
        label: 'LLVM IR',
        icon: 'fa-code',
        mime: 'text/x-llvm',
        extensions: ['ll'],
        category: 'code'
    },
    {
        syntax: 'wasm',
        label: 'WebAssembly',
        icon: 'fa-code',
        mime: 'application/wasm',
        extensions: ['wasm', 'wat'],
        category: 'code'
    },

    // ============================================
    // MOBILE DEVELOPMENT
    // ============================================
    {
        syntax: 'dart',
        label: 'Dart',
        icon: 'fa-code',
        mime: 'text/x-dart',
        extensions: ['dart'],
        category: 'code'
    },

    // ============================================
    // GAME DEVELOPMENT
    // ============================================
    {
        syntax: 'gdscript',
        label: 'GDScript',
        icon: 'fa-code',
        mime: 'text/x-gdscript',
        extensions: ['gd'],
        category: 'code'
    },
    {
        syntax: 'hlsl',
        label: 'HLSL',
        icon: 'fa-code',
        mime: 'text/x-hlsl',
        extensions: ['hlsl', 'fx', 'fxh'],
        category: 'code'
    },
    {
        syntax: 'glsl',
        label: 'GLSL',
        icon: 'fa-code',
        mime: 'text/x-glsl',
        extensions: ['glsl', 'vert', 'frag', 'geom', 'comp', 'tesc', 'tese'],
        category: 'code'
    },
    {
        syntax: 'wgsl',
        label: 'WGSL',
        icon: 'fa-code',
        mime: 'text/x-wgsl',
        extensions: ['wgsl'],
        category: 'code'
    },

    // ============================================
    // HARDWARE DESCRIPTION LANGUAGES
    // ============================================
    {
        syntax: 'verilog',
        label: 'Verilog',
        icon: 'fa-microchip',
        mime: 'text/x-verilog',
        extensions: ['v', 'vh', 'sv', 'svh'],
        category: 'code'
    },
    {
        syntax: 'vhdl',
        label: 'VHDL',
        icon: 'fa-microchip',
        mime: 'text/x-vhdl',
        extensions: ['vhd', 'vhdl'],
        category: 'code'
    },

    // ============================================
    // LEGACY & SPECIALIZED LANGUAGES
    // ============================================
    {
        syntax: 'cobol',
        label: 'COBOL',
        icon: 'fa-code',
        mime: 'text/x-cobol',
        extensions: ['cob', 'cbl', 'cobol'],
        category: 'code'
    },
    {
        syntax: 'pascal',
        label: 'Pascal',
        icon: 'fa-code',
        mime: 'text/x-pascal',
        extensions: ['pas', 'p', 'pp'],
        category: 'code'
    },
    {
        syntax: 'delphi',
        label: 'Delphi',
        icon: 'fa-code',
        mime: 'text/x-delphi',
        extensions: ['dpr', 'dfm'],
        category: 'code'
    },
    {
        syntax: 'basic',
        label: 'BASIC',
        icon: 'fa-code',
        mime: 'text/x-basic',
        extensions: ['bas'],
        category: 'code'
    },
    {
        syntax: 'vb',
        label: 'Visual Basic',
        icon: 'fa-code',
        mime: 'text/x-vb',
        extensions: ['vb', 'vbs'],
        category: 'code'
    },

    // ============================================
    // BLOCKCHAIN & SMART CONTRACTS
    // ============================================
    {
        syntax: 'solidity',
        label: 'Solidity',
        icon: 'fa-code',
        mime: 'text/x-solidity',
        extensions: ['sol'],
        category: 'code'
    },
    {
        syntax: 'cairo',
        label: 'Cairo',
        icon: 'fa-code',
        mime: 'text/x-cairo',
        extensions: ['cairo'],
        category: 'code'
    },
    {
        syntax: 'move',
        label: 'Move',
        icon: 'fa-code',
        mime: 'text/x-move',
        extensions: ['move'],
        category: 'code'
    },

    // ============================================
    // SPECIAL FILE TYPES
    // ============================================
    {
        syntax: 'diff',
        label: 'Diff',
        icon: 'fa-code-compare',
        mime: 'text/x-diff',
        extensions: ['diff', 'patch'],
        category: 'code'
    },
    {
        syntax: 'git',
        label: 'Git Config',
        icon: 'fa-brands fa-git-alt',
        mime: 'text/x-git',
        extensions: ['gitignore', 'gitattributes', 'gitmodules'],
        category: 'code'
    },
    {
        syntax: 'svg',
        label: 'SVG',
        icon: 'fa-image',
        mime: 'image/svg+xml',
        extensions: ['svg'],
        category: 'image'
    },

    // ============================================
    // BINARY & ARCHIVE FORMATS
    // ============================================
    {
        syntax: 'pdf',
        label: 'PDF',
        icon: 'fa-file-pdf',
        mime: 'application/pdf',
        extensions: ['pdf'],
        category: 'pdf'
    },
    {
        syntax: 'image',
        label: 'Image',
        icon: 'fa-image',
        mime: 'image/',
        extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'tiff', 'tif'],
        category: 'image'
    },
    {
        syntax: 'archive',
        label: 'Archive',
        icon: 'fa-file-zipper',
        mime: 'application/zip',
        extensions: ['zip', 'tar', 'gz', 'bz2', 'xz', '7z', 'rar', 'tgz', 'tbz2', 'txz'],
        category: 'archive'
    },

    // ============================================
    // DRAWING & DIAGRAM TOOLS
    // ============================================
    {
        syntax: 'excalidraw',
        label: 'Excalidraw',
        icon: 'fa-pen-to-square',
        mime: 'application/vnd.excalidraw+json',
        extensions: ['excalidraw', 'excalidraw.json'],
        category: 'excalidraw'
    },

    // ============================================
    // PLAIN TEXT (FALLBACK)
    // ============================================
    {
        syntax: 'text',
        label: 'Text',
        icon: 'fa-file-lines',
        mime: 'text/plain',
        extensions: ['txt', 'text', 'log'],
        category: 'text'
    }
]
