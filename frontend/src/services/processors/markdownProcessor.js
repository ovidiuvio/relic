/**
 * Advanced markdown processor using the unified ecosystem
 * Features: GitHub-flavored markdown, syntax highlighting, security sanitization
 */

import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'
import remarkRehype from 'remark-rehype'
import rehypeHighlight from 'rehype-highlight'
import rehypeSanitize from 'rehype-sanitize'
import rehypeStringify from 'rehype-stringify'
import hljs from 'highlight.js'

// Import a light theme CSS for highlight.js
import 'highlight.js/styles/github.css'

/**
 * Create the unified processing pipeline
 */
const processor = unified()
  .use(remarkParse)                     // Parse markdown to AST
  .use(remarkGfm)                       // GitHub-flavored markdown support
  .use(remarkBreaks)                    // Convert newlines to <br>
  .use(remarkRehype)                   // Convert markdown AST to HTML AST
  .use(rehypeHighlight, {               // Add syntax highlighting
    detect: true,
    ignoreMissing: true,
    aliases: {
      js: 'javascript',
      ts: 'typescript',
      sh: 'bash',
      py: 'python'
    }
  })
  .use(rehypeSanitize, {                // Security sanitization
    allowedTags: [
      // Text content
      'p', 'br', 'strong', 'em', 'i', 'b', 'u', 's', 'del', 'ins', 'mark',
      'small', 'sub', 'sup',

      // Headings
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',

      // Links and images
      'a', 'img',

      // Lists
      'ul', 'ol', 'li', 'dl', 'dt', 'dd',

      // Code
      'code', 'pre', 'div', 'span',

      // Tables
      'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'colgroup', 'col',

      // Blockquotes
      'blockquote',

      // HR
      'hr',

      // Details/summary
      'details', 'summary',

      // Inline elements
      'kbd', 'var', 'samp', 'abbr', 'cite', 'q',

      // Custom elements for code highlighting
      'span' // For highlight.js spans
    ],
    allowedAttributes: {
      '*': ['class', 'style'],
      'a': ['href', 'title', 'rel'],
      'img': ['src', 'alt', 'title', 'width', 'height', 'loading'],
      'code': ['class'],
      'pre': ['class'],
      'div': ['class'],
      'span': ['class'],
      'td': ['align', 'colspan', 'rowspan'],
      'th': ['align', 'colspan', 'rowspan'],
      'blockquote': ['cite'],
      'kbd': ['title'],
      'q': ['cite'],
      'time': ['datetime'],
      'abbr': ['title']
    },
    allowedClasses: {
      '*': ['hljs', 'language-*', 'highlighted', 'math'],
      'code': ['hljs', 'language-*'],
      'pre': ['hljs'],
      'div': ['highlight', 'highlight-source-*', 'highlight-lines-*'],
      'span': ['hljs-*', 'keyword', 'string', 'comment', 'number', 'function', 'variable', 'title', 'tag', 'attr', 'built_in', 'type', 'operator', 'punctuation', 'literal', 'symbol', 'class', 'params']
    }
  })
  .use(rehypeStringify)               // Convert HTML AST to string

/**
 * Process markdown content to HTML
 * @param {string|Uint8Array} content - Raw markdown content
 * @returns {Promise<Object>} Processed markdown object
 */
export async function processMarkdown(content) {
  try {
    const text = typeof content === 'string' ? content : new TextDecoder().decode(content)

    // Process the markdown
    const file = await processor.process(text)
    const html = String(file)

    return {
      type: 'markdown',
      html,
      preview: text,
      metadata: {
        lineCount: text.split('\n').length,
        charCount: text.length,
        wordCount: text.split(/\s+/).filter(word => word.length > 0).length,
        hasCodeBlocks: (html.match(/<code/g) || []).length,
        hasTables: html.includes('<table'),
        hasLinks: html.includes('<a'),
        hasImages: html.includes('<img')
      }
    }
  } catch (error) {
    console.error('Markdown processing error:', error)
    // Fallback to simple HTML escaping
    const text = typeof content === 'string' ? content : new TextDecoder().decode(content)
    const escapedHtml = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\n/g, '<br>')

    return {
      type: 'markdown',
      html: `<div class="markdown-error">${escapedHtml}</div>`,
      preview: text,
      metadata: {
        lineCount: text.split('\n').length,
        charCount: text.length,
        wordCount: text.split(/\s+/).filter(word => word.length > 0).length,
        hasCodeBlocks: 0,
        hasTables: false,
        hasLinks: false,
        hasImages: false,
        error: error.message
      }
    }
  }
}

/**
 * Get supported languages for code highlighting
 */
export function getSupportedLanguages() {
  return hljs.listLanguages().sort()
}

/**
 * Check if a language is supported for highlighting
 */
export function isLanguageSupported(lang) {
  return hljs.getLanguage(lang) !== undefined
}

export default {
  processMarkdown,
  getSupportedLanguages,
  isLanguageSupported
}