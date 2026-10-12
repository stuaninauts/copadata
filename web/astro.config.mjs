// @ts-check
import { defineConfig } from 'astro/config';

// PT na raiz e EN em /en/, com URLs no idioma da página (ADR 0010).
export default defineConfig({
  site: 'https://copa.stuaninauts.com',
  trailingSlash: 'ignore',
  // No Markdown here; Shiki would add inline styles the CSP blocks.
  markdown: { syntaxHighlight: false },
  i18n: {
    defaultLocale: 'pt',
    locales: ['pt', 'en'],
    routing: { prefixDefaultLocale: false },
  },
  // CSP estrita (ADR 0007): script-src e style-src saem com hashes no build. Nada inline sem hash,
  // por isso os SVGs do Plot chegam sem o <style> próprio (src/lib/charts.ts).
  security: {
    csp: {
      directives: [
        "default-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ],
    },
  },
});
