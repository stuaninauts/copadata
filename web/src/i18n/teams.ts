/** Team names as the export writes them (English, Fjelstul spelling) -> Portuguese. */
const PT: Record<string, string> = {
  Algeria: 'Argélia', Argentina: 'Argentina', Australia: 'Austrália', Austria: 'Áustria', Belgium: 'Bélgica',
  Brazil: 'Brasil', Bulgaria: 'Bulgária', Cameroon: 'Camarões', Canada: 'Canadá', Chile: 'Chile',
  Colombia: 'Colômbia', 'Costa Rica': 'Costa Rica', Croatia: 'Croácia', Denmark: 'Dinamarca', Ecuador: 'Equador',
  Egypt: 'Egito', England: 'Inglaterra', France: 'França', Germany: 'Alemanha', Ghana: 'Gana', Greece: 'Grécia',
  Iran: 'Irã', Italy: 'Itália', 'Ivory Coast': 'Costa do Marfim', Japan: 'Japão', Mexico: 'México',
  Morocco: 'Marrocos', Netherlands: 'Holanda', Nigeria: 'Nigéria', Norway: 'Noruega', Paraguay: 'Paraguai',
  Poland: 'Polônia', Portugal: 'Portugal', Qatar: 'Catar', 'Republic of Ireland': 'Irlanda', Romania: 'Romênia',
  Russia: 'Rússia', 'Saudi Arabia': 'Arábia Saudita', Scotland: 'Escócia', Senegal: 'Senegal',
  'South Africa': 'África do Sul', 'South Korea': 'Coreia do Sul', Spain: 'Espanha', Sweden: 'Suécia',
  Switzerland: 'Suíça', Tunisia: 'Tunísia', 'United States': 'Estados Unidos', Uruguay: 'Uruguai',
  'West Germany': 'Alemanha Ocidental',
};

export function teamName(name: string, lang: 'pt' | 'en'): string {
  if (lang === 'en') return name;
  const pt = PT[name];
  if (!pt) throw new Error(`teams: no Portuguese name for "${name}"`);
  return pt;
}
