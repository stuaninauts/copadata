/** The chart of each item, from its export rows (src/lib/charts.ts draws them). */
import type { CollectionEntry } from 'astro:content';
import type { Lang } from '../i18n/ui';
import { editionBars, pairBars } from './charts';
import { fill, format, rows, value } from './stats';

/** The caption line for the dashed mean, when the chart has one. */
export function meanNote(entry: CollectionEntry<'novelties'>, lang: Lang): string | undefined {
  const label = entry.data.pt.meanLabel;
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
    aria: entry.data.pt.chartAria,
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

/** Myth charts: one panel per case, the case against its same-minute reference. */
export function mythPanels(entry: CollectionEntry<'myths'>, lang: Lang): Panel[] {
  const page = entry.data.pt.page;
  if (!page?.parts) throw new Error(`myths.${entry.id}: a page needs "parts" for its chart`);
  const table = `myth_${entry.id}`;
  return page.parts.map((p) => {
    const [row] = rows({ table, where: { case: p.case } });
    if (!row) throw new Error(`${table}: no case "${p.case}"`);
    const fmt = (v: number) => format(v, 'pct', lang);
    return {
      title: p.title,
      note: fill(p.note, entry.data.stats, lang, entry.id),
      svg: pairBars(
        [
          { label: p.focus, value: row.value as number, focus: true },
          { label: p.reference, value: row.reference as number, focus: false },
        ],
        { max: 0.32, format: fmt, aria: `${p.focus}: ${fmt(row.value as number)}; ${p.reference}: ${fmt(row.reference as number)}.` },
      ),
    };
  });
}
