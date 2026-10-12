# CopaData

Engine de análise da Copa do Mundo (2026 + histórico) sobre dados públicos, sem API key.

## Comandos
- `python -m copadata.pipeline`: baixa e reprocessa (`--offline` reprocessa o snapshot já baixado).
- `python -m copadata.export`: regrava o export público em `web/public/data/` (`--check` só confere se está em dia).
- `python -m pytest`: testes. Rodar depois de mexer em `copadata/`.
- Site (`web/`, Node da `web/.node-version`): `npm run check && npm run build`; `npm run preview` serve o `dist/`. A CSP só existe no build: valide nele, nunca só no `dev`.

## Convenções
- Código, nomes de colunas e docstrings em **inglês**; documentação (`docs/adr/`) em **português**.
- `copadata/metrics.py` é o **único** lugar onde se define métrica. `transform`/`derive` só consomem; notebooks só leem `data/processed/` (ADR 0003). Toda mudança de definição vem com teste em `tests/test_metrics.py`.
- Agregações que viram achado (taxas e médias por edição, era, fase, sempre com `k` e `n`) ficam em `copadata/aggregate.py` (ADR 0006), não em notebook. Os testes golden em `tests/test_aggregate.py` reproduzem os números publicados: número que muda, teste que muda junto.
- Análise é descritiva: `n` sempre visível, sem bateria de testes de hipótese (ADR 0002).
- Mitos (ADR 0008): lista fechada por leva, com medida e limiar escritos antes de rodar; são a única parte com intervalo e faixa do acaso. Pergunta nova é leva nova, nunca entra numa leva já rodada.
- Decisão de arquitetura nova vira ADR em `docs/adr/` (numeração sequencial, superar em vez de apagar).
- `data/` é gerado pelo pipeline e não é versionado.
- Os parquets têm **todas as edições** (coluna `year`, 1986-2026): análise de uma Copa só precisa filtrar `year`.
- Força das seleções é o Elo de `copadata/elo.py` (ADR 0009), calculado da base CC0 de resultados internacionais; nenhum outro lugar define força. Nome de seleção é um só entre as fontes (`config.TEAM_NAMES`).
- Dados de 1986-2022 vêm do Fjelstul (CC-BY-SA 4.0, ADR 0005): gráfico ou post que os use leva "Fonte: Fjelstul World Cup Database (CC-BY-SA 4.0)". Dado derivado dele só é versionado em `web/public/data/`, que é CC-BY-SA (`REUSE.toml`).
- Site (ADR 0007, 0010): textos em `web/src/content/*.yaml`, números só por referência ao export (`{nome}` + `stats`), nunca digitados; nenhuma taxa calculada em JavaScript. Sem estilo ou script inline (CSP estrita): cor e tamanho por classe CSS; o `<style>` que o Plot gera é removido em `web/src/lib/charts.ts`.
- O export (`web/public/data/`) é commitado e gerado só por `copadata/export.py`, nunca editado à mão. Mudou métrica ou agregado: rode `python -m copadata.export` e commite junto; `tests/test_export.py` falha se ele estiver desatualizado.

## Git (GitHub Flow)
- Todo trabalho numa branch `<tipo>/<descricao-kebab>` saída da `main`, que volta por PR (merge: rebase). Nunca commitar na `main`.
- Fluxo pelas skills: `/start-branch` (com `--worktree` para trabalho isolado em `.claude/worktrees/`) → `/commit` → `/open-pr` → `/finish-branch`.
- Commits lógicos (um propósito cada) em Conventional Commits: `tipo(escopo): descrição` em minúscula, sem corpo, só o trailer `Co-Authored-By`. Detalhes na skill `commit`.
- Nunca commitar nem dar push sem pedido explícito. Guardrails: `.claude/hooks/git-guardrails.py` (pede aprovação para commit/push, bloqueia comandos destrutivos e commit na `main`) e `.githooks/commit-msg` (formato da mensagem; ativar com `git config core.hooksPath .githooks`).
- `gh` está em outra conta: PR é aberto no navegador pelo link que `/open-pr` gera.
- Não usar travessão longo (em dash) em textos, docs, commits ou comentários.
