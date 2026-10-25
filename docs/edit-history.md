# Customize the existing commit history

This helper opens the current checkout's existing commits in Git's interactive
rebase editor, starting with the first commit. It creates a separate branch and
working directory. Your original branch, staged changes, and untracked files
remain in place.

## 1. Preview the commits

From the repository root:

```bash
bash scripts/edit-history.sh --preview
```

This lists the existing commits, author dates, authors, and subjects. With no
arguments, the script also previews. It starts from local `HEAD`; it does not
fetch or merge remote changes.

## 2. Open an editable copy

Choose a new branch name and a directory that does not already exist:

```bash
bash scripts/edit-history.sh --edit history/refined ../freshroute-history
```

Git opens a list of the existing commits, oldest first. Edit the command at the
start of each line:

| Command | Effect |
| --- | --- |
| `pick` | Keep the commit as it is. |
| `reword` | Keep its changes and edit its message in a subsequent editor. |
| `squash` | Combine it with the preceding commit and edit the combined message. |
| `fixup` | Combine it with the preceding commit, keeping the preceding message. |

Move lines to change commit order. Keep prerequisite changes before the work
that depends on them; moving dependent commits can cause conflicts. Save and
close the editor to proceed. Rewording is the simplest way to clarify milestones
while preserving the detailed development trail.

Git retains original author identities and author dates for replayed commits;
rewritten commits record the current committer and actual rewrite time.
Squashing combines several contributions into one commit, so review its
authorship and message. The script does not manufacture development dates or
contributions and does not push or replace the original branch.

## 3. Review the result

```bash
git -C ../freshroute-history log --reverse --oneline
git diff main history/refined
```

If you started from another branch, replace `main` with that branch. For a
message-only cleanup, the file diff should be empty. For reordered or combined
commits, also rerun the relevant project checks in the new worktree.

Commit IDs change when history is rewritten. Keep the original branch: the
experiment provenance and project documentation reference its existing IDs.

If rebase stops, inspect and resolve conflicts in the separate worktree, then
run `git -C ../freshroute-history rebase --continue`. To cancel the rebase, run
`git -C ../freshroute-history rebase --abort`. The original checkout remains
available throughout. Publishing or replacing a remote branch is a separate
action; this script performs neither.
