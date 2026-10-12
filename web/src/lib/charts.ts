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

export interface PairBar {
  label: string;
  value: number;
  focus: boolean;
}

/** Two horizontal bars: the case against its reference. */
export function pairBars(data: PairBar[], o: { max: number; aria: string; format: (v: number) => string }): string {
  return render({
    width: 640,
    height: 96,
    marginLeft: 220,
    marginRight: 56,
    ariaLabel: o.aria,
    x: { domain: [0, o.max], axis: null },
    y: { domain: data.map((d) => d.label), label: null, tickSize: 0, padding: 0.3 },
    marks: [
      Plot.barX(data.filter((d) => !d.focus), { y: 'label', x: 'value', fill: 'currentColor', className: 'bar-ref' }),
      Plot.barX(data.filter((d) => d.focus), { y: 'label', x: 'value', fill: 'currentColor', className: 'bar-focus tone-accent' }),
      Plot.text(data, {
        y: 'label', x: 'value', dx: 8, textAnchor: 'start', text: (d: PairBar) => o.format(d.value),
        fill: 'currentColor', className: 'bar-label',
      }),
    ],
  });
}
