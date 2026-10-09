---
name: commit
description: Organiza as mudanças em commits lógicos no padrão Conventional Commits do projeto e commita. Use sempre que for commitar neste repo ("commita", "faz o commit", "salva isso no git").
allowed-tools: Bash(git status *), Bash(git diff *), Bash(git add *), Bash(git log *), Bash(git apply --cached *), Bash(python -m pytest *)
---

# Commits lógicos

Estado atual:
!`git status --short --branch`
!`git log --oneline -5`

## Regras
- **Nunca na `main`.** Se a branch atual for `main`, siga a skill `start-branch` antes.
- **Um propósito por commit.** Separe por intenção, não por arquivo: uma feature, uma correção, um ADR, uma mudança de configuração.
  - Teste vai junto do código que ele testa.
  - ADR vai num commit `docs(adr): ...` próprio, antes do código que o implementa.
  - Ordene para que cada commit faça sentido sozinho e os testes passem no estado final.
- **Mensagem** (validada pelo hook `.githooks/commit-msg`):
  - `<tipo>(<escopo>): <descrição>`, tudo em minúscula, imperativo, em inglês, até 72 caracteres, sem ponto final, sem travessão longo.
  - Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `build`, `ci`, `style`, `revert`.
  - Escopos (opcional): `ingest`, `transform`, `derive`, `metrics`, `pipeline`, `adr`, `claude`, `git`, `deps`, `readme`.
  - Sem corpo. Só uma linha em branco e o trailer `Co-Authored-By:` do modelo atual (o da instrução de atribuição da sessão).
- **Nunca** use `--no-verify`, `-n` ou `--amend` em commit já publicado. Se o hook `commit-msg` recusar, corrija a mensagem.
- Não adicione `data/`, `notas/`, `CLAUDE.local.md` nem segredos.

## Passos
1. Leia `git diff` e `git diff --cached` e monte o plano: uma tabela `mensagem ← arquivos`. Mostre ao usuário.
2. Rode `python -m pytest -q`. Se falhar, pare e reporte.
3. Para cada commit do plano:
   - `git add <arquivos>`. Se um arquivo mistura intenções, gere um patch só com os hunks do commit (no scratchpad) e use `git apply --cached <patch>`.
   - Commite com heredoc:
     ```bash
     git commit -m "$(cat <<'MSG'
     feat(ingest): add fjelstul historical adapter

     Co-Authored-By: <linha de atribuição da sessão>
     MSG
     )"
     ```
   - O hook pede a aprovação do usuário em cada commit.
4. No fim, mostre `git log --oneline origin/main..HEAD`.
