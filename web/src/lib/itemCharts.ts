/** The chart of each item, from its export rows (src/lib/charts.ts draws them). */
import type { CollectionEntry } from 'astro:content';
import type { Lang } from '../i18n/ui';
import { teamName } from '../i18n/teams';
import { diverging, editionBars, funnel, hBars } from './charts';
import { fill, format, rows, value } from './stats';

/** The caption line for the dashed mean, when the chart has one. */
export function meanNote(entry: CollectionEntry<'novelties'>, lang: Lang): string | undefined {
  const label = entry.data[lang].meanLabel;
  return entry.data.chart.mean && label ? fill(label, entry.data.stats, lang, entry.id) : undefined;
}

export function noveltyChart(entry: CollectionEntry<'novelties'>, lang: Lang, size?: { width: number; height: number }): string {
  const c = entry.data.chart;
  const data = rows(c.rows)
    .map((r) => ({ year: String(r.scope), value: r.value as number }))
    .sort((a, b) => a.year.localeCompare(b.year));
  const mean = c.mean ? (value(c.mean, `${entry.id}.chart.mean`) as number) : undefined;
  return editionBars(data, {
    focus: '2026',
    labelled: c.labelled,
    max: c.max,
    format: (v) => format(v, c.format, lang),
    aria: entry.data[lang].chartAria,
    mean,
    tone: entry.id === 'ko_final_quarter' ? 'accent' : 'blue',
    ...size,
  });
}

export interface Panel {
  title: string;
  note: string;
  svg: string;
}

/** Myth charts: explicit bars, the late-goal funnel or the hosts' residuals. */
export function mythPanels(entry: CollectionEntry<'myths'>, lang: Lang): Panel[] {
  const c = entry.data.chart;
  const at = `myths.${entry.id}.chart`;
  const note = (text: { pt: string; en: string }) => fill(text[lang], entry.data.stats, lang, at);
  const pct = (v: number) => format(v, 'pct', lang);

  if (c.kind === 'bars') {
    const tone = String(value(entry.data.verdict, at)) === 'myth' ? 'accent' : 'blue';
    return c.panels.map((p) => {
      const data = p.bars.map((b) => ({ label: b.label[lang], value: value(b.ref, at) as number, focus: b.focus }));
      const fmt = (v: number) => format(v, c.format, lang);
      return {
        title: p.title[lang],
        note: note(p.note),
        svg: hBars(data, { max: c.max, format: fmt, tone, aria: data.map((d) => `${d.label}: ${fmt(d.value)}`).join('; ') }),
      };
    });
  }

  if (c.kind === 'funnel') {
    return c.panels.map((p) => {
      const found = rows({ table: 'myth_late_specialists', where: { direction: p.direction } });
      const data = found.map((r) => ({
        label: teamName(String(r.team), lang),
        n: r.n as number,
        value: r.value as number,
        outside: Math.abs(r.z as number) > 1.96,
        low95: r.low95 as number,
        high95: r.high95 as number,
        low998: r.low998 as number,
        high998: r.high998 as number,
      }));
      return {
        title: p.title[lang],
        note: note(p.note),
        svg: funnel(data, {
          mean: found[0].mean as number,
          format: pct,
          xLabel: lang === 'pt' ? 'gols no tempo normal →' : 'regulation goals →',
          aria: p.title[lang],
        }),
      };
    });
  }

  const hosts = rows({ table: 'myth_home_advantage' })
    .map((r) => ({ label: `${r.year} · ${teamName(String(r.team), lang)}`, value: r.residual as number }));
  const fmt = (v: number) => format(v, 'pp', lang);
  return [{
    title: c.panels[0].title[lang],
    note: note(c.panels[0].note),
    svg: diverging(hosts, { extent: 0.35, format: fmt, aria: hosts.map((h) => `${h.label}: ${fmt(h.value)}`).join('; ') }),
  }];
}
