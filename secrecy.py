#!/usr/bin/env python3

from typing import List, Optional
import argparse
import configparser
import fnmatch
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

def matches_any_pattern(path: str, patterns) -> bool:
    if path.startswith("./"):
        path = path[2:]

    for pattern in patterns:
        pattern = pattern[1:] if pattern.startswith("/") else f'*{pattern}'
        if fnmatch.fnmatch(path, pattern):
            return True

    return False


class Context:
    """Utility type to keep track of error state and emit errors"""

    # Configuration
    config_ignores: List[str] = []
    config_vaults: List[str] = []

    # Runtime state
    errored = False
    commit: Optional[str] = None

    def is_ignored(self, path: str) -> bool:
        return matches_any_pattern(path, self.config_ignores)

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
    if ctx.is_ignored(path):
        return

    check_vault(ctx, content, path)
    check_private_key(ctx, content, path)


def check_vault(ctx: Context, content: bytes, path: str):
    """Checks for unencrypted Ansible vaults

    Emits an error if the filename is "vault" but the file does not start with
    "$ANSIBLE_VAULT", OR if any line starts with `vault_` and has a colon in it
    (thus resembling a variable assignment).
    """

    is_vault_file = (
        os.path.basename(path) == "vault" or
        matches_any_pattern(path, ctx.config_vaults)
    )

    if is_vault_file and not content.startswith(b"$ANSIBLE_VAULT"):
        if os.path.basename(path) == "vault":
            ctx.error(path, f'has filename "vault" but does not start with "$ANSIBLE_VAULT"')
        else:
            ctx.error(path, f'is a vault file (according to the configuration)'
                + ' but does not start with "$ANSIBLE_VAULT"')

        return

    for lineno, line in enumerate(content.splitlines(), start=1):
        if line.startswith(b"vault_") and b":" in line:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'looks like a vault variable definition: {linestr}')


def check_private_key(ctx: Context, content: bytes, path: str):
    pattern = re.compile(b"-----BEGIN .*PRIVATE KEY-----")
    for lineno, line in enumerate(content.splitlines(), start=1):
        if pattern.search(line) is not None:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'unencrypted private key: {linestr}')


# ----- Main: entry points ---------------------------------------------------

HELP_TEXT = (
    "Example usage:\n"
    "\n"
    "secrecy path <path>\n"
    "    Checking a single given file or all files in a given directory.\n"
    "\n"
    "secrecy staged\n"
    "    Checking all files that are currently staged by git (useful for pre-commit hook).\n"
    "\n"
    "secrecy between <base-commit> <target-commit>\n"
    "    Checking all files that were changed somewhere between two commits. This is\n"
    "    useful for pre-receive git hooks as only checking the final files does not\n"
    "    tell you if secrets are hiding somewhere in the git history. This command\n"
    "    checks the commits given by this command: `git rev-list base^ target`.\n"
)

def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(prog='secrecy', epilog=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="path to the configuration file")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    subparsers.add_parser("staged")
    path_parser = subparsers.add_parser("path")
    path_parser.add_argument("path", help="The path to (recursively) check")
    between_parser = subparsers.add_parser("between")
    between_parser.add_argument("start", help="start of the commit range to be checked")
    between_parser.add_argument("end", help="end of the commit range to be checked")

    args = parser.parse_args()


    ctx = Context()

    # Read configuration file
    config_file = args.config
    if config_file is None and os.path.isfile("secrecy.ini"):
        config_file = "secrecy.ini"

    if config_file is not None:
        config = configparser.ConfigParser()
        config.read_file(open(config_file), source=config_file)
        ctx.config_ignores = config.get("secrecy", "ignore", fallback="").strip().splitlines()
        ctx.config_vaults = config.get("secrecy", "vaults", fallback="").strip().splitlines()


    # Dispatch subcommand
    if args.cmd == "path":
        check_current(ctx, args.path)
    elif args.cmd == "staged":
        check_staged(ctx)
    elif args.cmd == "between":
        check_between(ctx, args.start, args.end)
    else:
        raise "no subcommand given"

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
        if ctx.is_ignored(path):
            eprint(f'The file you specified ({path}) is ignored by the configuration')
            return

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
