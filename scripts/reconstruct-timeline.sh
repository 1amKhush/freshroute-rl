#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/reconstruct-timeline.sh --preview
  bash scripts/reconstruct-timeline.sh --create demo/BRANCH_NAME

Build a labeled demonstration timeline from 20 real project snapshots.
Dates and the 12/8 author allocation are illustrative, not historical evidence.
The original branches, index, and working files are untouched. Nothing is pushed.
EOF
}

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mode=${1:---preview}
case "$mode" in
  --preview) if (( $# > 1 )); then usage; exit 2; fi ;;
  --create) if (( $# != 2 )); then usage; exit 2; fi ;;
  --help|-h) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

# Existing implementation snapshots, in their original dependency order.
plan=(
  'd5fea99|2026-10-15T18:20:00+05:30|Khush'
  'e4a3cfa|2026-10-15T21:35:00+05:30|Khush'
  '14c0ede|2026-10-16T17:45:00+05:30|Aditya'
  '3670783|2026-10-16T20:10:00+05:30|Khush'
  'e9db7cf|2026-10-17T16:30:00+05:30|Aditya'
  '34d16ac|2026-10-17T19:55:00+05:30|Khush'
  'b0eee4f|2026-10-18T14:15:00+05:30|Khush'
  '4a755e6|2026-10-18T18:40:00+05:30|Aditya'
  'efeac3b|2026-10-19T17:20:00+05:30|Khush'
  '5071ed0|2026-10-19T21:05:00+05:30|Aditya'
  '11375d3|2026-10-20T16:50:00+05:30|Khush'
  '49ab14c|2026-10-20T20:25:00+05:30|Khush'
  'beccee0|2026-10-21T18:10:00+05:30|Aditya'
  'a10aacc|2026-10-21T22:15:00+05:30|Khush'
  'e781067|2026-10-22T15:35:00+05:30|Aditya'
  '55170a8|2026-10-22T19:40:00+05:30|Khush'
  'ace896f|2026-10-23T17:55:00+05:30|Khush'
  '591c9b7|2026-10-23T21:20:00+05:30|Aditya'
  'bfb877e|2026-10-24T14:30:00+05:30|Khush'
  '90c054c|2026-10-24T18:45:00+05:30|Aditya'
)

# Check all source snapshots before creating any new objects or references.
for entry in "${plan[@]}"; do
  IFS='|' read -r source author_date contributor <<< "$entry"
  git rev-parse --verify "${source}^{commit}" > /dev/null
done

if [[ "$mode" == --create ]]; then
  branch=$2
  unset GIT_COMMITTER_DATE
  if [[ "$branch" != demo/* ]]; then
    printf 'Use a new branch under demo/, such as demo/oct15-24.\n' >&2
    exit 2
  fi
  git check-ref-format --branch "$branch" > /dev/null
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    printf 'Branch already exists: %s\n' "$branch" >&2
    exit 1
  fi
fi

printf 'RECONSTRUCTED DEMONSTRATION: illustrative dates and author assignments.\n'
printf '20 real snapshots; Khush 12 (60%%), Aditya 8 (40%%).\n\n'
parent=''
for entry in "${plan[@]}"; do
  IFS='|' read -r source author_date contributor <<< "$entry"
  subject=$(git show -s --format=%s "$source")
  printf '%s | %-6s | [reconstructed] %s\n' "$author_date" "$contributor" "$subject"
  if [[ "$mode" == --preview ]]; then continue; fi

  if [[ "$contributor" == Khush ]]; then
    author_name='Khush'
    author_email='Khushvendras99@gmail.com'
  else
    author_name='Aditya Ranjan'
    author_email='ranjanaditya689@gmail.com'
  fi
  tree=$(git rev-parse "${source}^{tree}")
  original=$(git show -s --format=%B "$source" | sed -n '/^Original-Commit: /,$p')
  message=$(printf '[reconstructed] %s\n\nDemonstration timeline: dates and author assignments are illustrative,\nnot evidence of when the original work occurred or who performed it.\nThe file snapshot comes from the source snapshot below.\n\nSnapshot-Commit: %s\n%s' "$subject" "$(git rev-parse "$source")" "$original")
  parents=()
  if [[ -n "$parent" ]]; then parents=(-p "$parent"); fi
  parent=$(GIT_AUTHOR_NAME="$author_name" GIT_AUTHOR_EMAIL="$author_email" \
    GIT_AUTHOR_DATE="$author_date" \
    git -c commit.gpgsign=false commit-tree "$tree" "${parents[@]}" -m "$message")
done

if [[ "$mode" == --create ]]; then
  # An empty expected old value makes this fail if the branch now exists.
  git update-ref "refs/heads/$branch" "$parent" ''
  printf '\nCreated %s without switching branches. Review with:\n' "$branch"
  printf '  git log --reverse --format=fuller %q\n' "$branch"
  printf '  git diff 90c054c %q\n' "$branch"
fi
