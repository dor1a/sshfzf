# sshfzf — pick a host from the generated tree and connect.
#
# Reads ~/.ssh/hosts, which generate.py writes from hosts.yaml. Nothing here
# parses the ssh config, so this file stays the same however hosts.yaml grows.
#
# Source it from ~/.zshrc, or link it into ~/.oh-my-zsh/custom/ where oh-my-zsh
# picks up every *.zsh on its own:
#
#     ln -sfn <repo>/sshfzf.zsh ~/.oh-my-zsh/custom/sshfzf.zsh
#
# POSIX only, so the same file works on macOS.

: "${SSHFZF_HOSTS:=$HOME/.ssh/hosts}"

sshfzf() {
  if [[ ! -r "$SSHFZF_HOSTS" ]]; then
    print -u2 "sshfzf: no $SSHFZF_HOSTS — run generate.py first"
    return 1
  fi
  command -v fzf >/dev/null || { print -u2 "sshfzf: fzf is not installed"; return 1 }

  local selected host
  # The preview is `ssh -G`, which resolves the config the way ssh will: the
  # HostName a pattern expands to, the user, the jump host. That is the thing
  # worth seeing before connecting, and it needs no network.
  selected=$(
    grep -vE '^\s*(#|$)' "$SSHFZF_HOSTS" |
      fzf --layout=reverse --height=60% --border \
          --prompt='ssh > ' \
          --header='enter to connect · ctrl-t for the tree' \
          --preview='ssh -G ${${(s:/:)1}[-1]} 2>/dev/null |
                     grep -iE "^(hostname|user|port|proxyjump|identityfile) " ' \
          --preview-window='right,45%,wrap' \
          --bind='ctrl-t:change-preview(sshfzf-tree)'
  ) || return 0

  # Only the last path segment is the ssh host; the rest is the group.
  host=${${(s:/:)selected}[-1]}
  [[ -n "$host" ]] && ssh "$host"
}

# The whole list at once, for when the question is "what do I have" rather than
# "connect me to this one".
sshfzf-tree() {
  local gen="${SSHFZF_REPO:-}/generate.py"
  if [[ -x "$gen" ]]; then
    "$gen" --tree
    return
  fi
  # Without the repo on hand, rebuild the tree from the generated list.
  grep -vE '^\s*(#|$)' "${SSHFZF_HOSTS}" | awk -F/ '
    { indent = ""
      for (i = 1; i < NF; i++) {
        if (seen[i "\x1f" $i] != 1) { print indent $i; seen[i "\x1f" $i] = 1 }
        indent = indent "  "
      }
      print indent $NF
    }'
}

# No completion function here: sshfzf takes no arguments, and zsh already
# completes `ssh` from the generated ~/.ssh/config on its own.
