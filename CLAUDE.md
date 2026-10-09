# CopaData

Engine de análise da Copa do Mundo (2026 + histórico) sobre dados públicos, sem API key.

## Comandos
- `python -m copadata.pipeline`: baixa e reprocessa (`--offline` reprocessa o snapshot já baixado).
- `python -m pytest`: testes. Rodar depois de mexer em `copadata/`.

## Convenções
- Código, nomes de colunas e docstrings em **inglês**; documentação (`docs/adr/`) em **português**.
- `copadata/metrics.py` é o **único** lugar onde se define métrica. `transform`/`derive` só consomem; notebooks só leem `data/processed/` (ADR 0003). Toda mudança de definição vem com teste em `tests/test_metrics.py`.
- Análise é descritiva: `n` sempre visível, sem bateria de testes de hipótese (ADR 0002).
- Decisão de arquitetura nova vira ADR em `docs/adr/` (numeração sequencial, superar em vez de apagar).
- `data/` é gerado pelo pipeline e não é versionado.

## Git (GitHub Flow)
- Todo trabalho numa branch `<tipo>/<descricao-kebab>` saída da `main`, que volta por PR (merge: rebase). Nunca commitar na `main`.
- Fluxo pelas skills: `/start-branch` (com `--worktree` para trabalho isolado em `.claude/worktrees/`) → `/commit` → `/open-pr` → `/finish-branch`.
- Commits lógicos (um propósito cada) em Conventional Commits: `tipo(escopo): descrição` em minúscula, sem corpo, só o trailer `Co-Authored-By`. Detalhes na skill `commit`.
- Nunca commitar nem dar push sem pedido explícito. Guardrails: `.claude/hooks/git-guardrails.py` (pede aprovação para commit/push, bloqueia comandos destrutivos e commit na `main`) e `.githooks/commit-msg` (formato da mensagem; ativar com `git config core.hooksPath .githooks`).
- `gh` está em outra conta: PR é aberto no navegador pelo link que `/open-pr` gera.
- Não usar travessão longo (em dash) em textos, docs, commits ou comentários.
