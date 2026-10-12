/**
 * Charts as static SVG, drawn by Observable Plot at build time (ADR 0007). No script reaches the
 * browser. Plot puts a <style> inside each SVG; the strict CSP would block it, so it is removed
 * here and its rules live in global.css (.chart). Colors come from CSS classes, so both themes work.
 */
import * as Plot from '@observablehq/plot';
import { parseHTML } from 'linkedom';

function render(options: Plot.PlotOptions): string {
  const { document } = parseHTML('<!doctype html><html><body></body></html>');
  const svg = Plot.plot({ ...options, document, className: 'chart' } as Plot.PlotOptions);
  return (svg as unknown as Element).outerHTML.replace(/<style>[\s\S]*?<\/style>/, '');
}

export interface EditionBar {
  year: string;
  value: number;
}

/** One bar per World Cup, the focus edition highlighted, labels only where they matter. */
export function editionBars(data: EditionBar[], o: {
  focus: string;
  labelled: string[];
  format: (v: number) => string;
  max: number;
  aria: string;
  /** Dashed reference line; its label goes in the figure caption, not on the bars. */
  mean?: number;
  tone?: 'accent' | 'blue';
  width?: number;
  height?: number;
}): string {
  const focus = data.filter((d) => d.year === o.focus);
  const rest = data.filter((d) => d.year !== o.focus);
  const labelled = data.filter((d) => d.year === o.focus || o.labelled.includes(d.year));
  const tone = o.tone ?? 'accent';
  return render({
    width: o.width ?? 640,
    height: o.height ?? 280,
    marginTop: 28,
    marginLeft: 8,
    marginRight: 8,
    ariaLabel: o.aria,
    x: { type: 'band', domain: data.map((d) => d.year), label: null, tickSize: 0, padding: 0.25 },
    y: { domain: [0, o.max], axis: null },
    marks: [
      Plot.barY(rest, { x: 'year', y: 'value', fill: 'currentColor', className: 'bar' }),
      Plot.barY(focus, { x: 'year', y: 'value', fill: 'currentColor', className: `bar-focus tone-${tone}` }),
      Plot.text(labelled, {
        x: 'year', y: 'value', dy: -10, text: (d: EditionBar) => o.format(d.value),
        fill: 'currentColor', className: 'bar-label',
      }),
      ...(o.mean !== undefined
        ? [Plot.ruleY([o.mean], { stroke: 'currentColor', strokeDasharray: '4,4', className: 'rule-mean' })]
        : []),
      Plot.ruleY([0], { stroke: 'currentColor', className: 'baseline' }),
    ],
  });
}

export interface HBar {
  label: string;
  value: number;
  focus: boolean;
}

/** Horizontal bars, the focus ones highlighted: a case against its reference. */
export function hBars(data: HBar[], o: { max: number; aria: string; format: (v: number) => string; tone?: 'accent' | 'blue' }): string {
  return render({
    width: 640,
    height: 36 * data.length + 24,
    marginLeft: 220,
    marginRight: 64,
    ariaLabel: o.aria,
    x: { domain: [0, o.max], axis: null },
    y: { domain: data.map((d) => d.label), label: null, tickSize: 0, padding: 0.3 },
    marks: [
      Plot.barX(data.filter((d) => !d.focus), { y: 'label', x: 'value', fill: 'currentColor', className: 'bar-ref' }),
      Plot.barX(data.filter((d) => d.focus), { y: 'label', x: 'value', fill: 'currentColor', className: `bar-focus tone-${o.tone ?? 'accent'}` }),
      Plot.text(data, {
        y: 'label', x: 'value', dx: 8, textAnchor: 'start', text: (d: HBar) => o.format(d.value),
        fill: 'currentColor', className: 'bar-label',
      }),
    ],
  });
}

export interface FunnelPoint {
  label: string;
  n: number;
  value: number;
  outside: boolean;
  low95: number;
  high95: number;
  low998: number;
  high998: number;
}

/** Funnel plot: each team's share against its number of goals, with the 95% and 99.8% limits. */
export function funnel(data: FunnelPoint[], o: { mean: number; aria: string; xLabel: string; format: (v: number) => string }): string {
  const byN = [...data].sort((a, b) => a.n - b.n);
  const limit = (key: 'low95' | 'high95' | 'low998' | 'high998', cls: string) =>
    Plot.line(byN, { x: 'n', y: (d: FunnelPoint) => Math.max(0, Math.min(1, d[key])), curve: 'monotone-x', stroke: 'currentColor', strokeDasharray: cls === 'limit-998' ? '2,4' : '6,4', className: cls });
  return render({
    width: 640,
    height: 320,
    marginLeft: 44,
    marginBottom: 40,
    ariaLabel: o.aria,
    x: { label: o.xLabel, labelAnchor: 'right', nice: true },
    y: { domain: [0, 0.7], tickFormat: (v: number) => o.format(v), label: null, ticks: 7 },
    marks: [
      Plot.ruleY([o.mean], { stroke: 'currentColor', className: 'rule-mean' }),
      limit('low95', 'limit-95'),
      limit('high95', 'limit-95'),
      limit('low998', 'limit-998'),
      limit('high998', 'limit-998'),
      Plot.dot(data.filter((d) => !d.outside), { x: 'n', y: 'value', r: 4, fill: 'currentColor', className: 'dot' }),
      Plot.dot(data.filter((d) => d.outside), { x: 'n', y: 'value', r: 5, fill: 'currentColor', className: 'dot-focus' }),
      Plot.text(data.filter((d) => d.outside), { x: 'n', y: 'value', text: 'label', dx: 8, textAnchor: 'start', fill: 'currentColor', className: 'bar-label' }),
    ],
  });
}

export interface Residual {
  label: string;
  value: number;
}

/** Bars around zero: above or below what was expected. */
export function diverging(data: Residual[], o: { aria: string; format: (v: number) => string; extent: number }): string {
  return render({
    width: 640,
    height: 28 * data.length + 24,
    marginLeft: 200,
    marginRight: 56,
    ariaLabel: o.aria,
    x: { domain: [-o.extent, o.extent], axis: null },
    y: { domain: data.map((d) => d.label), label: null, tickSize: 0, padding: 0.25 },
    marks: [
      Plot.barX(data.filter((d) => d.value >= 0), { y: 'label', x: 'value', fill: 'currentColor', className: 'bar-focus tone-blue' }),
      Plot.barX(data.filter((d) => d.value < 0), { y: 'label', x: 'value', fill: 'currentColor', className: 'bar-ref' }),
      Plot.ruleX([0], { stroke: 'currentColor', className: 'baseline' }),
      Plot.text(data.filter((d) => d.value >= 0), {
        y: 'label', x: 'value', dx: 6, textAnchor: 'start', text: (d: Residual) => o.format(d.value),
        fill: 'currentColor', className: 'bar-label',
      }),
      Plot.text(data.filter((d) => d.value < 0), {
        y: 'label', x: 'value', dx: -6, textAnchor: 'end', text: (d: Residual) => o.format(d.value),
        fill: 'currentColor', className: 'bar-label',
      }),
    ],
  });
}
