// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

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
  // The two versions of a page have different slugs (ADR 0010), so the sitemap lists each URL and the
  // pages carry their own hreflang links (Base.astro).
  integrations: [sitemap({ filter: (page) => !page.endsWith('/404/') })],
  // CSP estrita (ADR 0007): script-src e style-src saem com hashes no build. Nada inline sem hash,
  // por isso os SVGs do Plot chegam sem o <style> próprio (src/lib/charts.ts).
  // A única origem externa é o script do Web Analytics da Cloudflare (sem cookies), que a borda injeta
  // na página; as métricas voltam para o próprio domínio (/cdn-cgi/rum), então connect-src fica 'self'.
  security: {
    csp: {
      scriptDirective: { resources: ["'self'", 'https://static.cloudflareinsights.com'] },
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
