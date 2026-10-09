"""Tests for the git guardrails: the Claude Code PreToolUse hook and the git commit-msg hook."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARDRAILS = ROOT / ".claude" / "hooks" / "git-guardrails.py"
COMMIT_MSG = ROOT / ".githooks" / "commit-msg"

@pytest.fixture(scope="module")
def repos(tmp_path_factory):
    """Two throwaway repos: one on main, one on a feature branch."""
    out = {}
    for name, branch in (("on_main", "main"), ("on_feature", "feat/x")):
        d = tmp_path_factory.mktemp(name)
        git = ["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "init"], check=True)
        if branch != "main":
            subprocess.run(git + ["switch", "-q", "-c", branch], check=True)
        out[name] = d
    return out


def decision(command: str, cwd: Path) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)})
    res = subprocess.run([sys.executable, str(GUARDRAILS)], input=payload, capture_output=True, text=True, check=True)
    if not res.stdout.strip():
        return "none"
    return json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~1",
        "cd x && git reset --hard origin/main",
        "git clean -fd",
        "git clean -xdf",
        "git checkout .",
        "git restore -- .",
        "git push --force origin feat/x",
        "git push -f",
        "git push origin +feat/x",
        "git -C . push --force-with-lease",
        "bash <<'EOF'\ngit push --force\nEOF",  # heredoc run by a shell is inspected
        "git commit --no-verify -m 'fix: x'",
        "git commit -n -m 'fix: x'",
        "git commit -anm 'fix: x'",
        "git push --no-verify",
        "git push origin main",
        "git push -u origin HEAD:main",
    ],
)
def test_guardrails_deny(command, repos):
    assert decision(command, repos["on_feature"]) == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'fix: x'",
        "git -c user.name=x commit -m 'fix: y'",
        "git add . && git commit -m \"$(cat <<'EOF'\nfix: algo\n\nCo-Authored-By: x <y@z>\nEOF\n)\"",
        "git push",
        "git push -u origin feat/x",
        "git push origin feat/main-thing",  # not main: ask, not deny
        "git -C /x push",
        "git branch -D feat/old",
        "git branch --delete --force feat/old",
    ],
)
def test_guardrails_ask(command, repos):
    assert decision(command, repos["on_feature"]) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git log --oneline",
        "git diff --stat",
        "git reset HEAD file.py",
        "git switch -c feat/nova",
        "git restore --staged copadata/x.py",
        "git branch -d merged",
        "echo 'nunca rode git push --force'",
        "grep -rn 'git commit' docs/",
        "git log --grep=commit",
        "git commit-graph verify",
        "python -m copadata.pipeline",
        # heredoc bodies are data, not commands
        "cat > SKILL.md <<'EOF'\n`git push -u origin x`\ngit reset --hard\nEOF",
        "python3 - <<'EOF'\nprint('git push --force')\nEOF\necho done",
    ],
)
def test_guardrails_allow(command, repos):
    assert decision(command, repos["on_feature"]) == "none"


@pytest.mark.parametrize("command", ["git commit -m 'fix: x'", "git push", "git push -u origin HEAD"])
def test_guardrails_block_commit_and_push_on_main(command, repos):
    assert decision(command, repos["on_main"]) == "deny"


def test_guardrails_allow_branching_off_main(repos):
    assert decision("git switch -c feat/nova", repos["on_main"]) == "none"


# --- commit-msg ---------------------------------------------------------------------

def commit_msg_ok(message: str, tmp_path: Path) -> bool:
    f = tmp_path / "COMMIT_EDITMSG"
    f.write_text(message)
    return subprocess.run([str(COMMIT_MSG), str(f)], capture_output=True).returncode == 0


@pytest.mark.parametrize(
    "message",
    [
        "feat(ingest): add fjelstul adapter\n",
        "fix: handle 90+ minutes\n",
        "docs(adr): add 0005 historical source",
        "chore(claude): add git guardrails\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n",
        "refactor!: rename columns\n",
        "test(metrics): cover survival goal\n# a comment line\n",
        "Merge branch 'feat/x'\n",
        'Revert "feat: x"\n\nThis reverts commit abc.\n',
        "fixup! feat: x\n",
    ],
)
def test_commit_msg_accepts(message, tmp_path):
    assert commit_msg_ok(message, tmp_path)


@pytest.mark.parametrize(
    "message",
    [
        "add tests\n",  # no type
        "Feat: add tests\n",  # uppercase type
        "feat: Add tests\n",  # uppercase description
        "feat(Ingest): add x\n",  # uppercase scope
        "feature: add x\n",  # unknown type
        "feat: add x.\n",  # trailing period
        "feat: add x \u2014 and y\n",  # em dash
        "feat: " + "x" * 70 + "\n",  # too long
        "feat: add x\n\nthis body explains why\n",  # body not allowed
    ],
)
def test_commit_msg_rejects(message, tmp_path):
    assert not commit_msg_ok(message, tmp_path)
