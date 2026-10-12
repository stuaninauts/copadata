/** Interface text and routes per language (ADR 0010). Content lives in src/content/. */
export type Lang = 'pt' | 'en';
export type Section = 'myths' | 'novelties' | 'explore' | 'method';

const SEGMENT: Record<Section, Record<Lang, string>> = {
  myths: { pt: 'mitos', en: 'myths' },
  novelties: { pt: '2026', en: '2026' },
  explore: { pt: 'explorar', en: 'explore' },
  method: { pt: 'metodo', en: 'method' },
};

/** Home anchors of each series, used when an item has no page yet. */
const ANCHOR: Record<'myths' | 'novelties', string> = { myths: 'mitos', novelties: 'novidades' };

export function home(lang: Lang): string {
  return lang === 'pt' ? '/' : '/en/';
}

export function sectionPath(lang: Lang, section: Section, slug?: string): string {
  const prefix = lang === 'pt' ? '' : '/en';
  return `${prefix}/${SEGMENT[section][lang]}/${slug ? `${slug}/` : ''}`;
}

export function seriesAnchor(lang: Lang, series: 'myths' | 'novelties'): string {
  return `${home(lang)}#${ANCHOR[series]}`;
}

export const ui = {
  pt: {
    'site.name': 'CopaData',
    'site.description': 'Frases de torcedor sobre a Copa do Mundo, conferidas em 11 Copas e 708 jogos.',
    'nav.label': 'Principal',
    'nav.skip': 'Pular para o conteúdo',
    'nav.myths': 'Mitos',
    'nav.novelties': '2026',
    'nav.explore': 'Explorar',
    'nav.method': 'Método',
    'nav.other': 'EN',
    'nav.otherLabel': 'English version',
    'crumbs.label': 'Você está em',
    'crumbs.home': 'Início',
    'series.myths': 'Mitos',
    'series.novelties': 'O que 2026 teve de diferente',
    'series.mythsList': 'As frases',
    'pos.myth': 'Mito',
    'pos.of': 'de',
    'pager.label': 'Navegar na série',
    'pager.prev': 'Anterior',
    'pager.next': 'Próximo',
    'pager.back': 'Voltar',
    'pager.allMyths': 'Todas as frases',
    'pager.nextSection': 'Próxima seção',
    'pager.here': 'Você está aqui',
    'item.claim': 'A frase',
    'item.verdict': 'Veredito',
    'item.meaning': 'O que isso quer dizer',
    'item.how': 'Como sabemos',
    'item.code': 'Ver o código e os dados',
    'home.see': 'Ver',
    'home.eyebrow': 'Copa do Mundo · {editions} Copas, {first} a {last}',
    'home.title': 'Das {total} frases que todo torcedor repete sobre a Copa, {myths} são mito.',
    'home.lede': 'Conferimos cada uma em {matches} jogos. A regra que separa mito de verdade foi escrita antes de olhar os dados, e publicamos todas, inclusive as que não deram em nada.',
    'home.mythsHeading': 'As frases, conferidas',
    'home.noveltiesTitle': 'E o que 2026 teve de diferente?',
    'home.noveltiesLede': 'Cada número de 2026 comparado com Copas sorteadas do histórico: o que sai da faixa é novidade; o que fica dentro, não.',
    'home.fullAnalysis': 'Ver a análise completa',
    'home.closing': '{editions} Copas, {matches} jogos, {total} frases conferidas.',
    'home.closingText': 'Cada resposta mostra quantos jogos a sustentam e como foi calculada. Os dados são abertos.',
    'home.closingCta': 'Como testamos as frases',
    'footer.source': 'Fonte: Fjelstul World Cup Database (CC-BY-SA 4.0) para 1986-2022; OpenFootball (CC0) para 2026; resultados internacionais (CC0) para a força das seleções. Conteúdo sob CC-BY-SA 4.0.',
    'footer.code': 'Código e método',
  },
  en: {} as Record<string, string>,
} as const;

export type UiKey = keyof (typeof ui)['pt'];

export function t(lang: Lang, key: UiKey): string {
  const value = (ui[lang] as Record<string, string>)[key];
  if (value === undefined) throw new Error(`ui: missing "${key}" for ${lang}`);
  return value;
}

/** Export verdict codes (ADR 0008) and readings of the 2026 audit -> label and chip style. */
export type Chip = 'myth' | 'truth' | 'edge' | 'neutral';

const VERDICT: Record<string, { pt: string; en: string; chip: Chip }> = {
  myth: { pt: 'Mito', en: 'Myth', chip: 'myth' },
  true: { pt: 'Verdade', en: 'True', chip: 'truth' },
  true_borderline: { pt: 'Verdade, no limite', en: 'True, borderline', chip: 'edge' },
  partly_true: { pt: 'Verdade em parte', en: 'Partly true', chip: 'edge' },
  undecided: { pt: 'Não dá para dizer', en: "Can't tell", chip: 'neutral' },
  outside: { pt: 'Novidade de 2026', en: 'New in 2026', chip: 'truth' },
  edge: { pt: 'No limite do acaso', en: 'At the edge of chance', chip: 'edge' },
  inside: { pt: 'Dentro do normal', en: 'Within the usual', chip: 'neutral' },
};

export function verdict(code: string, lang: Lang): { label: string; chip: Chip } {
  const v = VERDICT[code];
  if (!v) throw new Error(`verdict: unknown code "${code}"`);
  return { label: v[lang], chip: v.chip };
}
