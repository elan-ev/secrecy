#!/usr/bin/env python3

from typing import List
import os
import sys


def main():
    ctx = Context()
    path = sys.argv[1]
    with open(path, "rb") as f:
        content = f.read()
        check_file(ctx, content, path)

    if ctx.errored:
        eprint("")
        eprint("Potentially found unencrypted secrets!")
        sys.exit(1)

# ----- Utilities ------------------------------------------------------------

def eprint(msg: str):
    print(msg, file=sys.stderr)

class Context:
    """Utility type to keep track of error state and emit errors"""

    errored = False

    def error(self, path: str, msg: str):
        self.errored = True
        print(f'ERROR in "{path}" => {msg}', file=sys.stderr)

    def line_error(self, path: str, line: int, msg: str):
        self.errored = True
        print(f'ERROR in {path}:{line} => {msg}', file=sys.stderr)


# ----- Actual checks trying to detect secrets -------------------------------

def check_file(ctx: Context, content: bytes, path: str):
    check_vault_filename(ctx, content, path)
    check_var_starting_with_vault(ctx, content, path)


def check_vault_filename(ctx: Context, content: bytes, path: str):
    """Emits an error if the filename is "vault" but the file does not start
    with "$ANSIBLE_VAULT"
    """
    if os.path.basename(path) == "vault" and not content.startswith(b"$ANSIBLE_VAULT"):
        ctx.error(path, f'has filename "vault" but does not start with "$ANSIBLE_VAULT"')

def check_var_starting_with_vault(ctx: Context, content: bytes, path: str):
    for lineno, line in enumerate(content.splitlines(), start=1):
        if line.startswith(b"vault_") and b":" in line:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'looks like a vault variable definition: {linestr}')





if __name__ == "__main__":
    main()
