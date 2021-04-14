# Secrecy: simple script to detect secrets

WIP


## Git Hooks

It is very simple to use this script from git hooks.
There are two hooks of particular interest.

### `pre-commit`

This hook is executed before the user has a chance to type a commit message.
With this, you can prevent secrets from ever entering any git history.
The disadvantage is that all developers have to setup this hook locally themselves, which can be forgotten.

In the hook you simply have to call `secrecy.py staged` to check all staged files.

### `pre-receive`

This hook is supposed to be executed on the server side and is able to reject pushes.
This can make sure that secrets are never stored in the repository on the server.
It doesn't prevent developers from committing secrets locally, but it runs for all pushes and is a good second check for developers who forgot to setup a local `pre-commit` hook.

In this hook, run `secrecy.py between <start> <target>` to check all new commits for secrets.


### Recommended setup

- Create a folder `secrecy` somewhere in your repository.
- Copy `secrecy.py` from this repository into it.
- Create a subfolder `secrecy/hooks` and copy the files `pre-commit` and `pre-receive` from the `hooks` folder in this repository into it.
  Make sure all of those files are executable.
- Instruct all developers to run this after cloning:
    - `ln -s $(readlink -f path/to/your/secrecy/hooks/pre-commit) .git/hooks/pre-commit`


---

## License

[CC0-1.0](./LICENSE).
