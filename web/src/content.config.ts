import { defineCollection } from 'astro:content';
import { file } from 'astro/loaders';
import { z } from 'astro/zod';

// A number in the content: a reference to the export (src/lib/stats.ts), never a typed value.
const ref = z.object({
  table: z.string(),
  where: z.record(z.string(), z.any()).optional(),
  field: z.string().optional(),
  agg: z.enum(['one', 'count', 'min', 'max', 'sum']).optional(),
  format: z.enum(['raw', 'int', 'pct', 'pp', 'pp_abs', 'dec1', 'dec2', 'p']).optional(),
});

/** A text in both languages (labels inside charts). */
const both = z.object({ pt: z.string(), en: z.string() });

// The page of an item, in one language (ADR 0010).
const page = z.object({
  question: z.string().optional(),
  title: z.string(),
  lede: z.string(),
  chartTitle: z.string(),
  chartNote: z.string(),
  facts: z.array(z.object({ big: z.string(), text: z.string() })).length(3),
  method: z.array(z.object({ label: z.string(), text: z.string() })),
});

// Myth charts (src/lib/itemCharts.ts): explicit bars, the late-goal funnel, or the hosts' residuals.
const panel = z.object({ title: both, note: both });
const mythChart = z.discriminatedUnion('kind', [
  z.object({
    kind: z.literal('bars'),
    max: z.number(),
    format: z.enum(['pct', 'dec1']),
    panels: z.array(panel.extend({ bars: z.array(z.object({ label: both, ref, focus: z.boolean().default(false) })) })),
  }),
  z.object({ kind: z.literal('funnel'), panels: z.array(panel.extend({ direction: z.enum(['scored', 'conceded']) })) }),
  z.object({ kind: z.literal('hosts'), panels: z.array(panel).length(1) }),
]);

const mythText = z.object({ claim: z.string(), big: z.string(), caption: z.string(), page });
const slug = z.object({ pt: z.string(), en: z.string() });

// Mitos (ADR 0008): one row each on the home and a page each.
const myths = defineCollection({
  loader: file('src/content/myths.yaml'),
  schema: z.object({
    order: z.number().int().positive(),
    slug,
    verdict: ref,
    stats: z.record(z.string(), ref),
    chart: mythChart,
    pt: mythText,
    en: mythText,
  }),
});

const noveltyText = z.object({
  title: z.string(),
  text: z.string(),
  chartCaption: z.string(),
  chartAria: z.string(),
  meanLabel: z.string().optional(),
  page,
});

// O que 2026 teve de diferente: the headlines of the 2026 audit (season_outlier).
const novelties = defineCollection({
  loader: file('src/content/novelties.yaml'),
  schema: z.object({
    order: z.number().int().positive(),
    slug,
    verdict: ref,
    stats: z.record(z.string(), ref),
    chart: z.object({
      rows: ref,
      format: z.enum(['pct', 'dec2']),
      max: z.number(),
      labelled: z.array(z.string()),
      mean: ref.optional(),
    }),
    pt: noveltyText,
    en: noveltyText,
  }),
});

export const collections = { myths, novelties };
