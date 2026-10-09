---
name: finish-branch
description: Depois que o PR foi mergeado na main, atualiza a main, remove a worktree e apaga a branch local e remota.
disable-model-invocation: true
argument-hint: [branch]
allowed-tools: Bash(git fetch *), Bash(git cherry *), Bash(git switch main), Bash(git pull --ff-only), Bash(git worktree list), Bash(git worktree remove *), Bash(git ls-remote *), Bash(git status *)
---

# Encerrar uma branch mergeada

Branch: `$ARGUMENTS` (se vazio, a branch atual). Nunca `main`.

## Passos
1. `git fetch origin --prune`.
2. **Confirme que foi mergeada:** `git cherry origin/main <branch>`. O merge é por rebase, então os SHAs mudam; o `cherry` compara o conteúdo dos patches.
   - Todas as linhas começam com `-`: mergeada.
   - Alguma começa com `+`: pare e mostre ao usuário quais commits não estão na `main`.
3. **Worktree:**
   - Se a sessão está numa worktree criada pela `start-branch`, use `ExitWorktree` com `action: "remove"`. Se ela recusar por causa de commits fora da branch original (esperado com rebase merge), mostre o resultado do `cherry` e peça confirmação ao usuário antes de repetir com `discard_changes: true`.
   - Se a worktree é de outra sessão: `git worktree remove .claude/worktrees/<nome>` (sem `--force`).
4. No checkout principal: `git switch main` e `git pull --ff-only`.
5. `git branch -D <branch>`. O `-D` é necessário porque o rebase merge muda os SHAs; o hook pede aprovação.
6. Se a branch remota ainda existir (`git ls-remote --heads origin <branch>`), `git push origin --delete <branch>` (o hook pede aprovação).
