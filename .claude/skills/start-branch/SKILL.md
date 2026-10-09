---
name: start-branch
description: Cria uma branch (ou worktree) a partir da main no padrão <tipo>/<descricao>. Use ao começar qualquer trabalho novo neste repo, antes do primeiro commit.
argument-hint: <tipo> <descricao-kebab> [--worktree]
allowed-tools: Bash(git fetch *), Bash(git switch *), Bash(git status *), Bash(git branch -m *), Bash(git rev-parse *), Bash(python -m pytest *)
---

# Começar trabalho numa branch (GitHub Flow)

Estado atual:
!`git status --short --branch`

## Nome da branch
`<tipo>/<descricao>`
- `tipo`: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore` (os mesmos tipos dos commits).
- `descricao`: kebab-case, só `[a-z0-9-]`, até 40 caracteres, em inglês. Ex.: `feat/historical-ingest`, `docs/adr-0005-fjelstul`.

Argumentos recebidos: `$ARGUMENTS`. Se faltar tipo ou descrição, deduza do pedido do usuário e confirme o nome antes de criar.

## Passos
1. `git fetch origin main`.
2. **Sem `--worktree`:**
   - Árvore limpa: `git switch --no-track -c <tipo>/<desc> origin/main`.
   - Há mudanças não commitadas que pertencem a este trabalho e `HEAD` está em `origin/main` (`git rev-parse HEAD origin/main` iguais): `git switch -c <tipo>/<desc>` (leva as mudanças junto).
   - Qualquer outro caso: pare e pergunte ao usuário.
3. **Com `--worktree`:**
   - Use a ferramenta `EnterWorktree` com `name: <tipo>-<desc>`. Ela cria em `.claude/worktrees/`, a partir de `origin/main`, e copia os arquivos do `.worktreeinclude` (dados brutos, `notas/`, `CLAUDE.local.md`).
   - Dentro da worktree: `git branch -m <tipo>/<desc>` para seguir o padrão de nome.
   - Rode `python -m pytest -q` para confirmar que o ambiente funciona.
4. Informe a branch criada (e o caminho da worktree, se houver).

Nunca commite na `main`: o hook `.claude/hooks/git-guardrails.py` bloqueia.
