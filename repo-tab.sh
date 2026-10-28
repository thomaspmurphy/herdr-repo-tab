#!/bin/sh
# repo-tab: pick a ghq repo with fzf and open it as a tab in one herdr workspace.
#   open  show the picker in an overlay pane (bind this action to a key)
#   pick  the picker itself: choose a repo, then jump to its tab in the
#         workspace, creating the tab (and the workspace) when missing
#
# REPO_TAB_SPACE names the workspace the tabs go in (default: terminal).
H="${HERDR_BIN_PATH:-herdr}"
PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
NAME="${REPO_TAB_SPACE:-terminal}"

# Without these the overlay would close before the error could be read.
need() {
  missing=""
  for cmd in fzf jq; do
    command -v "$cmd" >/dev/null 2>&1 || missing="$missing $cmd"
  done
  [ -z "$missing" ] && return 0
  printf 'repo-tab needs:%s\nPress Enter to close.' "$missing"
  read -r _
  exit 1
}

repos() {
  if command -v ghq >/dev/null 2>&1; then
    ghq list -p
  else
    for git in "$HOME"/ghq/*/*/*/.git; do [ -e "$git" ] && dirname "$git"; done
  fi
}

# The workspace is matched by its label, either exactly or after an icon
# ("<icon>  terminal"), so a workspace made by another tool is reused.
workspace_id() {
  "$H" workspace list | jq -r --arg n "$NAME" '
    [.result.workspaces[] | select(.label == $n or (.label | endswith("  " + $n)))][0].workspace_id // empty'
}

ensure_space() {
  ws=$(workspace_id)
  # cockpit users get the workspace from cockpit's own script, so it keeps cockpit's label.
  if [ -z "$ws" ] && [ -f "$HOME/.config/cockpit/herdr/ensure-spaces.sh" ]; then
    sh "$HOME/.config/cockpit/herdr/ensure-spaces.sh" >/dev/null 2>&1
    ws=$(workspace_id)
  fi
  if [ -z "$ws" ]; then
    ws=$("$H" workspace create --cwd "$HOME" --label "$NAME" --no-focus | jq -r '.result.workspace.workspace_id')
  fi
  echo "$ws"
}

pick() {
  need
  root="$HOME/ghq/"
  command -v ghq >/dev/null 2>&1 && root="$(ghq root)/"
  # Rows are "<path>\t<label>": fzf shows the label without the root and host
  # (~/ghq/github.com/owner/repo → owner/repo).
  dir=$(repos | awk -v r="$root" '{
      l = $0
      if (index(l, r) == 1) l = substr(l, length(r) + 1)
      sub("^[^/]+/", "", l)
      print $0 "\t" l
    }' |
    fzf --delimiter '\t' --with-nth 2 --prompt 'repo › ' \
      --header "Enter: open as a tab in the $NAME workspace" \
      --preview 'git -C {1} -c color.status=always status -sb | head -20; echo; git -C {1} log --oneline --color=always -10' \
      --preview-window right:50% | cut -f1)
  [ -n "$dir" ] || exit 0

  ws=$(ensure_space)
  [ -n "$ws" ] || exit 1
  # A tab whose pane already sits at the repo root is reused rather than duplicated.
  tab=$("$H" pane list --workspace "$ws" | jq -r --arg d "$dir" '[.result.panes[] | select(.cwd == $d)][0].tab_id // empty')
  if [ -z "$tab" ]; then
    tab=$("$H" tab create --workspace "$ws" --cwd "$dir" --label "$(basename "$dir")" --no-focus | jq -r '.result.tab.tab_id')
  fi
  "$H" workspace focus "$ws" >/dev/null
  "$H" tab focus "$tab" >/dev/null
}

case "$1" in
  open) "$H" plugin pane open --plugin repo-tab --entrypoint picker --focus >/dev/null ;;
  pick) pick ;;
esac
