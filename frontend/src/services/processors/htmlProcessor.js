import { decodeContent } from './utils/contentUtils'

/**
 * Process HTML content
 */
export function processHTML(content) {
    const text = decodeContent(content)

    // Inject navigation interception script to prevent recursive iframe loading
    // This script intercepts link clicks and either:
    // 1. Navigates the parent app to the relic (if link is to a relic ID)
    // 2. Opens external links in a new tab
    const navigationScript = `
<script>
(function() {
  // Prevent iframe navigation that causes recursive navigation bar rendering
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    if (!link || !link.href) return;

    try {
      const url = new URL(link.href);
      const path = url.pathname;

      // Check if this looks like a relic ID (32-char hex string)
      const parts = path.split('/').filter(p => p);
      if (parts.length >= 1 && /^[a-f0-9]{32}$/i.test(parts[0])) {
        // Navigate parent window to this relic
        e.preventDefault();
        if (window.parent) {
          window.parent.location.href = path;
        } else {
          window.top.location.href = path;
        }
        return;
      }

      // For all other links, open in new tab to prevent iframe navigation
      if (link.target !== '_blank') {
        e.preventDefault();
        window.open(link.href, '_blank');
      }
    } catch (err) {
      // If URL parsing fails, let the link work normally
      console.error('Link navigation error:', err);
    }
  }, true);
})();
</script>
  `.trim();

    // Inject the script before </body> or at the end if no body tag
    let injectedHtml = text;
    if (/<\/body>/i.test(text)) {
        injectedHtml = text.replace(/<\/body>/i, `${navigationScript}\n</body>`);
    } else if (/<\/html>/i.test(text)) {
        injectedHtml = text.replace(/<\/html>/i, `${navigationScript}\n</html>`);
    } else {
        injectedHtml = text + '\n' + navigationScript;
    }

    return {
        type: 'html',
        html: injectedHtml,
        metadata: {
            charCount: text.length,
            // Basic HTML structure validation
            hasDoctype: text.toLowerCase().includes('<!doctype'),
            hasHtmlTag: text.toLowerCase().includes('<html'),
            hasBodyTag: text.toLowerCase().includes('<body')
        }
    }
}
