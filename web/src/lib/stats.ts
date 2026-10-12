/**
 * Numbers by reference (ADR 0006, ADR 0010): content cites the export, never types a number.
 * A reference that does not resolve to exactly what it asks for throws, so the build fails.
 * Nothing here computes a rate: it selects rows of web/public/data/ and formats them.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Lang } from '../i18n/ui';

type Value = string | number | boolean | null;
type Row = Record<string, Value>;
type Condition = Value | { ne?: Value; gt?: number };

export interface Ref {
  table: string;
  where?: Record<string, Condition>;
  field?: string;
  /** one (default): exactly one row; count: number of rows; min / max: over `field`. */
  agg?: 'one' | 'count' | 'min' | 'max';
  format?: Format;
}

export type Format = 'raw' | 'int' | 'pct' | 'pp' | 'pp_abs' | 'dec1' | 'dec2' | 'p';

const DATA = join(process.cwd(), 'public', 'data');
const cache = new Map<string, Row[]>();

export function table(name: string): Row[] {
  if (!cache.has(name)) cache.set(name, JSON.parse(readFileSync(join(DATA, `${name}.json`), 'utf8')) as Row[]);
  return cache.get(name)!;
}

function matches(row: Row, where: Record<string, Condition> = {}): boolean {
  return Object.entries(where).every(([key, cond]) => {
    if (!(key in row)) throw new Error(`stats: column "${key}" not in row`);
    const v = row[key];
    if (cond !== null && typeof cond === 'object') {
      if ('ne' in cond) return v !== cond.ne;
      if ('gt' in cond) return typeof v === 'number' && v > (cond.gt as number);
    }
    return v === cond;
  });
}

export function rows(ref: Pick<Ref, 'table' | 'where'>): Row[] {
  return table(ref.table).filter((r) => matches(r, ref.where));
}

export function value(ref: Ref, where = ''): Value {
  const found = rows(ref);
  const at = `stats ${where} (${ref.table} ${JSON.stringify(ref.where ?? {})})`;
  const agg = ref.agg ?? 'one';
  if (agg === 'count') return found.length;
  if (found.length === 0) throw new Error(`${at}: no row`);
  const field = ref.field;
  if (!field || !(field in found[0])) throw new Error(`${at}: no field "${field}"`);
  if (agg === 'one') {
    if (found.length !== 1) throw new Error(`${at}: ${found.length} rows, expected 1`);
    return found[0][field];
  }
  const nums = found.map((r) => r[field] as number);
  return agg === 'min' ? Math.min(...nums) : Math.max(...nums);
}

const decimal = (v: number, digits: number, lang: Lang) =>
  v.toLocaleString(lang === 'pt' ? 'pt-BR' : 'en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function format(v: Value, fmt: Format = 'raw', lang: Lang): string {
  if (fmt === 'raw') return String(v);
  if (typeof v !== 'number') throw new Error(`stats: "${fmt}" needs a number, got ${JSON.stringify(v)}`);
  switch (fmt) {
    case 'int': return decimal(v, 0, lang);
    case 'pct': return `${Math.round(100 * v)}%`;
    case 'pp': { const n = Math.round(100 * v); return n > 0 ? `+${n}` : `${n}`; }
    case 'pp_abs': return `${Math.abs(Math.round(100 * v))}`;
    case 'dec1': return decimal(v, 1, lang);
    case 'dec2': return decimal(v, 2, lang);
    case 'p': return `≈ ${decimal(v, 2, lang)}`;
  }
}

/** Replace each {name} in a text with its formatted stat; an unknown name throws. */
export function fill(text: string, stats: Record<string, Ref>, lang: Lang, where = ''): string {
  return text.replace(/\{(\w+)\}/g, (_, name: string) => {
    const ref = stats[name];
    if (!ref) throw new Error(`stats ${where}: "{${name}}" is not defined`);
    return format(value(ref, `${where}.${name}`), ref.format, lang);
  });
}

interface Manifest {
  editions: number[];
  tables: Record<string, { rows: number }>;
}

/** The export's manifest: editions covered and table sizes. */
export function manifest(): Manifest {
  return JSON.parse(readFileSync(join(DATA, 'manifest.json'), 'utf8')) as Manifest;
}

/** Replace {name} with given values (interface text, not content numbers). */
export function interpolate(text: string, values: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (_, name: string) => {
    if (!(name in values)) throw new Error(`interpolate: "{${name}}" missing`);
    return String(values[name]);
  });
}
