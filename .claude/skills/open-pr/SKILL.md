---
name: open-pr
description: Publica a branch atual e abre no navegador o formulário de PR para a main, já com título e descrição preenchidos.
disable-model-invocation: true
allowed-tools: Bash(git status *), Bash(git log *), Bash(git fetch *), Bash(git remote get-url *), Bash(git rev-list *), Bash(git diff *), Bash(python -m pytest *), Bash(xdg-open *)
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
6. Escreva o título e a descrição (formatos abaixo). Grave a descrição num arquivo no scratchpad.
7. Gere o link **já preenchido** e abra no navegador do usuário. O GitHub aceita `title` e `body` na URL de compare:
   ```bash
   python3 -c "import sys, urllib.parse as u; print('https://github.com/<owner>/<repo>/compare/main...<branch>?' + u.urlencode({'expand': 1, 'title': sys.argv[1], 'body': open(sys.argv[2]).read()}, quote_via=u.quote))" "<titulo>" <arquivo-da-descricao> > <arquivo-da-url>
   xdg-open "$(cat <arquivo-da-url>)"
   ```
   `<owner>/<repo>` vem de `git remote get-url origin`. Se o `xdg-open` falhar, entregue a URL ao usuário.
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
8. O usuário só confere e clica em **Create pull request**. Lembre: o merge é com **Rebase and merge**.
