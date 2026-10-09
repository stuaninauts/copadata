#!/usr/bin/env python3
"""PreToolUse hook (Bash): git guardrails for Claude Code (GitHub Flow: work on branches, PR to main).

deny -> commands that lose work (reset --hard, clean -f, checkout/restore ., force push),
        skipping git hooks (--no-verify), and commit/push on or to main.
ask  -> git commit, git push and git branch -D always need the user's approval, even in auto mode.

Matches git only at the start of a (sub)command and ignores heredoc bodies (data, not
commands), so "git push" inside an echo, a commit message or a file being written doesn't
trigger. A heredoc fed to a shell (bash <<EOF) is still inspected.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

SP = r"[ \t]"
START = r"(?:^|[;&|(`]|\$\()" + SP + "*"
# git plus any global options before the subcommand (-C <dir>, -c <k=v>, --no-pager, ...)
GIT = r"git(?:" + SP + r"+(?:-[Cc]" + SP + r"+\S+|--?[a-zA-Z][-a-zA-Z]*(?:=\S+)?))*" + SP + "+"
ARGS = r"(?:[^;&|\n]*" + SP + ")?"
END = r"(?=[ \t]|$)"

DENY = [
    rf"reset{SP}+{ARGS}--hard{END}",
    rf"clean{SP}+{ARGS}-[a-zA-Z]*f[a-zA-Z]*{END}",
    rf"(?:checkout|restore){SP}+(?:--{SP}+)?\.{END}",
    rf"push{SP}+{ARGS}(?:--force(?:-with-lease)?|-f){END}",
    rf"push{SP}+{ARGS}\+\S+",
    rf"(?:commit|push|merge|rebase){SP}+{ARGS}--no-verify{END}",
    rf"commit{SP}+{ARGS}-[aqsvSe]*n[aqsvmSe]*{END}",
    rf"push{SP}+{ARGS}(?:\S*:)?main{END}",
]
ASK = [
    rf"commit{END}",
    rf"push{END}",
    rf"branch{SP}+{ARGS}(?:-D|--delete{SP}+--force|--force{SP}+--delete){END}",
]

HEREDOC = re.compile(r"<<-?" + SP + r"*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
SHELL_BEFORE = re.compile(r"\b(?:ba|z|da)?sh(?:" + SP + r"+-\S+)*" + SP + r"*$")


def strip_heredoc_bodies(command: str) -> str:
    out, delim = [], None
    for line in command.split("\n"):
        if delim is not None:
            if line.strip() == delim:
                delim = None
            out.append("")
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m and not SHELL_BEFORE.search(line[: m.start()]):
            delim = m.group(2)
    return "\n".join(out)


def matches(pattern: str, command: str) -> bool:
    return re.search(START + GIT + pattern, command, re.MULTILINE) is not None


def current_branch(cwd: str) -> str:
    res = subprocess.run(
        ["git", "-C", cwd or ".", "symbolic-ref", "--quiet", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    return res.stdout.strip()


def decide(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def main() -> None:
    data = json.load(sys.stdin)
    command = strip_heredoc_bodies((data.get("tool_input") or {}).get("command") or "")

    if any(matches(p, command) for p in DENY):
        decide("deny", "BLOCKED by .claude/hooks/git-guardrails.py: destructive git command, skipped git hooks, "
                       "or push to main. Work on a branch and open a PR; ask the user to run it themselves if needed.")

    # GitHub Flow: no commit/push while the current branch is main.
    if matches(rf"(?:commit|push){END}", command) and current_branch(data.get("cwd", "")) == "main":
        decide("deny", "BLOCKED: the current branch is main. Create a branch first (/start-branch, or "
                       "'git switch -c <type>/<desc>' as a separate command), then commit.")

    if any(matches(p, command) for p in ASK):
        decide("ask", "git commit/push/branch -D need explicit user approval (project rule).")


if __name__ == "__main__":
    main()
