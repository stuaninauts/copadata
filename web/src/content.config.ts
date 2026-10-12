import { defineCollection } from 'astro:content';
import { file } from 'astro/loaders';
import { z } from 'astro/zod';

// A number in the content: a reference to the export (src/lib/stats.ts), never a typed value.
const ref = z.object({
  table: z.string(),
  where: z.record(z.string(), z.any()).optional(),
  field: z.string().optional(),
  agg: z.enum(['one', 'count', 'min', 'max']).optional(),
  format: z.enum(['raw', 'int', 'pct', 'pp', 'pp_abs', 'dec1', 'dec2', 'p']).optional(),
});

const page = z.object({
  question: z.string().optional(),
  title: z.string(),
  lede: z.string(),
  chartTitle: z.string(),
  chartNote: z.string(),
  facts: z.array(z.object({ big: z.string(), text: z.string() })).length(3),
  method: z.array(z.object({ label: z.string(), text: z.string() })),
  // Myth charts with one panel per case (e.g. 2-0, then 2-1): rows of the myth's export table.
  parts: z.array(z.object({ title: z.string(), note: z.string(), case: z.string(), focus: z.string(), reference: z.string() })).optional(),
});

const slug = z.object({ pt: z.string(), en: z.string() });

// Mitos (ADR 0008): one row each on the home, a page when `page` is written.
const myths = defineCollection({
  loader: file('src/content/myths.yaml'),
  schema: z.object({
    order: z.number().int().positive(),
    slug,
    verdict: ref,
    stats: z.record(z.string(), ref),
    pt: z.object({ claim: z.string(), big: z.string(), caption: z.string(), page: page.optional() }),
  }),
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
    pt: z.object({
      title: z.string(),
      text: z.string(),
      chartCaption: z.string(),
      chartAria: z.string(),
      meanLabel: z.string().optional(),
      page: page.optional(),
    }),
  }),
});

export const collections = { myths, novelties };
