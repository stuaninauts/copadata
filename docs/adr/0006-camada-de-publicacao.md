# Camada de publicação: agregados e export no pacote, dados versionados sob CC-BY-SA

Os achados vão ser publicados na web ([ADR 0007](./0007-site-web.md)). Hoje as métricas por partida vivem em `copadata/metrics.py`, mas as **agregações** que viram achado (taxas por era e por fase, faixa histórica por Copa, o teste único do H1) estão dentro de um notebook privado. Publicar a partir dali criaria uma terceira implementação dos números, fora dos testes.

Decidimos criar uma camada de publicação dentro do pacote:

- **`copadata/aggregate.py`:** as agregações que sustentam os achados, saídas dos notebooks. Cada uma tem teste "golden" que reproduz o número publicado (ex.: 11/31 e 37/150 no último quarto do mata-mata). Os notebooks passam a importar essas funções em vez de recalcular.
- **`copadata/export.py`:** gera as tabelas pré-computadas que o site consome. JSON para as páginas; CSV e Parquet para download; um `manifest.json` com versão do schema, commits das fontes, data de geração e licença. Formato principal "longo" (`metric, scope, stage, lens, k, n, value`) mais tabelas pequenas por gráfico.
- **O navegador só filtra e desenha.** Nenhuma taxa, média ou corte (último quarto, gol tardio) é recalculado em JavaScript. Continua valendo o [ADR 0003](./0003-pipeline-modulos-notebooks-so-analisam.md): métrica se define em um lugar só.

**Dados versionados.** O export é commitado no repositório (é pequeno e revisável em PR), em pastas próprias sob **CC-BY-SA 4.0**, com a atribuição exigida pelo [ADR 0005](./0005-fonte-historica-fjelstul.md). O código continua MIT. A separação de licenças por pasta segue o padrão [REUSE](https://reuse.software/) (`LICENSES/` + `REUSE.toml`). O CI roda `export --check`, que falha se o export commitado divergir do que o pipeline gera.

**Commit fixo do OpenFootball.** A Copa 2026 terminou em 2026-07-19. Para o export ser reprodutível, o download de 2026 passa a apontar para um commit fixo do `worldcup.json`, como já é feito com o Fjelstul. Isso supera o uso da branch `master` do [ADR 0004](./0004-fonte-openfootball.md).

**Conteúdo curado.** O que vai para o público é uma peça escrita para o leitor, não o caderno de trabalho:
- `questions.yaml`, neutro de idioma: id, status (`answered`, `partial`, `pending`, `idea`), estatísticas citadas, gráfico, ressalva, se o achado se repete no histórico e links para método e ADRs.
- Um texto por pergunta em EN e PT. Os números entram por referência ao export, nunca digitados, então os dois idiomas não divergem e o texto não envelhece quando o pipeline muda.
- `notas/` (ACHADOS, ROADMAP, notebooks) continua privado, como rascunho de trabalho. O ACHADOS é a matéria-prima do primeiro `questions.yaml`.
- Um teste garante que toda estatística citada no conteúdo existe no export.

**Incerteza, conforme o [ADR 0002](./0002-analise-descritiva-nao-inferencial.md).** Toda estatística publicada carrega `k/n`. Comparações históricas mostram a faixa entre Copas (mínimo e máximo). P-valor aparece só nos testes únicos de afirmação externa (o meme das africanas e o H1). Não há intervalo de confiança por célula, porque convidaria a comparar tudo com tudo.

## Considered Options

- **Publicar os notebooks:** repetem agregações que deveriam estar no pacote, guardam números de snapshots antigos nas saídas e não são bilíngues. Rejeitada no v1; um notebook "reproduza você mesmo" que lê só o export público pode vir depois.
- **Publicar o ACHADOS como está:** números digitados à mão, só em PT, com referências internas. Rejeitada.
- **Gerar o export no build do site, sem versionar:** o build passaria a depender de Python e de baixar as fontes a cada deploy. Rejeitada: commitar deixa o build só com Node e torna toda mudança de número visível no diff do PR.

## Consequences

- O convênio "não versionar dados derivados do Fjelstul sem a mesma licença" passa a ter um lugar certo: as pastas de export, sob CC-BY-SA.
- Mudar uma definição de métrica passa a mexer em `metrics.py`, teste, `aggregate.py`, export e, se for o caso, texto, tudo no mesmo PR. O `export --check` impede que alguma parte fique para trás.
- O commit do OpenFootball fixado em `config.py` só muda por decisão explícita, como o do Fjelstul.
- Escrever cada pergunta em dois idiomas custa mais conteúdo; o custo fica no texto, não nos números.
