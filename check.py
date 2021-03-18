#!/usr/bin/env python3

from typing import List
import os
import sys


def main():
    path = sys.argv[1]
    with open(path, "rb") as f:
        content = f.read()
        check_file(content, path)
    pass

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def check_file(content: bytes, path: str):
    check_vault_filename(content, path)

def check_vault_filename(content: bytes, path: str):
    if os.path.basename(path) == "vault" and not content.startswith(b"$ANSIBLE_VAULT"):
        eprint(f'Error: {path} has filename "vault" but does not start with "$ANSIBLE_VAULT"')





if __name__ == "__main__":
    main()
