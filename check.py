#!/usr/bin/env python3

from typing import List
import os
import re
import subprocess
import sys



# ----- Utilities ------------------------------------------------------------

def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def eprint(msg: str):
    print(msg, file=sys.stderr)

class Context:
    """Utility type to keep track of error state and emit errors"""

    errored = False

    def error(self, path: str, msg: str):
        self.errored = True
        print(f'ERROR in {path} => {msg}', file=sys.stderr)

    def line_error(self, path: str, line: int, msg: str):
        self.errored = True
        print(f'ERROR in {path}:{line} => {msg}', file=sys.stderr)


# ----- Actual checks trying to detect secrets -------------------------------

def check_file(ctx: Context, content: bytes, path: str):
    check_vault(ctx, content, path)
    check_private_key(ctx, content, path)


def check_vault(ctx: Context, content: bytes, path: str):
    """Checks for unencrypted Ansible vaults

    Emits an error if the filename is "vault" but the file does not start with
    "$ANSIBLE_VAULT", OR if any line starts with `vault_` and has a colon in it
    (thus resembling a variable assignment).
    """
    if os.path.basename(path) == "vault" and not content.startswith(b"$ANSIBLE_VAULT"):
        ctx.error(path, f'has filename "vault" but does not start with "$ANSIBLE_VAULT"')
        return

    for lineno, line in enumerate(content.splitlines(), start=1):
        if line.startswith(b"vault_") and b":" in line:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'looks like a vault variable definition: {linestr}')


def check_private_key(ctx: Context, content: bytes, path: str):
    pattern = re.compile(b"-----BEGIN .+PRIVATE KEY-----")
    for lineno, line in enumerate(content.splitlines(), start=1):
        if pattern.search(line) is not None:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'unencrypted private key: {linestr}')


# ----- Main: entry points ---------------------------------------------------

def main():
    ctx = Context()

    if len(sys.argv) < 2:
        print_help()
    elif len(sys.argv) == 2 and sys.argv[1] == "--staged":
        check_staged(ctx)
    elif len(sys.argv) == 2:
        check_current(ctx, sys.argv[1])
    else:
        print_help()

    if ctx.errored:
        eprint("")
        eprint("Potentially found unencrypted secrets!")
        sys.exit(1)

def print_help():
    print("Missing argument. Usage:")
    print("")
    print("Checking a single given file or all files in a given directory:")
    print("    check <path>")
    print("")
    print("Checking all files that are currently staged by git (useful for pre-commit hook):")
    print("    check --staged")

def check_staged(ctx: Context):
    """Checks all files that are currently staged. Useful in pre-commit hook"""

    files = subprocess.check_output(["git", "diff", "--staged", "--name-only"])
    for file in files.splitlines():
        filestr = file.decode()
        content = read_file(filestr)
        check_file(ctx, content, filestr)

def check_current(ctx: Context, path: str):
    """Checks all files in 'path' in their current version (not using git)"""

    if os.path.isfile(path):
        content = read_file(path)
        check_file(ctx, content, path)
    else:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                fullpath = os.path.join(dirpath, filename);
                content = read_file(fullpath)
                check_file(ctx, content, fullpath)




if __name__ == "__main__":
    main()
