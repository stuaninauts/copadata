# Site web: Astro estático em copa.stuaninauts.com, código em `web/`

O CopaData vai ser publicado como peça de portfólio técnico, bilíngue (EN e PT), mostrando os dados e as perguntas levantadas e respondidas. O site pessoal (stuaninauts.com) já é Astro estático na Cloudflare, com i18n EN/PT e CSP estrita por hashes. Os projetos anteriores com demo própria (enem, fipe) eram apps Shiny com servidor, e a versão hospedada do Fipe já foi desativada: para portfólio de longa duração, servidor que morre leva a demo junto.

Decidimos fazer um **site Astro estático em `copa.stuaninauts.com`**, com o código em **`web/` dentro deste repositório**:

- **Monorepo.** Um PR pode mudar métrica, teste, export ([ADR 0006](./0006-camada-de-publicacao.md)), gráfico e texto juntos. Não há sincronização entre repositórios.
- **Hosting:** um segundo Worker com static assets na Cloudflare, custom domain `copa.stuaninauts.com`, deploy por Workers Builds (root `web/`, watch paths `web/*`) a cada merge na `main`, preview por branch. Custo zero no plano free.
- **Stack:** Astro na mesma major do site principal, TypeScript, sem framework de UI. Mesmo i18n (EN na raiz, PT em `/pt`), mesmos tokens de tema e fontes self-hosted, sem CDN externa.
- **Gráficos:** Observable Plot, renderizado no build como SVG estático e hidratado só onde há interação. O tema vem das CSS variables do site. O `<style>` que o Plot injeta entra na CSP por hash.
- **Formato único, guiado por perguntas.** Não há artigo separado do dashboard. Cada pergunta tem página própria: status, resposta, `k/n`, ressalva, "se repete no histórico?" e abas Gráfico, Tabela, Método e Download. O "Explorar" reaproveita os mesmos dados e gráficos.
- **Rotas:** `/` (gancho e manchetes), `/questions/` e `/questions/<id>/`, `/explore/`, `/method/` (pipeline, glossário, definições ligadas ao código, ADRs, correções públicas) e `/data/` (downloads, licença, atribuição, commit dos dados).
- **Explorar sem p-hacking ([ADR 0002](./0002-analise-descritiva-nao-inferencial.md)):** todo número mostra `k/n`, célula com `n < 10` aparece esmaecida com selo de amostra pequena, comparação por era e não por Copa isolada, estado dos filtros na URL.
- **Licença do conteúdo:** texto, gráficos e dados do subdomínio sob CC-BY-SA 4.0, com o rodapé "Fonte: Fjelstul World Cup Database (CC-BY-SA 4.0); OpenFootball (CC0)" em toda página. Código MIT.
- **Integração com o site principal:** um card de projeto no stuaninauts.com, em EN e PT, apontando para o subdomínio.

**Fora do v1:**
- **Scrollytelling** (custo alto em mobile, acessibilidade e dois idiomas). Fica para v2, e só se a transição contar algo.
- **Visões por seleção** (nomes, bandeiras), que dependem do mapeamento de nomes entre fontes do ADR 0005.
- **Analytics** (beacon externo conflita com a CSP).
- **Perguntas em linguagem natural com LLM.** O custo em tokens é baixo; o problema é risco (abuso, conta, alucinação) e responder qualquer recorte sem `n`, o oposto do ADR 0002. No lugar, um link "sugira uma pergunta" para as Issues do repositório. Se entrar um dia, será busca restrita sobre as perguntas curadas, citando a pergunta e o `n`.

## Considered Options

- **Páginas dentro do site principal (`stuaninauts.com/copa`):** coerência visual de graça, mas acopla a publicação dos dados ao repositório do site e mistura conteúdo CC-BY-SA num repositório de outra licença. Plano B, de migração barata: os componentes e o contrato de dados são os mesmos.
- **App Python (Streamlit, Shiny, ou Shinylive/marimo em WASM):** com servidor repete o destino de enem e fipe (sono, cota, desativação); em WASM, vários MB antes do primeiro gráfico e i18n fraco. Rejeitada.
- **Claude Artifact público:** sem domínio próprio, rótulo de conteúdo não verificado para visitante anônimo, depende de CDN externa e de conta. Serve só para protótipo privado da arquitetura de informação. Rejeitada como peça pública.
- **Vega-Lite gerado por Altair** (gráfico definido em Python): bundle quase 4 vezes maior e CSP mais difícil (`unsafe-eval` sem o interpreter). Alternativa se o Plot não servir.
- **Observable Framework ou Evidence:** bom encaixe com loaders de dados, mas sem i18n nativo e com stack diferente do site.

## Consequences

- Dois projetos Astro para manter (site e `web/`), com tokens de design e configuração de CSP copiados. Divergência visual é o risco a vigiar.
- O repositório passa a ter Node (`web/package.json`) além de Python, e um CI no GitHub Actions: `pytest`, `export --check` e `npm run check && npm run build`.
- Merge na `main` publica o site: merges seguem a mesma regra de horário de qualquer ação no GitHub.
- Toda página nova existe nos dois idiomas; o build falha se um id de pergunta faltar em um deles.
- O card no site principal é uma mudança no outro repositório, feita depois que o subdomínio estiver no ar.
