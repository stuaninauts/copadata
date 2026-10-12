/**
 * The two series of the site (ADR 0010): order, position and neighbours of each item.
 */
import { getCollection, type CollectionEntry } from 'astro:content';
import { sectionPath, verdict, type Chip, type Lang } from '../i18n/ui';
import { fill, value } from './stats';

export type SeriesName = 'myths' | 'novelties';
type Entry = CollectionEntry<'myths'> | CollectionEntry<'novelties'>;

export interface Item {
  id: string;
  n: number;
  title: string;
  href: string;
  verdict: { label: string; chip: Chip };
}

function itemTitle(entry: Entry, series: SeriesName, lang: Lang): string {
  const d = entry.data;
  const text = series === 'myths' ? (d as CollectionEntry<'myths'>['data'])[lang].claim : (d as CollectionEntry<'novelties'>['data'])[lang].title;
  return fill(text, d.stats, lang, `${series}.${entry.id}.title`);
}

export async function series(name: SeriesName, lang: Lang): Promise<Item[]> {
  const entries = ((await getCollection(name)) as Entry[]).sort((a, b) => a.data.order - b.data.order);
  return entries.map((e, i) => ({
    id: e.id,
    n: i + 1,
    title: itemTitle(e, name, lang),
    href: sectionPath(lang, name, e.data.slug[lang]),
    verdict: verdict(String(value(e.data.verdict, `${name}.${e.id}.verdict`)), lang),
  }));
}

export interface Neighbours {
  index: number;
  total: number;
  prev?: Item;
  next?: Item;
}

export function neighbours(items: Item[], id: string): Neighbours {
  const index = items.findIndex((i) => i.id === id);
  if (index < 0) throw new Error(`series: "${id}" not found`);
  return { index, total: items.length, prev: items[index - 1], next: items[index + 1] };
}
