#!/usr/bin/env python3

from typing import List, Optional
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
    commit: Optional[str] = None

    def error(self, path: str, msg: str):
        self.errored = True
        print(f'ERROR in {path}{self.commit_output()} => {msg}', file=sys.stderr)

    def line_error(self, path: str, line: int, msg: str):
        self.errored = True
        print(f'ERROR in {path}:{line}{self.commit_output()} => {msg}', file=sys.stderr)

    def commit_output(self):
        if self.commit is not None:
            return f' (at {self.commit})';
        else:
            return ""


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
    elif len(sys.argv) == 4 and sys.argv[1] == "--between":
        check_between(ctx, sys.argv[2], sys.argv[3])
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
    print("")
    print("Checking all files that were changed somewhere between two commits. This is")
    print("useful for pre-receive git hooks as only checking the final files does not")
    print("tell you if secrets are hiding somewhere in the git history. This command")
    print("checks the commits given by this command: `git rev-list base^ target`.")
    print("    check --between <base-commit> <target-commit>")

def check_staged(ctx: Context):
    """Checks all files that are currently staged. Useful in pre-commit hook"""

    files = subprocess.check_output(["git", "diff", "--staged", "--name-only"])
    for file in files.splitlines():
        filestr = file.decode()
        content = read_file(filestr)
        check_file(ctx, content, filestr)

def check_between(ctx: Context, base: str, target: str):
    """Checks all files changed in all commits between the two given ones.

    "Between" in the git commit graph is a bit vague. Precisely: all commits are
    inspected that are reachable from 'target' but are not reachable from
    'base'. This maps very nicely to the intuitive notion of "new commits" in a
    pre-receive hook.
    """

    commits = subprocess.check_output(["git", "rev-list", f'^{base}', target])
    for rawcommit in commits.splitlines():
        commit = rawcommit.decode()

        # Setting the commit in the context for better error message
        ctx.commit = commit

        # Receive all files that were somehow changed in that commit, excluding
        # the files that were removed.
        cmd = ["git", "diff", "--diff-filter=d", "--name-only", f'{commit}^', commit]
        files = subprocess.check_output(cmd)
        for file in files.splitlines():
            filestr = file.decode()
            content = subprocess.check_output(["git", "show", f'{commit}:{filestr}'])
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
