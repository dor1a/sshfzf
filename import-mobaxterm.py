#!/usr/bin/env python3
r"""Turn MobaXterm's saved sessions into hosts.yaml.

MobaXterm is Windows-only and keeps its sessions in
`%APPDATA%\MobaXterm\MobaXterm.ini`, one `[Bookmarks_N]` section per folder.
From WSL that path is under `/mnt/c`. `SubRep=` in each section is the folder path, which is exactly the tree
hosts.yaml calls `group` -- so the structure comes across without being retyped.

    ./import-mobaxterm.py "/mnt/c/Users/<you>/AppData/Roaming/MobaXterm/MobaXterm.ini"
    ./import-mobaxterm.py <MobaXterm.ini> -o "$hosts"   # the path the README works out

The number after the first `#` is the **icon**, not the session type -- these
sessions carry six different ones and every one of them is SSH. What separates
an SSH session is its field layout: `%host%port%user%`, with a port that parses
as a number. Anything else is skipped with a note.

Passwords are not read. MobaXterm writes a credential *name* in brackets where
the user should be. That name is a label in its own vault and is not required
to equal the account it logs in as -- a credential named for the environment
rather than the login is the case that catches you. The names come across as
`user` and the importer prints every distinct one at the end; check that list
against the real accounts before connecting.
"""

import argparse
import pathlib
import re
import sys

def parse(path):
    text = pathlib.Path(path).read_text(errors="replace").replace("\r", "")
    # Splitting on the section header keeps name and body adjacent.
    blocks = re.split(r"^\[(.+)\]$", text, flags=re.M)

    hosts, skipped = [], []
    for i in range(1, len(blocks), 2):
        section, body = blocks[i], blocks[i + 1]
        if not section.startswith("Bookmarks"):
            continue
        sub = re.search(r"^SubRep=(.*)$", body, re.M)
        group = (sub.group(1) if sub else "").strip().replace("\\", "/") or "ungrouped"

        for name, value in re.findall(r"^([^=\[\n]+)=(#\d+#.*)$", body, re.M):
            fields = value.split("#")
            icon = fields[1] if len(fields) > 1 else ""
            # #<icon>#0%host%port%user%...
            parts = fields[2].split("%") if len(fields) > 2 else []
            host = parts[1].strip() if len(parts) > 1 else ""
            port = parts[2].strip() if len(parts) > 2 else ""
            user = parts[3].strip() if len(parts) > 3 else ""
            if not host or not port.isdigit():
                skipped.append((name.strip(), icon))
                continue
            hosts.append(
                {
                    "name": name.strip(),
                    "group": group,
                    "hostname": host,
                    "port": port,
                    "user": user,
                }
            )
    return hosts, skipped


def emit(hosts):
    # A credential name in brackets is MobaXterm's, not ssh's. They line up with
    # accounts often enough to be worth unwrapping, and whichever appears most
    # belongs in defaults rather than on seventy hosts.
    users = {}
    for h in hosts:
        u = h["user"].strip("[]")
        h["user"] = u
        if u:
            users[u] = users.get(u, 0) + 1
    common = max(users, key=users.get) if users else ""

    out = [
        "# Imported from MobaXterm. Check it before use:",
        "#   - `user` came from a MobaXterm credential name, which is not",
        "#     required to equal the account it logs in as",
        "#   - a bastion needs proxy_jump adding by hand",
        "",
        # No preferred_authentications here. MobaXterm keeps passwords in its
        # own vault, so an imported host is very likely password-only, and
        # pinning publickey would refuse the one method that works.
        "defaults:",
    ]
    if common:
        out.append(f"  user: {common}")
    out += ["", "hosts:"]
    for h in hosts:
        out.append(f"  - name: {h['name']}")
        out.append(f"    group: {h['group']}")
        out.append(f"    hostname: {h['hostname']}")
        if h["port"] and h["port"] not in ("0", "22"):
            out.append(f"    port: {h['port']}")
        if h["user"] and h["user"] != common:
            out.append(f"    user: {h['user']}")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ini", help="path to MobaXterm.ini")
    ap.add_argument("-o", "--out", help="write here instead of stdout")
    args = ap.parse_args()

    hosts, skipped = parse(args.ini)
    if not hosts:
        sys.exit("no SSH sessions found")

    text = emit(hosts)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)

    groups = len({h["group"] for h in hosts})
    print(f"{len(hosts)} ssh hosts in {groups} groups", file=sys.stderr)
    users = {}
    for h in hosts:
        u = h["user"].strip("[]")
        if u:
            users[u] = users.get(u, 0) + 1
    if users:
        common = max(users, key=users.get)
        print(f"users seen: {users}", file=sys.stderr)
        print(
            f"  '{common}' went into defaults; the rest are per-host.\n"
            "  These came from MobaXterm credential names, which are labels in\n"
            "  its vault -- check each against the account it actually logs in as.",
            file=sys.stderr,
        )
    if skipped:
        kinds = {}
        for _, k in skipped:
            kinds[k] = kinds.get(k, 0) + 1
        print(f"skipped {len(skipped)} without a host/port: {kinds}", file=sys.stderr)


if __name__ == "__main__":
    main()
