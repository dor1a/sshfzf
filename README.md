# sshfzf

Pick an SSH host from a tree and connect. One file describes every host;
`~/.ssh/config` and the picker's list are both generated from it.

```
hosts.yaml ──generate.py──┬──> ~/.ssh/config    what ssh reads
                          └──> ~/.ssh/hosts     what sshfzf reads
```

## Why it is built this way

The first version kept a hand-maintained `.ssh/hosts` beside `.ssh/config`,
because ssh config has no way to express a category tree. That meant writing
every host name twice, and by the time it was next opened the two files had
already drifted — sixty-nine entries each, one of them out of step, and the
deployed config had a single host in it while the list offered sixty-eight.

So `hosts.yaml` is the only file edited by hand. Both outputs are generated,
which makes drift impossible rather than unlikely. It is gitignored — the
tracked file is `hosts.example.yaml`, so a fork's host list never lands in a
commit. Point `SSHFZF_HOSTS_YAML` elsewhere to keep it outside the repo
entirely.

## Where it runs

zsh and Python, so WSL, macOS and any Linux.

⚠️ **On Windows, run it inside WSL.** There is no PowerShell version. Windows
Terminal hosts the WSL shell, which is where `sshfzf` lives; the ssh config it
generates is WSL's `~/.ssh/config`, not the one under `%USERPROFILE%`.

Keeping to one side is deliberate rather than lazy — see the last section.

## Setup

```sh
sudo apt install fzf          # or: brew install fzf
pip install --user pyyaml     # if `python3 -c "import yaml"` fails

cp hosts.example.yaml hosts.yaml   # hosts.yaml is gitignored — yours stays local
./generate.py                      # writes ~/.ssh/config and ~/.ssh/hosts
ln -sfn "$PWD/sshfzf" ~/.local/bin/sshfzf
```

`sshfzf` is an executable rather than a shell function, so no rc file has to
know it exists. Link it into any directory already on `PATH` and it runs from
any shell. macOS does not put `~/.local/bin` on `PATH`, so add it there if
`which sshfzf` comes up empty.

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
| `sshfzf-tree` | print the tree and nothing else |

The preview runs `ssh -G`, which resolves the config the way ssh itself will —
the hostname a pattern expands to, the user, the jump host. It touches no
network, so it is instant even for hosts behind a bastion.

## Managing hosts

Every command edits `hosts.yaml` and regenerates immediately, so the ssh config
is never a change behind. Omit the name and you get a picker rather than a
usage error.

| | |
|---|---|
| `./generate.py add` | asks for each field; the group comes from an fzf list of the ones in use, or type a new path |
| `./generate.py add <name> <group> <hostname>` | same, for scripts. `-p` port, `-u` user, `-j` proxy jump, `-i` identity file |
| `./generate.py set` | pick one, then `-u root`, `-p 2222`, `--unset port`. Fields you do not name are left alone |
| `./generate.py remove` | pick with tab to mark several; escape does nothing |
| `./generate.py --tree` | the whole tree |

`hosts.yaml` stays plain YAML and edits are made on the text, so comments and
ordering survive — which means editing it by hand still works when that is
faster than a command.

## Importing from MobaXterm

MobaXterm is Windows-only, so its config lives on the Windows side:

```
%APPDATA%\MobaXterm\MobaXterm.ini
```

From WSL that is reachable under `/mnt/c`, which is where this is usually run:

```sh
./import-mobaxterm.py "/mnt/c/Users/<you>/AppData/Roaming/MobaXterm/MobaXterm.ini" \
  -o hosts.yaml
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

Then `./generate.py`.

`group` is the one field ssh has no equivalent for; it is what builds the tree,
and it is free text. Everything else is an ssh option in `snake_case`:
`proxy_jump` becomes `ProxyJump`, `identity_file` becomes `IdentityFile`. There
is no list of supported keys — whatever ssh understands passes through.

`defaults:` applies to every host, and a host that repeats a key overrides it.

## Checks

```sh
./generate.py --check      # validate hosts.yaml
./generate.py --tree       # the tree, without writing anything
./generate.py --dry-run    # what would be written
```

`--check` refuses a host with no group (it would never appear in the picker), a
duplicate name (ssh silently uses the first and ignores the rest), and a
`proxy_jump` naming a host that is not defined here.

## Keys are not shared between WSL and Windows

If both are in use, each side needs its own `~/.ssh` — a Windows key read
through `/mnt/c` shows as `0777` because DrvFs does not carry Unix modes, and
`ssh` refuses a private key that permissive. Generating into WSL alone avoids
the question; making Windows work too means a second key pair, not a symlink.
