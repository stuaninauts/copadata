# Estrutura do site: duas séries, URLs por idioma e conteúdo por série

O protótipo da v2 foi aprovado em 2026-10-12. Ele muda o que o [ADR 0007](./0007-site-web.md) previa: o site deixa de ser um índice de "perguntas" com abas (Gráfico, Tabela, Método, Download) e passa a ser editorial. Abre com uma lista de frases de torcedor conferidas e mostra cada achado como uma página curta, com veredito, um gráfico, três números e o método recolhido. Os mitos vêm do [ADR 0008](./0008-mitos-lista-fechada.md).

Decidimos:

- **Duas séries, lidas em sequência:**
  - **Mitos:** as 7 frases publicadas, primeiro os mitos e depois as verdades;
  - **O que 2026 teve de diferente:** as 3 manchetes da auditoria de 2026 (`season_outlier`).

  Cada item tem página própria. Explorar e Método são áreas de consulta, fora das séries.
- **URLs no idioma da página.** Português na raiz, inglês em `/en/`, cada item com um slug por idioma:
  - em PT: `/`, `/mitos/<slug>/`, `/2026/<slug>/`, `/explorar/`, `/metodo/`;
  - em EN: `/en/`, `/en/myths/<slug>/`, `/en/2026/<slug>/`, `/en/explore/`, `/en/method/`.

  Cada página aponta para a sua versão no outro idioma (`hreflang`). Isso supera as rotas do ADR 0007 (`/questions/`, EN na raiz e PT em `/pt`). O site pessoal continua com EN na raiz; aqui o público principal é brasileiro e o link compartilhado deve ser legível em português.
- **Navegação igual em toda página**, como no protótipo:
  - menu fixo (Mitos, 2026, Explorar, Método, idioma), com a seção atual marcada;
  - nas páginas de item, a faixa "Você está em", com o caminho, a posição ("Mito 1 de 7") e Anterior/Próximo;
  - no fim, dois cartões de Anterior/Próximo com o título do destino e a lista da série com o item atual marcado.

  O último item de uma série aponta para a série seguinte.
- **Página de item:**
  - no topo, a frase ou pergunta, um título que afirma e o veredito;
  - um gráfico;
  - "O que isso quer dizer", com três números;
  - "Como sabemos" recolhido: base, definição, regra, intervalo e link para o código.

  Tabela e download vão para a página de Método, que absorve a `/data/` do ADR 0007.
- **Veredito por código.** O export grava códigos e o site os traduz por idioma:
  - mitos (`verdict`): `myth`, `true`, `true_borderline`, `partly_true`, `undecided`;
  - auditoria de 2026 (`reading`): `outside`, `edge`, `inside`.

  A tradução fica em `web/src/i18n/`.
- **Conteúdo por série, números por referência.** O `questions.yaml` do [ADR 0006](./0006-camada-de-publicacao.md) vira um arquivo por série (`web/src/content/myths.yaml`, `web/src/content/novelties.yaml`). Cada item traz:
  - ordem, slugs e textos em PT e EN;
  - números como referências ao export (tabela, filtro, campo, formato), resolvidas no build.

  Uma referência que não resolve quebra o build. O build só seleciona e formata; nenhuma taxa é calculada em JavaScript.
- **Conteúdo sob CC-BY-SA.** Os textos em `web/src/content/` seguem a licença do conteúdo do site (ADR 0007), declarada no `REUSE.toml`.

Continuam valendo do ADR 0007: Astro estático na mesma major do site pessoal, Worker com static assets em `copa.stuaninauts.com`, gráficos do Observable Plot gerados no build, CSP estrita e o que ficou fora do v1.

## Considered Options

- **Grade de cartões na home:** testada no protótipo. A lista lê melhor: veredito, frase e número sempre na mesma coluna. Rejeitada.
- **URLs em inglês nos dois idiomas:** mais simples (um slug por item), mas o link em PT fica estrangeiro para quem mais compartilha. Rejeitada.
- **EN na raiz, como o site pessoal:** coerente com ele, mas contrário ao público. Rejeitada.
- **Manter as abas por pergunta:** densas para o público executivo; o método recolhido cumpre o papel sem competir com a resposta. Rejeitada.

## Consequences

- Cada item precisa de dois slugs e dos textos nos dois idiomas; o build falha se faltar um.
- O primeiro corte (spike) entrega só PT: Home, uma página de mito e uma da série de 2026. O EN entra antes do primeiro deploy.
- As séries têm ordem fixa no conteúdo. Mudar a ordem muda "n de N" e Anterior/Próximo, sem tocar em código.
