---
name: open-pr
description: Publica a branch atual e prepara o PR para a main (título, descrição e link de compare para abrir no navegador).
disable-model-invocation: true
allowed-tools: Bash(git status *), Bash(git log *), Bash(git fetch *), Bash(git remote get-url *), Bash(git rev-list *), Bash(git diff *), Bash(python -m pytest *)
---

# Abrir PR para a main

Estado atual:
!`git status --short --branch`

O `gh` desta máquina está logado em outra conta, sem permissão neste repo: **não use `gh pr create`**. O usuário abre o PR no navegador.

## Passos
1. Pare se a branch for `main` ou se houver mudanças não commitadas (sugira a skill `commit`).
2. `python -m pytest -q`. Se falhar, pare.
3. `git fetch origin main` e veja se a branch está atrás (`git rev-list --count HEAD..origin/main`).
   - Atrás e ainda **não publicada**: `git rebase origin/main` e rode os testes de novo.
   - Atrás e **já publicada**: não faça rebase (exigiria force push, que é bloqueado). Avise o usuário.
4. Se a mudança for grande, sugira rodar `/code-review` antes de publicar.
5. `git push -u origin <branch>` (o hook pede aprovação).
6. Monte o link a partir de `git remote get-url origin`: `https://github.com/<owner>/<repo>/compare/main...<branch>?expand=1`.
7. Entregue ao usuário, prontos para colar:
   - **Título:** a mensagem do commit, se houver um só; senão, um resumo no mesmo formato Conventional Commits.
   - **Descrição:**
     ```markdown
     ## Resumo
     - <o que muda e por quê, 1-3 itens>

     ## Commits
     - `<sha curto>` <mensagem>

     ## Como verificar
     - `python -m pytest`

     ## Decisões
     - <ADRs criados/alterados em docs/adr/, ou "nenhuma">

     🤖 Generated with [Claude Code](https://claude.com/claude-code)
     ```
8. Lembre: fazer o merge com **Rebase and merge**.
