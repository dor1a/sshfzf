# sshfzf

Pick an SSH host from a tree and connect. One file describes every host;
`~/.ssh/config` and the picker's list are both generated from it.

```
~/.config/sshfzf/hosts.yaml ──sshfzf generate──┬──> ~/.ssh/config    what ssh reads
                                               └──> ~/.ssh/hosts     what sshfzf reads
```

## Why it is built this way

The first version kept a hand-maintained `.ssh/hosts` beside `.ssh/config`,
because ssh config has no way to express a category tree. That meant writing
every host name twice, and by the time it was next opened the two files had
already drifted — sixty-nine entries each, one of them out of step, and the
deployed config had a single host in it while the list offered sixty-eight.

So `hosts.yaml` is the only file edited by hand. Both outputs are generated,
which makes drift impossible rather than unlikely. It lives in
`~/.config/sshfzf/` (or `$XDG_CONFIG_HOME/sshfzf/`), away from the code, so an
upgrade never touches it and a fork's host list never lands in a commit.
`SSHFZF_HOSTS_YAML` points it anywhere else.

## Where it runs

zsh and Python, so WSL, macOS and any Linux. On macOS, install it with
Homebrew; elsewhere, run it from a clone.

⚠️ **On Windows, run it inside WSL.** There is no PowerShell version. Windows
Terminal hosts the WSL shell, which is where `sshfzf` lives; the ssh config it
generates is WSL's `~/.ssh/config`, not the one under `%USERPROFILE%`.

Keeping to one side is deliberate rather than lazy — see the last section.

## Setup

### macOS, with Homebrew

```sh
brew install dor1a/tap/sshfzf          # fzf comes with it

hosts="${SSHFZF_HOSTS_YAML:-${XDG_CONFIG_HOME:-$HOME/.config}/sshfzf/hosts.yaml}"
mkdir -p -m 700 "$(dirname "$hosts")"
install -m 600 "$(brew --prefix sshfzf)/libexec/hosts.example.yaml" "$hosts"
sshfzf generate                        # writes ~/.ssh/config and ~/.ssh/hosts
```

`$hosts` is worked out in the same order `sshfzf` uses: `SSHFZF_HOSTS_YAML`
if set, then `$XDG_CONFIG_HOME/sshfzf/hosts.yaml`, then
`~/.config/sshfzf/hosts.yaml`.

`brew upgrade sshfzf` replaces the code and leaves `hosts.yaml` alone.

### WSL and Linux, from a clone

```sh
sudo apt install fzf
git clone https://github.com/dor1a/sshfzf.git ~/sshfzf

hosts="${SSHFZF_HOSTS_YAML:-${XDG_CONFIG_HOME:-$HOME/.config}/sshfzf/hosts.yaml}"
mkdir -p -m 700 "$(dirname "$hosts")"
install -m 600 ~/sshfzf/hosts.example.yaml "$hosts"
mkdir -p ~/.local/bin
ln -sfn ~/sshfzf/sshfzf ~/.local/bin/sshfzf
sshfzf generate
```

`git pull` updates it. A clone that still keeps `hosts.yaml` beside the code
needs it moved to `$hosts`; nothing reads the old place.

`sshfzf` is an executable rather than a shell function, so no rc file has to
know it exists. Link it into any directory already on `PATH` and it runs from
any shell. macOS does not put `~/.local/bin` on `PATH`, so add it there if
you run a clone on a Mac and `which sshfzf` comes up empty.

Being a file is also what makes `ctrl-t` work. fzf runs its child commands with
`$SHELL -c`, and that shell is not interactive, so it never reads `~/.zshrc` —
a function defined there is invisible to the preview. The binding calls this
file by path instead.

⚠️ `generate.py` will not overwrite an `~/.ssh/config` it did not write. Move an
existing one aside once its hosts are in `hosts.yaml`.

## Use

| | |
|---|---|
| `sshfzf` | pick and connect |
| `enter` | connect to the highlighted host |
| `ctrl-t` | swap the preview for the whole tree |
| `sshfzf --tree` | print the tree and nothing else |
| `sshfzf --select` | print the selected SSH alias without connecting; cancellation prints nothing |

The preview runs `ssh -G`, which resolves the config the way ssh itself will —
the hostname a pattern expands to, the user, the jump host. It touches no
network, so it is instant even for hosts behind a bastion.

### Recall the selected connection with Up

An executable cannot update its parent shell's in-memory history. For zsh,
add this wrapper to `~/.zshrc`. It uses the executable for selection and records
`ssh user@alias` before connecting, so Up recalls that command even after Ctrl-C.
The user comes from `ssh -G`; the alias retains its configured port and jump host.
Cancelling the picker adds no SSH command to history.

```zsh
sshfzf() {
  if (( $# )); then
    command sshfzf "$@"
    return $?
  fi
  local selected ssh_user target config
  selected=$(command sshfzf --select) || return $?
  [[ -n "$selected" ]] || return 0
  config=$(command ssh -G "$selected") || return $?
  ssh_user=$(print -r -- "$config" | awk '$1 == "user" {print $2; exit}')
  [[ -n "$ssh_user" ]] || return 1
  target="$ssh_user@$selected"
  print -s -- ssh "$target"
  command ssh "$target"
}
```

Run `source ~/.zshrc` in existing terminals. New shells load it automatically.
Update the executable first: the wrapper requires `--select`. Calling
`command sshfzf` bypasses the wrapper and retains the standalone behavior.

## Managing hosts

Every command edits `hosts.yaml` and regenerates immediately, so the ssh config
is never a change behind. Omit the name and you get a picker rather than a
usage error.

| | |
|---|---|
| `sshfzf add` | asks for each field; the group comes from an fzf list of the ones in use, or type a new path |
| `sshfzf add <name> <group> <hostname>` | same, for scripts. `-p` port, `-u` user, `-j` proxy jump, `-i` identity file |
| `sshfzf set` | pick one, then `-u root`, `-p 2222`, `--unset port`. Fields you do not name are left alone |
| `sshfzf remove` | pick with tab to mark several; escape does nothing |
| `sshfzf generate` | regenerate after editing `hosts.yaml` by hand |

These hand their arguments to `generate.py`, which a Homebrew install keeps off
`PATH`. From a clone, `./generate.py` with the same arguments does the same.

`hosts.yaml` stays plain YAML and edits are made on the text, so comments and
ordering survive — which means editing it by hand still works when that is
faster than a command.

Nothing beyond the Python standard library is needed. `generate.py` reads the
shape the commands write: `defaults:` and `hosts:`, then one `key: value` per
line. Quotes and trailing `# comments` are fine; anchors and multi-line values
are not, and a line it cannot read stops it with the line number.

## Importing from MobaXterm

MobaXterm is Windows-only, so its config lives on the Windows side:

```
%APPDATA%\MobaXterm\MobaXterm.ini
```

From WSL that is reachable under `/mnt/c`, which is where this is usually run:

```sh
hosts="${SSHFZF_HOSTS_YAML:-${XDG_CONFIG_HOME:-$HOME/.config}/sshfzf/hosts.yaml}"
mkdir -p -m 700 "$(dirname "$hosts")"
./import-mobaxterm.py "/mnt/c/Users/<you>/AppData/Roaming/MobaXterm/MobaXterm.ini" -o "$hosts"
chmod 600 "$hosts"
```

`SubRep=` in each `[Bookmarks_N]` section is the folder path, so the tree comes
across without being retyped.

⚠️ Check `user` afterwards. MobaXterm stores a credential *name* where the user
belongs — a label in its own vault, which is not required to equal the account
it logs in as. `proxy_jump`, `identity_file` and passwords are not in the
format at all.

## The host schema

```yaml
hosts:
  - name: web1
    group: prod/frontend
    hostname: 10.0.0.11
    proxy_jump: bastion
```

Then `sshfzf generate`.

`group` is the one field ssh has no equivalent for; it is what builds the tree,
and it is free text. Everything else is an ssh option in `snake_case`:
`proxy_jump` becomes `ProxyJump`, `identity_file` becomes `IdentityFile`. There
is no list of supported keys — whatever ssh understands passes through.

`defaults:` applies to every host, and a host that repeats a key overrides it.

## Checks

```sh
sshfzf generate --check      # validate hosts.yaml
sshfzf generate --tree       # the tree, without writing anything
sshfzf generate --dry-run    # what would be written
```

`--check` refuses a host with no group (it would never appear in the picker), a
duplicate name (ssh silently uses the first and ignores the rest), and a
`proxy_jump` naming a host that is not defined here.

## Keys are not shared between WSL and Windows

If both are in use, each side needs its own `~/.ssh` — a Windows key read
through `/mnt/c` shows as `0777` because DrvFs does not carry Unix modes, and
`ssh` refuses a private key that permissive. Generating into WSL alone avoids
the question; making Windows work too means a second key pair, not a symlink.

## License

MIT. See [LICENSE](LICENSE).
