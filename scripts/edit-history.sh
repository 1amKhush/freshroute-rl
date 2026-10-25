#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/edit-history.sh --preview
  bash scripts/edit-history.sh --edit NEW_BRANCH WORKTREE_DIRECTORY

Preview the current checkout's commits, or edit them with Git's interactive
rebase in a new branch and worktree. Relative paths use the repository root.
The original branch and working files stay intact. Nothing is pushed.
EOF
}

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

case "${1:---preview}" in
  --preview)
    if (( $# > 1 )); then usage; exit 2; fi
    git log --reverse --date=iso-strict --format='%h  %ad  %an%n    %s' HEAD
    ;;
  --edit)
    if (( $# != 3 )); then usage; exit 2; fi
    branch=$2
    worktree=$3
    git worktree add -b "$branch" -- "$worktree" HEAD
    if git -C "$worktree" rebase --interactive --root; then
      printf '\nEdited history is on branch %s. Review before publishing:\n' "$branch"
      printf '  git -C %q log --reverse --oneline\n' "$worktree"
      printf '  git diff HEAD %q\n' "$branch"
    else
      printf '\nThe separate worktree is available for inspection:\n' >&2
      printf '  git -C %q status\n' "$worktree" >&2
      printf 'Resolve conflicts, then continue; or abort the rebase:\n' >&2
      printf '  git -C %q rebase --continue\n' "$worktree" >&2
      printf '  git -C %q rebase --abort\n' "$worktree" >&2
      exit 1
    fi
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
